"""首页仪表盘和交易增删改路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import Flask, session, request, url_for, redirect, render_template, flash

from models import db, User, Family, Category, Transaction, Account, AccountType, \
    SavingsPlan, SavingsRecord, MonthlyTodo, DEFAULT_CATEGORIES, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR


@pytest.fixture
def main_app():
    """创建包含 main.py 路由的测试 app（首页/交易增删改/before_request）"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    db_path = temp_db.name

    application = Flask(__name__)
    application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['SECRET_KEY'] = 'test-secret-key'
    application.config['TESTING'] = True
    application.static_folder = str(BASE_DIR / 'src' / 'static')
    application.template_folder = str(BASE_DIR / 'src' / 'templates')

    db.init_app(application)

    @application.template_filter('currency')
    def currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '0.00'
        return f'{value:,.{decimals}f}'

    @application.template_filter('signed_currency')
    def signed_currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '+0.00'
        formatted = f'{abs(value):,.{decimals}f}'
        return f'+{formatted}' if value >= 0 else f'-{formatted}'

    @application.context_processor
    def inject_timedelta():
        return {'timedelta': timedelta}

    # --- 注册 before_request ---
    @application.before_request
    def require_login():
        allowed_routes = ['auth.login', 'auth.register', 'static']
        if request.endpoint and request.endpoint not in allowed_routes:
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))

    # --- 注册首页路由 ---
    @application.route('/')
    def index():
        from sqlalchemy import func, extract, case
        from routes.account import _get_family_accounts, _get_exchange_rates
        from routes.savings import _get_family_member_ids
        from routes.monthly_todo import ensure_monthly_checklist, CHECKLIST_ITEMS

        user_id = session.get('user_id')
        user = User.query.get(user_id)
        family = user.family if user else None
        current_view = request.args.get('view', 'family' if family else 'personal')
        if current_view == 'family' and not family:
            current_view = 'personal'

        if current_view == 'family' and family:
            family_member_ids = [m.id for m in family.members]
            user_filter = Transaction.user_id.in_(family_member_ids)
        else:
            user_filter = (Transaction.user_id == user_id)

        current_month = date.today().month
        current_year = date.today().year

        month_stats = db.session.query(
            func.sum(case(
                ((Transaction.type == 'income') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & user_filter, Transaction.amount)
            )).label('income'),
            func.sum(case(
                ((Transaction.type == 'expense') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & user_filter, Transaction.amount)
            )).label('expense')
        ).first()

        monthly_income = float(month_stats.income or 0)
        monthly_expense = float(month_stats.expense or 0)
        monthly_balance = monthly_income - monthly_expense

        accounts = _get_family_accounts(user_id, current_view)
        rates = _get_exchange_rates()
        savings_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'savings']
        fund_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'fund']
        stock_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'stock']
        savings_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in savings_accounts)
        fund_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in fund_accounts)
        stock_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in stock_accounts)
        total_assets = savings_total + fund_total + stock_total

        member_ids = _get_family_member_ids(user_id, current_view)
        plans = SavingsPlan.query.filter(SavingsPlan.created_by.in_(member_ids)).all()
        total_target = Decimal('0')
        total_saved = Decimal('0')
        for plan in plans:
            saved = db.session.query(func.sum(SavingsRecord.amount)).filter(
                SavingsRecord.plan_id == plan.id
            ).scalar() or Decimal('0')
            total_target += plan.target_amount
            total_saved += saved
        overall_progress = float(total_saved / total_target * 100) if total_target else 0

        checklist = ensure_monthly_checklist(user_id, current_year, current_month)
        checklist.sort(key=lambda t: t.priority, reverse=True)
        required_todos = [t for t in checklist if t.is_required]
        required_completed = sum(1 for t in required_todos if t.status == 'completed')
        total_required = len(required_todos)
        checklist_rate = (required_completed / total_required * 100) if total_required > 0 else 0

        popup_key = f'todo_popup_{current_year}_{current_month}'
        pending_required = [t for t in required_todos if t.status != 'completed']
        show_todo_popup = len(pending_required) > 0 and not session.get(popup_key)
        if show_todo_popup:
            session[popup_key] = True

        return render_template('index.html',
                              monthly_income=monthly_income,
                              monthly_expense=monthly_expense,
                              monthly_balance=monthly_balance,
                              stat_year=current_year,
                              stat_month=current_month,
                              savings_total=savings_total,
                              fund_total=fund_total,
                              stock_total=stock_total,
                              total_assets=total_assets,
                              total_target=float(total_target),
                              total_saved=float(total_saved),
                              overall_progress=min(overall_progress, 100),
                              checklist=checklist,
                              checklist_items=CHECKLIST_ITEMS,
                              required_completed=required_completed,
                              total_required=total_required,
                              checklist_rate=checklist_rate,
                              show_todo_popup=show_todo_popup,
                              pending_required=pending_required,
                              current_view=current_view,
                              family=family,
                              username=session.get('nickname', session.get('username', '用户')))

    # --- 注册添加交易路由 ---
    @application.route('/add', methods=['POST'])
    def add_transaction():
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))

        transaction_type = request.form.get('type')
        amount = request.form.get('amount')
        category_id = request.form.get('category')
        transaction_date_str = request.form.get('date')
        description = request.form.get('description')

        if not all([transaction_type, amount, category_id, transaction_date_str]):
            return "缺少必填字段", 400

        try:
            amount_val = float(amount)
            if amount_val <= 0 or amount_val > 9999999:
                flash('金额必须在 0 ~ 9,999,999 之间', 'error')
                return redirect(url_for('transaction.transaction_list'))
        except (ValueError, TypeError):
            flash('金额格式错误', 'error')
            return redirect(url_for('transaction.transaction_list'))

        try:
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
        except ValueError:
            return "日期格式错误", 400

        transaction = Transaction(
            amount=Decimal(amount),
            type=transaction_type,
            category_id=int(category_id),
            description=description or None,
            transaction_date=transaction_date,
            user_id=user_id
        )
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('transaction.transaction_list'))

    # --- 注册编辑交易路由 ---
    @application.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
    def edit_transaction(transaction_id):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))

        transaction = Transaction.query.get_or_404(transaction_id)
        user = User.query.get(user_id)

        if transaction.user_id != user_id:
            if not (user.family_id and user.family_id == transaction.user.family_id):
                return "无权编辑此交易", 403

        if request.method == 'GET':
            categories = Category.query.filter(
                (Category.user_id == None) | (Category.user_id == user_id)
            ).all()
            accounts = Account.query.filter_by(user_id=user_id).all()
            return render_template('edit_transaction.html',
                                  transaction=transaction,
                                  categories=categories,
                                  accounts=accounts,
                                  username=session.get('nickname', session.get('username', '用户')),
                                  page_title='编辑交易')

        return redirect(url_for('transaction.transaction_list'))

    # --- 注册删除交易路由 ---
    @application.route('/delete/<int:transaction_id>', methods=['POST'])
    def delete_transaction(transaction_id):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))

        transaction = Transaction.query.get_or_404(transaction_id)
        user = User.query.get(user_id)

        if transaction.user_id != user_id:
            if not (user.family_id and user.family_id == transaction.user.family_id):
                return "无权删除此交易", 403

        db.session.delete(transaction)
        db.session.commit()
        return redirect(url_for('transaction.transaction_list'))

    # --- 注册蓝图 ---
    from routes.auth import auth_bp
    from routes.account import account_bp
    from routes.category import category_bp
    from routes.savings import savings_bp
    from routes.baby_fund import baby_fund_bp
    from routes.upload import upload_bp
    from routes.family import family_bp
    from routes.transaction import transaction_bp
    from routes.reports import reports_bp
    from routes.template import template_bp
    from routes.recurring import recurring_bp
    from routes.monthly_todo import monthly_todo_bp
    from routes.advisor import advisor_bp

    application.register_blueprint(auth_bp)
    application.register_blueprint(account_bp)
    application.register_blueprint(category_bp)
    application.register_blueprint(savings_bp)
    application.register_blueprint(baby_fund_bp)
    application.register_blueprint(upload_bp)
    application.register_blueprint(family_bp)
    application.register_blueprint(transaction_bp)
    application.register_blueprint(reports_bp)
    application.register_blueprint(template_bp)
    application.register_blueprint(recurring_bp)
    application.register_blueprint(monthly_todo_bp)
    application.register_blueprint(advisor_bp)

    with application.app_context():
        db.create_all()
        for cat_data in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=cat_data['name']).first():
                db.session.add(Category(**cat_data))
        for at_data in DEFAULT_ACCOUNT_TYPES:
            if not AccountType.query.filter_by(name=at_data['name']).first():
                db.session.add(AccountType(**at_data))
        db.session.commit()

    yield application
    os.unlink(db_path)


