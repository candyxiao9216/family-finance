from datetime import date, datetime
from decimal import Decimal

from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func, extract, case

from database import create_app, init_database
from models import db, Transaction, Category, User, Family, TransactionModification, Account, TransactionTemplate
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
from flask import session, flash
from datetime import timedelta

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

@app.before_request
def require_login():
    """登录状态检查"""
    # 允许访问的公开路由
    allowed_routes = ['auth.login', 'auth.register', 'static', 'family.family_info', 'family.family_members']

    if request.endpoint and request.endpoint not in allowed_routes:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))


@app.route('/init-db')
def init_db_route():
    """初始化数据库（开发用路由）"""
    init_database(app)
    return "数据库初始化成功！<a href='/'>返回首页</a>"


@app.route('/')
def index():
    """首页 - 交易列表，支持个人/家庭视图切换"""
    user_id = session.get('user_id')

    # 自动执行到期的定期交易
    from routes.recurring import process_recurring_transactions
    recurring_count = process_recurring_transactions(user_id)
    if recurring_count:
        flash(f'已自动创建 {recurring_count} 笔定期交易', 'success')

    # 获取当前用户和家庭信息
    user = User.query.get(user_id)
    family = user.family if user else None

    # 读取视图参数：personal（个人）或 family（家庭）
    current_view = request.args.get('view', 'personal')

    # 确定查询范围：家庭视图且用户有家庭时，查询所有家庭成员的数据
    if current_view == 'family' and family:
        family_member_ids = [m.id for m in family.members]
        user_filter = Transaction.user_id.in_(family_member_ids)
        family_members = family.members
    else:
        # 个人视图或无家庭，回退到仅查询当前用户
        current_view = 'personal'
        user_filter = (Transaction.user_id == user_id)
        family_members = []

    # 获取交易列表，按日期降序
    transactions = Transaction.query.filter(user_filter).order_by(Transaction.transaction_date.desc()).all()

    # 计算本月统计
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

    monthly_income = month_stats.income or Decimal('0')
    monthly_expense = month_stats.expense or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    # 获取当前用户可用的分类（系统预设 + 用户自定义）
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()

    # 获取当前用户的账户列表（用于交易表单）
    accounts = Account.query.filter_by(user_id=user_id).all()

    # 获取快捷模板（按使用次数排序，最多 6 个）
    quick_templates = TransactionTemplate.query.filter_by(user_id=user_id)\
        .order_by(TransactionTemplate.use_count.desc()).limit(6).all()

    return render_template('index.html',
                          transactions=transactions,
                          monthly_income=float(monthly_income),
                          monthly_expense=float(monthly_expense),
                          monthly_balance=float(monthly_balance),
                          stat_year=current_year,
                          stat_month=current_month,
                          categories=categories,
                          accounts=accounts,
                          quick_templates=quick_templates,
                          current_view=current_view,
                          family=family,
                          family_members=family_members,
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

    return redirect(url_for('index'))


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

    return redirect(url_for('index'))


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

    return redirect(url_for('index'))


if __name__ == '__main__':
    # 首次运行时初始化数据库
    init_database(app)
    # 使用 5001 端口避免与 macOS AirPlay Receiver 冲突
    app.run(host='0.0.0.0', port=5001, debug=True)
