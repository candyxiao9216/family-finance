"""定期交易路由模块"""
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, session, url_for, flash

from models import db, User, RecurringTransaction, Transaction, Category, Account

recurring_bp = Blueprint('recurring', __name__, url_prefix='/recurring')


def _calculate_next_run(item):
    """计算下一次执行日期"""
    current = item.next_run_date
    if item.frequency == 'monthly':
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        day = min(item.day_of_month or current.day, 28)
        return date(year, month, day)
    elif item.frequency == 'weekly':
        return current + timedelta(days=7)
    elif item.frequency == 'custom' and item.interval_days:
        return current + timedelta(days=item.interval_days)
    return current + timedelta(days=30)


def process_recurring_transactions(user_id):
    """处理到期的定期交易，返回创建的交易数量"""
    today = date.today()
    due_items = RecurringTransaction.query.filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_run_date <= today
    ).all()

    count = 0
    for item in due_items:
        while item.next_run_date <= today:
            txn = Transaction(
                user_id=item.user_id,
                amount=item.amount,
                type=item.type,
                category_id=item.category_id,
                description=f"[定期] {item.description or item.name}",
                transaction_date=item.next_run_date,
                source='recurring',
                account_id=item.account_id
            )
            db.session.add(txn)

            # 更新关联账户余额
            if item.account_id:
                account = Account.query.get(item.account_id)
                if account:
                    if item.type == 'income':
                        account.current_balance = account.current_balance + item.amount
                    else:
                        account.current_balance = account.current_balance - item.amount

            item.next_run_date = _calculate_next_run(item)
            count += 1

    if count:
        db.session.commit()
    return count


@recurring_bp.route('/')
def recurring_list():
    """定期交易列表页"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    items = RecurringTransaction.query.filter_by(user_id=user_id)\
        .order_by(RecurringTransaction.is_active.desc(), RecurringTransaction.next_run_date).all()

    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()
    accounts = Account.query.filter_by(user_id=user_id).all()

    return render_template('recurring.html',
                           items=items,
                           categories=categories,
                           accounts=accounts,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@recurring_bp.route('/add', methods=['POST'])
def add_recurring():
    """创建定期交易"""
    user_id = session.get('user_id')
    name = request.form.get('name')
    amount = request.form.get('amount')
    rec_type = request.form.get('type')
    frequency = request.form.get('frequency')
    category_id = request.form.get('category_id', type=int)
    account_id = request.form.get('account_id', type=int)
    description = request.form.get('description')
    day_of_month = request.form.get('day_of_month', type=int)
    day_of_week = request.form.get('day_of_week', type=int)
    interval_days = request.form.get('interval_days', type=int)

    if not all([name, amount, rec_type, frequency]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('recurring.recurring_list'))

    # 计算首次 next_run_date
    today = date.today()
    if frequency == 'monthly':
        day = min(day_of_month or 1, 28)
        if today.day <= day:
            next_run = date(today.year, today.month, day)
        else:
            month = today.month + 1
            year = today.year
            if month > 12:
                month = 1
                year += 1
            next_run = date(year, month, day)
    elif frequency == 'weekly':
        # day_of_week: 0=周一 ... 6=周日
        dow = day_of_week if day_of_week is not None else 0
        days_ahead = dow - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        next_run = today + timedelta(days=days_ahead)
        if days_ahead == 0:
            next_run = today  # 今天就是目标日
    elif frequency == 'custom' and interval_days:
        next_run = today + timedelta(days=interval_days)
    else:
        next_run = today + timedelta(days=30)

    item = RecurringTransaction(
        user_id=user_id,
        name=name,
        amount=Decimal(amount),
        type=rec_type,
        frequency=frequency,
        category_id=category_id or None,
        account_id=account_id or None,
        description=description or None,
        day_of_month=day_of_month if frequency == 'monthly' else None,
        day_of_week=day_of_week if frequency == 'weekly' else None,
        interval_days=interval_days if frequency == 'custom' else None,
        next_run_date=next_run,
        is_active=True
    )
    db.session.add(item)
    db.session.commit()

    flash('定期交易创建成功', 'success')
    return redirect(url_for('recurring.recurring_list'))


@recurring_bp.route('/<int:item_id>/toggle', methods=['POST'])
def toggle_recurring(item_id):
    """切换定期交易的启用/暂停状态"""
    item = RecurringTransaction.query.get_or_404(item_id)
    item.is_active = not item.is_active

    # 重新启用时，如果 next_run_date 已过期，设为今天
    if item.is_active and item.next_run_date < date.today():
        item.next_run_date = date.today()

    db.session.commit()
    flash(f'定期交易已{"启用" if item.is_active else "暂停"}', 'success')
    return redirect(url_for('recurring.recurring_list'))


@recurring_bp.route('/<int:item_id>/delete', methods=['POST'])
def delete_recurring(item_id):
    """删除定期交易"""
    item = RecurringTransaction.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('定期交易已删除', 'success')
    return redirect(url_for('recurring.recurring_list'))