@pytest.fixture
def main_client(main_app):
    """未登录的测试客户端"""
    return main_app.test_client()


@pytest.fixture
def main_logged_in_client(main_app):
    """已登录的测试客户端"""
    with main_app.app_context():
        user = User(username='testuser', nickname='测试用户')
        user.set_password('Test1234')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = main_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'testuser'
        sess['nickname'] = '测试用户'
    return client


class TestIndexRoute:
    """首页仪表盘路由测试"""

    def test_unauthenticated_redirects_to_login(self, main_client):
        """未登录访问首页重定向到登录页"""
        resp = main_client.get('/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_authenticated_index_returns_200(self, main_logged_in_client):
        """登录后访问首页返回 200"""
        resp = main_logged_in_client.get('/')
        assert resp.status_code == 200


class TestAddTransaction:
    """添加交易路由测试"""

    def test_add_income_success(self, main_app, main_logged_in_client):
        """添加收入交易成功"""
        with main_app.app_context():
            cat = Category.query.filter_by(type='income').first()
            cat_id = cat.id

        resp = main_logged_in_client.post('/add', data={
            'type': 'income',
            'amount': '5000.00',
            'category': str(cat_id),
            'date': date.today().strftime('%Y-%m-%d'),
            'description': '工资收入'
        }, follow_redirects=False)
        assert resp.status_code == 302

        with main_app.app_context():
            txn = Transaction.query.filter_by(description='工资收入').first()
            assert txn is not None
            assert float(txn.amount) == 5000.00
            assert txn.type == 'income'

    def test_add_expense_success(self, main_app, main_logged_in_client):
        """添加支出交易成功"""
        with main_app.app_context():
            cat = Category.query.filter_by(type='expense').first()
            cat_id = cat.id

        resp = main_logged_in_client.post('/add', data={
            'type': 'expense',
            'amount': '120.50',
            'category': str(cat_id),
            'date': '2026-05-01',
            'description': '午餐费'
        }, follow_redirects=False)
        assert resp.status_code == 302

        with main_app.app_context():
            txn = Transaction.query.filter_by(description='午餐费').first()
            assert txn is not None
            assert float(txn.amount) == 120.50
            assert txn.type == 'expense'

    def test_add_transaction_missing_fields_returns_400(self, main_logged_in_client):
        """缺少必填字段返回 400"""
        resp = main_logged_in_client.post('/add', data={
            'type': 'income',
            'amount': '',
            'category': '',
            'date': ''
        })
        assert resp.status_code == 400
        assert '缺少必填字段' in resp.data.decode('utf-8')

    def test_add_transaction_invalid_date_returns_400(self, main_app, main_logged_in_client):
        """日期格式错误返回 400"""
        with main_app.app_context():
            cat = Category.query.filter_by(type='income').first()
            cat_id = cat.id

        resp = main_logged_in_client.post('/add', data={
            'type': 'income',
            'amount': '100',
            'category': str(cat_id),
            'date': 'not-a-date'
        })
        assert resp.status_code == 400
        assert '日期格式错误' in resp.data.decode('utf-8')


class TestEditTransaction:
    """编辑交易路由测试"""

    def test_edit_page_returns_200(self, main_app, main_logged_in_client):
        """编辑交易页面正常显示"""
        with main_app.app_context():
            user = User.query.filter_by(username='testuser').first()
            cat = Category.query.filter_by(type='expense').first()
            txn = Transaction(
                amount=Decimal('88.00'),
                type='expense',
                category_id=cat.id,
                transaction_date=date.today(),
                user_id=user.id,
                description='测试编辑'
            )
            db.session.add(txn)
            db.session.commit()
            txn_id = txn.id

        resp = main_logged_in_client.get(f'/edit/{txn_id}')
        assert resp.status_code == 200
        assert '测试编辑' in resp.data.decode('utf-8')


class TestDeleteTransaction:
    """删除交易路由测试"""

    def test_delete_transaction_success(self, main_app, main_logged_in_client):
        """删除交易成功"""
        with main_app.app_context():
            user = User.query.filter_by(username='testuser').first()
            cat = Category.query.filter_by(type='expense').first()
            txn = Transaction(
                amount=Decimal('50.00'),
                type='expense',
                category_id=cat.id,
                transaction_date=date.today(),
                user_id=user.id,
                description='即将删除'
            )
            db.session.add(txn)
            db.session.commit()
            txn_id = txn.id

        resp = main_logged_in_client.post(f'/delete/{txn_id}', follow_redirects=False)
        assert resp.status_code == 302

        with main_app.app_context():
            deleted = Transaction.query.get(txn_id)
            assert deleted is None

    def test_delete_nonexistent_returns_404(self, main_logged_in_client):
        """删除不存在的交易返回 404"""
        resp = main_logged_in_client.post('/delete/99999')
        assert resp.status_code == 404
