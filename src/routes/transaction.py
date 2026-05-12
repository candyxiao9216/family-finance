"""月度收支路由模块 — 从原首页迁移的记账功能"""
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from sqlalchemy import func, extract, case

from models import db, Transaction, Category, User, Account, TransactionTemplate

transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')


@transaction_bp.route('/')
def transaction_list():
    """月度收支页 — 记账表单 + 交易列表 + 分页 + 快捷模板"""
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

    # 确定查询范围
    if current_view == 'family' and family:
        family_member_ids = [m.id for m in family.members]
        user_filter = Transaction.user_id.in_(family_member_ids)
        family_members = family.members
    else:
        current_view = 'personal'
        user_filter = (Transaction.user_id == user_id)
        family_members = []

    # 获取交易列表，按日期降序（分页，每页 10 条）
    # 转账只显示 transfer_out（合并为一条），隐藏 transfer_in
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Transaction.query.filter(
        user_filter,
        Transaction.type != 'transfer_in'
    ).order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

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
        ).label('expense'),
        func.sum(
            case(
                ((Transaction.type == 'transfer_out') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & user_filter, Transaction.amount)
            )
        ).label('transfer')
    ).first()

    monthly_income = month_stats.income or Decimal('0')
    monthly_expense = month_stats.expense or Decimal('0')
    monthly_transfer = month_stats.transfer or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    # 获取分类
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()

    # 获取账户列表（家庭视图显示全家，按成员分组）
    if current_view == 'family' and family:
        family_accounts = {}  # {member: [accounts]}
        for member in family.members:
            member_accounts = Account.query.filter_by(user_id=member.id).all()
            if member_accounts:
                family_accounts[member] = member_accounts
        accounts = Account.query.filter(Account.user_id.in_(family_member_ids)).all()
    else:
        family_accounts = {}
        accounts = Account.query.filter_by(user_id=user_id).all()

    # 获取快捷模板
    quick_templates = TransactionTemplate.query.filter_by(user_id=user_id)\
        .order_by(TransactionTemplate.use_count.desc()).limit(6).all()

    # 获取「最近常用」：按分类分组，取近3个月出现次数最多的Top 5，金额取该分类最近一笔
    # 跟随视图：个人视图查自己的，家庭视图查全家的
    from datetime import timedelta
    three_months_ago = date.today() - timedelta(days=90)

    # 收入常用
    income_frequent = db.session.query(
        Category.name,
        func.count(Transaction.id).label('cnt'),
        func.max(Transaction.amount).label('last_amount')
    ).join(Category, Transaction.category_id == Category.id)\
     .filter(user_filter, Transaction.type == 'income',
             Transaction.transaction_date >= three_months_ago)\
     .group_by(Category.name)\
     .order_by(func.count(Transaction.id).desc())\
     .limit(5).all()

    # 支出常用
    expense_frequent = db.session.query(
        Category.name,
        func.count(Transaction.id).label('cnt'),
        func.max(Transaction.amount).label('last_amount')
    ).join(Category, Transaction.category_id == Category.id)\
     .filter(user_filter, Transaction.type == 'expense',
             Transaction.transaction_date >= three_months_ago)\
     .group_by(Category.name)\
     .order_by(func.count(Transaction.id).desc())\
     .limit(5).all()

    # 转账常用（按 from→to 账户对分组，带上账户ID）
    # 转账按账户归属过滤：个人视图只显示自己账户发起的转账
    if current_view == 'family' and family:
        transfer_account_filter = Transaction.account_id.in_(
            [a.id for a in Account.query.filter(Account.user_id.in_(family_member_ids)).all()]
        )
    else:
        transfer_account_filter = Transaction.account_id.in_(
            [a.id for a in Account.query.filter_by(user_id=user_id).all()]
        )

    transfer_frequent_raw = db.session.query(
        Transaction.account_id,
        Transaction.transfer_pair_id,
        Transaction.description,
        func.count(Transaction.id).label('cnt'),
        func.max(Transaction.amount).label('last_amount')
    ).filter(transfer_account_filter, Transaction.type == 'transfer_out',
             Transaction.transaction_date >= three_months_ago)\
     .group_by(Transaction.account_id, Transaction.transfer_pair_id, Transaction.description)\
     .order_by(func.count(Transaction.id).desc())\
     .limit(5).all()

    # 构造转账常用数据（包含 from/to account_id）
    transfer_shortcuts = []
    for r in transfer_frequent_raw:
        to_account_id = None
        if r.transfer_pair_id:
            pair = Transaction.query.get(r.transfer_pair_id)
            if pair:
                to_account_id = pair.account_id
        transfer_shortcuts.append({
            'name': r.description or '转账',
            'amount': float(r.last_amount),
            'from_account_id': r.account_id,
            'to_account_id': to_account_id,
        })

    recent_shortcuts = {
        'income': [{'name': r.name, 'amount': float(r.last_amount)} for r in income_frequent],
        'expense': [{'name': r.name, 'amount': float(r.last_amount)} for r in expense_frequent],
        'transfer': transfer_shortcuts,
    }

    return render_template('transactions.html',
                          transactions=transactions,
                          pagination=pagination,
                          monthly_income=float(monthly_income),
                          monthly_expense=float(monthly_expense),
                          monthly_balance=float(monthly_balance),
                          monthly_transfer=float(monthly_transfer),
                          stat_year=current_year,
                          stat_month=current_month,
                          categories=categories,
                          accounts=accounts,
                          family_accounts=family_accounts,
                          quick_templates=quick_templates,
                          recent_shortcuts=recent_shortcuts,
                          current_view=current_view,
                          family=family,
                          family_members=family_members,
                          username=session.get('nickname', session.get('username', '用户')),
                          page_title='月度收支')
