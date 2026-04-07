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
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Transaction.query.filter(user_filter)\
        .order_by(Transaction.transaction_date.desc())\
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
        ).label('expense')
    ).first()

    monthly_income = month_stats.income or Decimal('0')
    monthly_expense = month_stats.expense or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    # 获取分类
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()

    # 获取账户列表
    accounts = Account.query.filter_by(user_id=user_id).all()

    # 获取快捷模板
    quick_templates = TransactionTemplate.query.filter_by(user_id=user_id)\
        .order_by(TransactionTemplate.use_count.desc()).limit(6).all()

    return render_template('transactions.html',
                          transactions=transactions,
                          pagination=pagination,
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
                          username=session.get('nickname', session.get('username', '用户')),
                          page_title='月度收支')
