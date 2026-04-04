from datetime import date, datetime, timedelta
from decimal import Decimal

# TODO: [安全] 添加 CSRF 防护（flask-wtf），当前为家庭内部应用暂未实施
from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func, extract, case

from database import create_app, init_database
from models import db, Transaction, Category, User, Family, TransactionModification, Account, TransactionTemplate, SavingsPlan, SavingsRecord
from routes.auth import auth_bp
from routes.family import family_bp
from routes.category import category_bp
from routes.reports import reports_bp
from routes.account import account_bp
from routes.savings import savings_bp
from routes.baby_fund import baby_fund_bp
from routes.upload import upload_bp
from routes.template import template_bp
from routes.recurring import recurring_bp
from routes.transaction import transaction_bp
from flask import session, flash

app = create_app()


@app.context_processor
def inject_timedelta():
    return dict(timedelta=timedelta)

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(family_bp)
app.register_blueprint(category_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(account_bp)
app.register_blueprint(savings_bp)
app.register_blueprint(baby_fund_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(template_bp)
app.register_blueprint(recurring_bp)
app.register_blueprint(transaction_bp)

@app.before_request
def require_login():
    """登录状态检查"""
    # 允许访问的公开路由
    allowed_routes = ['auth.login', 'auth.register', 'static', 'family.family_info', 'family.family_members']

    if request.endpoint and request.endpoint not in allowed_routes:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))


# 安全修复：已删除 /init-db 公开路由，生产环境通过 deploy.sh CLI 初始化数据库


@app.route('/')
def index():
    """首页 — 三模块仪表盘（月度收支概览 + 资产总览 + 储蓄计划概览）"""
    user_id = session.get('user_id')

    # 自动执行到期的定期交易
    from routes.recurring import process_recurring_transactions
    recurring_count = process_recurring_transactions(user_id)
    if recurring_count:
        flash(f'已自动创建 {recurring_count} 笔定期交易', 'success')

    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = 'family' if family else 'personal'

    # --- 模块 1：月度收支概览 ---
    if current_view == 'family' and family:
        family_member_ids = [m.id for m in family.members]
        user_filter = Transaction.user_id.in_(family_member_ids)
    else:
        user_filter = (Transaction.user_id == user_id)

    current_month = date.today().month
    current_year = date.today().year

    month_stats = db.session.query(
        func.sum(
            case(
                ((Transaction.type == 'income') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & user_filter, Transaction.amount)
            )
        ).label('income'),
        func.sum(
            case(
                ((Transaction.type == 'expense') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & user_filter, Transaction.amount)
            )
        ).label('expense')
    ).first()

    monthly_income = float(month_stats.income or 0)
    monthly_expense = float(month_stats.expense or 0)
    monthly_balance = monthly_income - monthly_expense

    # --- 模块 2：资产总览 ---
    from routes.account import _get_family_accounts, _get_exchange_rates
    accounts = _get_family_accounts(user_id, current_view)
    rates = _get_exchange_rates()

    savings_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'savings']
    investment_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'investment']

    savings_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in savings_accounts)
    investment_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in investment_accounts)
    total_assets = savings_total + investment_total

    # --- 模块 3：储蓄计划概览 ---
    from routes.savings import _get_family_member_ids
    member_ids = _get_family_member_ids(user_id, current_view)

    plans = SavingsPlan.query.filter(
        SavingsPlan.created_by.in_(member_ids)
    ).all()

    total_target = Decimal('0')
    total_saved = Decimal('0')
    for plan in plans:
        saved = db.session.query(func.sum(SavingsRecord.amount)).filter(
            SavingsRecord.plan_id == plan.id
        ).scalar() or Decimal('0')
        total_target += plan.target_amount
        total_saved += saved

    overall_progress = float(total_saved / total_target * 100) if total_target else 0

    return render_template('index.html',
                          monthly_income=monthly_income,
                          monthly_expense=monthly_expense,
                          monthly_balance=monthly_balance,
                          stat_year=current_year,
                          stat_month=current_month,
                          savings_total=savings_total,
                          investment_total=investment_total,
                          total_assets=total_assets,
                          total_target=float(total_target),
                          total_saved=float(total_saved),
                          overall_progress=min(overall_progress, 100),
                          current_view=current_view,
                          family=family,
                          username=session.get('nickname', session.get('username', '用户')))


