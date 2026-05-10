from datetime import date, datetime, timedelta
from decimal import Decimal

# TODO: [安全] 添加 CSRF 防护（flask-wtf），当前为家庭内部应用暂未实施
from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func, extract, case

from database import create_app, init_database
from models import db, Transaction, Category, User, Family, TransactionModification, Account, AccountBalance, TransactionTemplate, SavingsPlan, SavingsRecord, MonthlyTodo
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
from routes.monthly_todo import monthly_todo_bp
from routes.advisor import advisor_bp
from routes.settings import settings_bp
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
app.register_blueprint(monthly_todo_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(advisor_bp)
app.register_blueprint(settings_bp)

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
    current_view = request.args.get('view', 'family' if family else 'personal')
    if current_view == 'family' and not family:
        current_view = 'personal'

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
    fund_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'fund']
    stock_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'stock']

    savings_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in savings_accounts)
    fund_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in fund_accounts)
    stock_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in stock_accounts)
    total_assets = savings_total + fund_total + stock_total

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

    # --- 模块 4：月度待办 Checklist ---
    from routes.monthly_todo import ensure_monthly_checklist, CHECKLIST_ITEMS
    checklist = ensure_monthly_checklist(user_id, current_year, current_month)
    checklist.sort(key=lambda t: t.priority, reverse=True)

    required_todos = [t for t in checklist if t.is_required]
    required_completed = sum(1 for t in required_todos if t.status == 'completed')
    total_required = len(required_todos)
    checklist_rate = (required_completed / total_required * 100) if total_required > 0 else 0

    # 弹窗逻辑：当月有未完成必选项 + 本次登录还没弹过
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


@app.route('/add', methods=['POST'])
def add_transaction():
    """添加交易"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction_type = request.form.get('type')
    amount = request.form.get('amount')
    transaction_date_str = request.form.get('date')
    description = request.form.get('description')

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

    # === 转账逻辑 ===
    if transaction_type == 'transfer':
        from_account_id = request.form.get('from_account_id', type=int)
        to_account_id = request.form.get('to_account_id', type=int)

        if not from_account_id or not to_account_id:
            flash('请选择转出和转入账户', 'error')
            return redirect(url_for('transaction.transaction_list'))
        if from_account_id == to_account_id:
            flash('转出和转入账户不能相同', 'error')
            return redirect(url_for('transaction.transaction_list'))

        from_account = Account.query.get(from_account_id)
        to_account = Account.query.get(to_account_id)
        transfer_amount = Decimal(amount)

        # 转出记录
        txn_out = Transaction(
            amount=transfer_amount,
            type='transfer_out',
            category_id=None,
            description=description or f'转账→{to_account.name}',
            transaction_date=transaction_date,
            user_id=user_id,
            account_id=from_account_id
        )
        # 转入记录
        txn_in = Transaction(
            amount=transfer_amount,
            type='transfer_in',
            category_id=None,
            description=description or f'转账←{from_account.name}',
            transaction_date=transaction_date,
            user_id=user_id,
            account_id=to_account_id
        )
        db.session.add(txn_out)
        db.session.add(txn_in)
        db.session.flush()  # 获取 id

        # 互相引用
        txn_out.transfer_pair_id = txn_in.id
        txn_in.transfer_pair_id = txn_out.id

        # 更新账户余额
        from_account.current_balance = from_account.current_balance - transfer_amount
        to_account.current_balance = to_account.current_balance + transfer_amount

        # 插入变更记录
        this_month = transaction_date.replace(day=1)
        bal_out = AccountBalance(
            account_id=from_account_id,
            balance=from_account.current_balance,
            change_amount=-transfer_amount,
            record_month=this_month,
            source='transfer',
            recorded_by=user_id
        )
        bal_in = AccountBalance(
            account_id=to_account_id,
            balance=to_account.current_balance,
            change_amount=transfer_amount,
            record_month=this_month,
            source='transfer',
            recorded_by=user_id
        )
        db.session.add(bal_out)
        db.session.add(bal_in)
        db.session.commit()

        return redirect(url_for('transaction.transaction_list'))

    # === 普通收入/支出逻辑 ===
    category_id = request.form.get('category')
    account_id = request.form.get('account_id', type=int)

    if not all([transaction_type, amount, category_id, transaction_date_str]):
        return "缺少必填字段", 400

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
                              username=session.get('nickname', session.get('username', '用户')),
                              page_title='编辑交易')

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
        # 先记录旧值用于字段对比
        old_account_id = transaction.account_id
        old_amount = transaction.amount
        old_type = transaction.type

        # 更新交易的 account_id
        transaction.account_id = new_account_id

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

    # 转账联动删除：删配对记录 + 回滚余额 + 删变更记录
    if transaction.type in ('transfer_out', 'transfer_in') and transaction.transfer_pair_id:
        pair = Transaction.query.get(transaction.transfer_pair_id)

        # 找出哪个是 out、哪个是 in
        if transaction.type == 'transfer_out':
            txn_out, txn_in = transaction, pair
        else:
            txn_out, txn_in = pair, transaction

        # 回滚余额
        if txn_out and txn_out.account_id:
            from_account = Account.query.get(txn_out.account_id)
            if from_account:
                from_account.current_balance = from_account.current_balance + txn_out.amount
        if txn_in and txn_in.account_id:
            to_account = Account.query.get(txn_in.account_id)
            if to_account:
                to_account.current_balance = to_account.current_balance - txn_in.amount

        # 删除对应的变更记录
        this_month = transaction.transaction_date.replace(day=1)
        if txn_out and txn_out.account_id:
            AccountBalance.query.filter_by(
                account_id=txn_out.account_id, record_month=this_month, source='transfer'
            ).filter(AccountBalance.change_amount == -txn_out.amount).delete()
        if txn_in and txn_in.account_id:
            AccountBalance.query.filter_by(
                account_id=txn_in.account_id, record_month=this_month, source='transfer'
            ).filter(AccountBalance.change_amount == txn_in.amount).delete()

        # 删除配对记录
        if pair:
            db.session.delete(pair)

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
