"""
账户管理路由模块
"""
from datetime import datetime, date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, render_template, request, session, url_for, flash

from models import db, Account, AccountType, AccountBalance, User

account_bp = Blueprint('account', __name__, url_prefix='/accounts')


def _get_family_accounts(user_id, current_view):
    """获取当前视图下的所有账户"""
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        family_member_ids = [m.id for m in user.family.members]
        return Account.query.filter(Account.user_id.in_(family_member_ids)).all()
    return Account.query.filter_by(user_id=user_id).all()


@account_bp.route('/')
def account_list():
    """账户管理页"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    if current_view == 'family' and not family:
        current_view = 'personal'

    accounts = _get_family_accounts(user_id, current_view)
    account_types = AccountType.query.all()

    # 按类型分组
    savings_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'savings']
    investment_accounts = [a for a in accounts if a.account_type and a.account_type.category == 'investment']

    # 计算各组合计
    savings_total = sum(float(a.current_balance) for a in savings_accounts)
    investment_total = sum(float(a.current_balance) for a in investment_accounts)

    # 获取本月快照记录
    this_month = date.today().replace(day=1)
    account_ids = [a.id for a in accounts]
    snapshots = {}
    if account_ids:
        records = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids),
            AccountBalance.record_month == this_month
        ).all()
        for r in records:
            snapshots[r.account_id] = r

    # 获取每个账户的最新快照（用于显示余额对应的月份）
    latest_snapshots = {}
    for a in accounts:
        latest = AccountBalance.query.filter_by(
            account_id=a.id
        ).order_by(AccountBalance.record_month.desc()).first()
        if latest:
            latest_snapshots[a.id] = latest

    # 获取所有快照记录（按月份降序），用于展示历史记录
    all_snapshots = []
    if account_ids:
        all_snapshots = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids)
        ).order_by(AccountBalance.record_month.desc(), AccountBalance.created_at.desc()).all()

    # 获取上月快照（用于批量录入面板显示上月余额）
    prev_month = this_month - relativedelta(months=1)
    prev_snapshots = {}
    if account_ids:
        prev_records = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids),
            AccountBalance.record_month == prev_month
        ).all()
        for r in prev_records:
            prev_snapshots[r.account_id] = r

    return render_template('accounts.html',
                           savings_accounts=savings_accounts,
                           investment_accounts=investment_accounts,
                           savings_total=savings_total,
                           investment_total=investment_total,
                           account_types=account_types,
                           snapshots=snapshots,
                           prev_snapshots=prev_snapshots,
                           latest_snapshots=latest_snapshots,
                           all_snapshots=all_snapshots,
                           exchange_rates=_get_exchange_rates(),
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@account_bp.route('/create', methods=['POST'])
def create_account():
    """创建账户"""
    user_id = session.get('user_id')
    name = request.form.get('name', '').strip()
    type_id = request.form.get('type_id', type=int)
    initial_balance = request.form.get('initial_balance', '0')
    currency = request.form.get('currency', 'CNY')

    if not name or not type_id:
        return "缺少必填字段", 400

    account = Account(
        user_id=user_id,
        name=name,
        type_id=type_id,
        currency=currency,
        initial_balance=Decimal(initial_balance),
        current_balance=Decimal(initial_balance)
    )
    db.session.add(account)
    db.session.commit()

    return redirect(url_for('account.account_list'))


@account_bp.route('/<int:account_id>/snapshot', methods=['POST'])
def add_snapshot(account_id):
    """录入月度余额快照"""
    user_id = session.get('user_id')
    account = Account.query.get_or_404(account_id)

    # 权限检查
    user = User.query.get(user_id)
    if account.user_id != user_id:
        if not (user.family_id and user.family_id == account.owner.family_id):
            return "无权操作此账户", 403

    balance_str = request.form.get('balance', '0')
    month_str = request.form.get('month')  # 格式 YYYY-MM

    if not month_str:
        return "缺少月份", 400

    record_month = datetime.strptime(month_str + '-01', '%Y-%m-%d').date()
    balance = Decimal(balance_str)

    # 查询上月快照计算变化量
    prev_month = record_month - relativedelta(months=1)
    prev_record = AccountBalance.query.filter_by(
        account_id=account_id, record_month=prev_month
    ).first()
    change_amount = balance - Decimal(str(prev_record.balance)) if prev_record else None

    # 插入或更新
    existing = AccountBalance.query.filter_by(
        account_id=account_id, record_month=record_month
    ).first()

    if existing:
        existing.balance = balance
        existing.change_amount = change_amount
        existing.recorded_by = user_id
    else:
        snapshot = AccountBalance(
            account_id=account_id, balance=balance,
            change_amount=change_amount, record_month=record_month,
            recorded_by=user_id
        )
        db.session.add(snapshot)

    # 只有录入的月份是最新的，才更新账户当前余额
    latest_snapshot = AccountBalance.query.filter_by(
        account_id=account_id
    ).order_by(AccountBalance.record_month.desc()).first()

    if latest_snapshot and latest_snapshot.record_month <= record_month:
        account.current_balance = balance
    elif not latest_snapshot:
        account.current_balance = balance

    db.session.commit()

    return redirect(url_for('account.account_list'))


# 汇率（带缓存，每小时刷新一次）
import time
import urllib.request
import json

_rate_cache = {'rates': {'CNY': 1.0, 'HKD': 0.923, 'USD': 7.25}, 'ts': 0}


def _get_exchange_rates():
    """获取实时汇率（CNY 为基准），失败时用缓存"""
    now = time.time()
    if now - _rate_cache['ts'] < 3600:  # 1 小时缓存
        return _rate_cache['rates']
    try:
        url = 'https://api.exchangerate-api.com/v4/latest/CNY'
        req = urllib.request.Request(url, headers={'User-Agent': 'FamilyFinance/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            # API 返回的是 1 CNY = X 外币，我们需要 1 外币 = X CNY
            rates = {
                'CNY': 1.0,
                'HKD': round(1.0 / data['rates'].get('HKD', 0.1083), 4),
                'USD': round(1.0 / data['rates'].get('USD', 0.1379), 4),
            }
            _rate_cache['rates'] = rates
            _rate_cache['ts'] = now
            return rates
    except Exception:
        return _rate_cache['rates']


@account_bp.route('/batch-snapshot', methods=['POST'])
def batch_snapshot():
    """批量录入月度快照"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    month_str = request.form.get('month')

    if not month_str:
        flash('请选择月份', 'error')
        return redirect(url_for('account.account_list'))

    record_month = datetime.strptime(month_str + '-01', '%Y-%m-%d').date()

    # 获取所有可操作账户
    current_view = request.form.get('view', 'personal')
    accounts = _get_family_accounts(user_id, current_view)

    count = 0
    for account in accounts:
        balance_str = request.form.get(f'balance_{account.id}', '').strip()
        note = request.form.get(f'note_{account.id}', '').strip()
        currency = request.form.get(f'currency_{account.id}', '').strip()

        if not balance_str:
            continue  # 跳过未填写的账户

        # 更新投资账户币种
        if currency and currency in ('CNY', 'HKD', 'USD'):
            account.currency = currency

        balance = Decimal(balance_str)

        # 计算变化量
        prev_month = record_month - relativedelta(months=1)
        prev_record = AccountBalance.query.filter_by(
            account_id=account.id, record_month=prev_month
        ).first()
        change_amount = balance - Decimal(str(prev_record.balance)) if prev_record else None

        # 插入或更新
        existing = AccountBalance.query.filter_by(
            account_id=account.id, record_month=record_month
        ).first()

        if existing:
            existing.balance = balance
            existing.change_amount = change_amount
            existing.note = note or None
            existing.recorded_by = user_id
        else:
            snapshot = AccountBalance(
                account_id=account.id, balance=balance,
                change_amount=change_amount, record_month=record_month,
                note=note or None, recorded_by=user_id
            )
            db.session.add(snapshot)

        # 更新账户当前余额
        latest_snapshot = AccountBalance.query.filter_by(
            account_id=account.id
        ).order_by(AccountBalance.record_month.desc()).first()

        if latest_snapshot and latest_snapshot.record_month <= record_month:
            account.current_balance = balance
        elif not latest_snapshot:
            account.current_balance = balance

        count += 1

    db.session.commit()
    flash(f'已录入 {count} 个账户的快照', 'success')
    return redirect(url_for('account.account_list'))


@account_bp.route('/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """删除账户"""
    user_id = session.get('user_id')
    account = Account.query.get_or_404(account_id)

    if account.user_id != user_id:
        return "无权删除此账户", 403

    # 删除关联的快照记录
    AccountBalance.query.filter_by(account_id=account_id).delete()
    # 清除关联交易的 account_id
    from models import Transaction
    Transaction.query.filter_by(account_id=account_id).update({'account_id': None})
    db.session.delete(account)
    db.session.commit()

    return redirect(url_for('account.account_list'))
