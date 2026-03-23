"""宝宝基金路由模块"""
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from sqlalchemy import func

from models import db, User, BabyFund, Transaction, TransactionModification, Account, Category

baby_fund_bp = Blueprint('baby_fund', __name__, url_prefix='/baby-fund')


def _get_family_member_ids(user_id, current_view):
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        return [m.id for m in user.family.members]
    return [user_id]


def _get_or_create_baby_category():
    """获取或创建'宝宝基金'收入分类"""
    cat = Category.query.filter_by(name='宝宝基金', type='income').first()
    if not cat:
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        db.session.flush()
    return cat


@baby_fund_bp.route('/')
def baby_fund_list():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    member_ids = _get_family_member_ids(user_id, current_view)

    funds = BabyFund.query.filter(
        BabyFund.created_by.in_(member_ids)
    ).order_by(BabyFund.event_date.desc()).all()

    total_amount = db.session.query(func.sum(BabyFund.amount)).filter(
        BabyFund.created_by.in_(member_ids)
    ).scalar() or Decimal('0')

    accounts = Account.query.filter(Account.user_id.in_(member_ids)).all()

    return render_template('baby_fund.html',
                           funds=funds,
                           total_amount=float(total_amount),
                           fund_count=len(funds),
                           accounts=accounts,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@baby_fund_bp.route('/add', methods=['POST'])
def add_fund():
    user_id = session.get('user_id')
    giver_name = request.form.get('giver_name')
    amount = request.form.get('amount')
    event_date_str = request.form.get('event_date')
    event_type = request.form.get('event_type')
    account_id = request.form.get('account_id', type=int)
    notes = request.form.get('notes')

    if not all([giver_name, amount, event_date_str]):
        flash('请填写所有必填字段')
        return redirect(url_for('baby_fund.baby_fund_list'))

    # event_type 校验
    if event_type and event_type not in BabyFund.VALID_EVENT_TYPES:
        flash('无效的事件类型')
        return redirect(url_for('baby_fund.baby_fund_list'))

    try:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('日期格式错误')
        return redirect(url_for('baby_fund.baby_fund_list'))

    cat = _get_or_create_baby_category()

    # 自动创建收入交易
    desc = f"宝宝基金: {giver_name}"
    if event_type:
        desc += f" ({event_type})"

    txn = Transaction(
        amount=Decimal(amount), type='income',
        category_id=cat.id, description=desc,
        transaction_date=event_date, user_id=user_id,
        account_id=account_id or None
    )
    db.session.add(txn)
    db.session.flush()  # get txn.id

    # 创建宝宝基金记录
    fund = BabyFund(
        giver_name=giver_name, amount=Decimal(amount),
        account_id=account_id or None, event_date=event_date,
        event_type=event_type or None, notes=notes or None,
        transaction_id=txn.id, created_by=user_id
    )
    db.session.add(fund)

    # 更新账户余额
    if account_id:
        account = Account.query.get(account_id)
        if account:
            account.current_balance = account.current_balance + Decimal(amount)

    db.session.commit()
    return redirect(url_for('baby_fund.baby_fund_list'))


@baby_fund_bp.route('/<int:fund_id>/edit', methods=['POST'])
def edit_fund(fund_id):
    fund = BabyFund.query.get_or_404(fund_id)

    new_giver = request.form.get('giver_name', fund.giver_name)
    new_amount = request.form.get('amount', str(fund.amount))
    new_event_date_str = request.form.get('event_date')
    new_event_type = request.form.get('event_type', fund.event_type)

    if new_event_type and new_event_type not in BabyFund.VALID_EVENT_TYPES:
        flash('无效的事件类型')
        return redirect(url_for('baby_fund.baby_fund_list'))

    try:
        new_event_date = datetime.strptime(new_event_date_str, '%Y-%m-%d').date() if new_event_date_str else fund.event_date
    except ValueError:
        flash('日期格式错误')
        return redirect(url_for('baby_fund.baby_fund_list'))

    fund.giver_name = new_giver
    fund.amount = Decimal(new_amount)
    fund.event_date = new_event_date
    fund.event_type = new_event_type
    fund.notes = request.form.get('notes', fund.notes)

    # 同步更新关联交易
    if fund.transaction_id:
        txn = Transaction.query.get(fund.transaction_id)
        if txn:
            txn.amount = Decimal(new_amount)
            desc = f"宝宝基金: {new_giver}"
            if new_event_type:
                desc += f" ({new_event_type})"
            txn.description = desc
            txn.transaction_date = new_event_date

    db.session.commit()
    return redirect(url_for('baby_fund.baby_fund_list'))


@baby_fund_bp.route('/<int:fund_id>/delete', methods=['POST'])
def delete_fund(fund_id):
    fund = BabyFund.query.get_or_404(fund_id)

    # 级联删除：先删 TransactionModification，再删 Transaction
    if fund.transaction_id:
        txn = Transaction.query.get(fund.transaction_id)
        if txn:
            # 反向修正账户余额
            if txn.account_id:
                account = Account.query.get(txn.account_id)
                if account:
                    account.current_balance = account.current_balance - txn.amount

            # 删除修改记录
            TransactionModification.query.filter_by(transaction_id=txn.id).delete()
            db.session.delete(txn)

    db.session.delete(fund)
    db.session.commit()
    return redirect(url_for('baby_fund.baby_fund_list'))