@app.route('/add', methods=['POST'])
def add_transaction():
    """添加交易"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction_type = request.form.get('type')
    amount = request.form.get('amount')
    category_id = request.form.get('category')
    transaction_date_str = request.form.get('date')
    description = request.form.get('description')
    account_id = request.form.get('account_id', type=int)

    # 基本验证
    if not all([transaction_type, amount, category_id, transaction_date_str]):
        return "缺少必填字段", 400

    # 金额范围校验
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

    # 创建交易记录
    transaction = Transaction(
        amount=Decimal(amount),
        type=transaction_type,
        category_id=int(category_id),
        description=description or None,
        transaction_date=transaction_date,
        user_id=user_id,
        account_id=account_id or None
    )

    db.session.add(transaction)

    # 如果关联了账户，更新账户余额
    if account_id:
        account = Account.query.get(account_id)
        if account:
            if transaction_type == 'income':
                account.current_balance = account.current_balance + Decimal(amount)
            else:
                account.current_balance = account.current_balance - Decimal(amount)

    db.session.commit()

    return redirect(url_for('transaction.transaction_list'))


@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    """编辑交易 - GET 显示编辑表单，POST 处理提交"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction = Transaction.query.get_or_404(transaction_id)
    user = User.query.get(user_id)

    # 权限检查：自己的交易或同一家庭的交易可编辑
    if transaction.user_id != user_id:
        if not (user.family_id and user.family_id == transaction.user.family_id):
            return "无权编辑此交易", 403

    if request.method == 'GET':
        # 显示编辑表单
        categories = Category.query.filter(
            (Category.user_id == None) | (Category.user_id == user_id)
        ).all()
        accounts = Account.query.filter_by(user_id=user_id).all()

        return render_template('edit_transaction.html',
                              transaction=transaction,
                              categories=categories,
                              accounts=accounts,
                              username=session.get('nickname', session.get('username', '用户')))

    # POST：处理编辑表单提交
    new_type = request.form.get('type')
    new_amount = request.form.get('amount')
    new_category_id = request.form.get('category')
    new_date_str = request.form.get('date')
    new_description = request.form.get('description')
    new_account_id = request.form.get('account_id', type=int) or None

    # 解析日期
    try:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
    except ValueError:
        return "日期格式错误", 400

    # 逐字段对比，记录变化
    modifications = []
    field_map = {
        'type': ('类型', str(transaction.type), new_type),
        'amount': ('金额', str(float(transaction.amount)), new_amount),
        'category_id': ('分类', str(transaction.category_id), new_category_id),
        'transaction_date': ('日期', str(transaction.transaction_date), new_date_str),
        'description': ('备注', transaction.description or '', new_description or ''),
        'account_id': ('关联账户', str(transaction.account_id or ''), str(new_account_id or '')),
    }

    for field, (label, old_val, new_val) in field_map.items():
        if old_val != new_val:
            mod = TransactionModification(
                transaction_id=transaction.id,
                modified_by=user_id,
                field_name=label,
                old_value=old_val,
                new_value=new_val
            )
            modifications.append(mod)

    # 如果有变化，更新记录
    if modifications:
        # 先处理账户余额修正（需要用旧值），再更新交易字段
        old_account_id = transaction.account_id
        old_amount = transaction.amount
        old_type = transaction.type

        # 反向修正旧账户余额
        if old_account_id:
            old_account = Account.query.get(old_account_id)
            if old_account:
                if old_type == 'income':
                    old_account.current_balance = old_account.current_balance - old_amount
                else:
                    old_account.current_balance = old_account.current_balance + old_amount

        # 更新交易的 account_id
        transaction.account_id = new_account_id

        # 正向更新新账户余额
        if new_account_id:
            new_account = Account.query.get(new_account_id)
            if new_account:
                if new_type == 'income':
                    new_account.current_balance = new_account.current_balance + Decimal(new_amount)
                else:
                    new_account.current_balance = new_account.current_balance - Decimal(new_amount)

        # 更新交易字段
        transaction.type = new_type
        transaction.amount = Decimal(new_amount)
        transaction.category_id = int(new_category_id)
        transaction.transaction_date = new_date
        transaction.description = new_description or None
        transaction.last_modified_by = user_id
        transaction.last_modified_at = datetime.utcnow()
        transaction.modification_count = (transaction.modification_count or 0) + 1

        for mod in modifications:
            db.session.add(mod)

        db.session.commit()

    return redirect(url_for('transaction.transaction_list'))


@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    """删除交易"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction = Transaction.query.get_or_404(transaction_id)
    user = User.query.get(user_id)

    # 权限检查：自己的交易或同一家庭的交易可删除
    if transaction.user_id != user_id:
        if not (user.family_id and user.family_id == transaction.user.family_id):
            return "无权删除此交易", 403

    # 反向修正关联账户余额
    if transaction.account_id:
        account = Account.query.get(transaction.account_id)
        if account:
            if transaction.type == 'income':
                account.current_balance = account.current_balance - transaction.amount
            else:
                account.current_balance = account.current_balance + transaction.amount

    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for('transaction.transaction_list'))


if __name__ == '__main__':
    import os
    # 首次运行时初始化数据库
    init_database(app)
    # 使用 5001 端口避免与 macOS AirPlay Receiver 冲突
    # 安全修复：debug 模式通过环境变量控制，生产环境禁止开启
    app.run(host='0.0.0.0', port=5001,
            debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')
