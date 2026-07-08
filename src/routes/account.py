"""
账户管理路由模块
"""
from datetime import datetime, date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from pypinyin import lazy_pinyin

from models import db, Account, AccountType, AccountBalance, User, Transaction, AccountGroup

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
    account_types = sorted(AccountType.query.all(), key=lambda t: lazy_pinyin(t.name))

    # 按类型分组（三分类），按拼音排序
    pinyin_key = lambda a: lazy_pinyin(a.name)
    savings_accounts = sorted([a for a in accounts if a.account_type and a.account_type.category == 'savings'], key=pinyin_key)
    fund_accounts = sorted([a for a in accounts if a.account_type and a.account_type.category == 'fund'], key=pinyin_key)
    stock_accounts = sorted([a for a in accounts if a.account_type and a.account_type.category == 'stock'], key=pinyin_key)

    # 计算各组合计（外币转换为人民币）
    rates = _get_exchange_rates()
    savings_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in savings_accounts)
    fund_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in fund_accounts)
    stock_total = sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in stock_accounts)

    # 获取本月快照记录
    this_month = date.today().replace(day=1)
    account_ids = [a.id for a in accounts]
    snapshots = {}
    if account_ids:
        records = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids),
            AccountBalance.record_month == this_month,
            db.or_(AccountBalance.source == 'snapshot', AccountBalance.source == None)
        ).all()
        for r in records:
            snapshots[r.account_id] = r

    # 获取每个账户的最新快照（用于显示余额对应的月份，只取快照类型）
    latest_snapshots = {}
    for a in accounts:
        latest = AccountBalance.query.filter(
            AccountBalance.account_id == a.id,
            db.or_(AccountBalance.source == 'snapshot', AccountBalance.source == None)
        ).order_by(AccountBalance.record_month.desc()).first()
        if latest:
            latest_snapshots[a.id] = latest

    # 获取所有快照记录（按月份降序），用于展示历史记录
    all_snapshots = []
    if account_ids:
        all_snapshots = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids)
        ).order_by(AccountBalance.record_month.desc(), AccountBalance.created_at.desc()).all()

    # 获取上月快照（用于批量录入面板显示上月余额，只取快照类型）
    prev_month = this_month - relativedelta(months=1)
    prev_snapshots = {}
    if account_ids:
        prev_records = AccountBalance.query.filter(
            AccountBalance.account_id.in_(account_ids),
            AccountBalance.record_month == prev_month,
            db.or_(AccountBalance.source == 'snapshot', AccountBalance.source == None)
        ).all()
        for r in prev_records:
            prev_snapshots[r.account_id] = r

    # 对账助手：计算本月每个账户的理论变化（关联交易净收支合计）
    next_month = this_month + relativedelta(months=1)
    account_theory = {}  # {account_id: net_change}
    account_theory_details = {}  # {account_id: [{'desc': ..., 'amount': ..., 'sign': ...}, ...]}
    if account_ids:
        for aid in account_ids:
            txns = Transaction.query.filter(
                Transaction.account_id == aid,
                Transaction.transaction_date >= this_month,
                Transaction.transaction_date < next_month
            ).all()
            net = 0
            details = []
            for t in txns:
                if t.type in ('income', 'transfer_in'):
                    val = float(t.amount)
                    details.append({'desc': t.description or t.type, 'amount': val, 'sign': '+'})
                else:
                    val = -float(t.amount)
                    details.append({'desc': t.description or t.type, 'amount': float(t.amount), 'sign': '-'})
                net += val
            account_theory[aid] = net
            account_theory_details[aid] = details

    # 获取所有分组信息
    groups = AccountGroup.query.filter_by(user_id=user_id).order_by(AccountGroup.display_order).all()
    
    # 按分组组织账户
    all_accounts = savings_accounts + fund_accounts + stock_accounts
    grouped_accounts = {}  # {group_id: [accounts]}
    group_stats = {}  # {group_id: {'account_count': N, 'total_balance': X}}
    for group in groups:
        accounts_in_group = [a for a in all_accounts if a.group_id == group.id]
        grouped_accounts[group.id] = accounts_in_group
        # 计算分组统计信息
        group_stats[group.id] = {
            'account_count': len(accounts_in_group),
            'total_balance': sum(float(a.current_balance) * rates.get(a.currency or 'CNY', 1.0) for a in accounts_in_group)
        }
    
    # 未分组的账户
    ungrouped_accounts = [a for a in all_accounts if not a.group_id]

    return render_template('accounts.html',
                           groups=groups,
                           grouped_accounts=grouped_accounts,
                           group_stats=group_stats,
                           ungrouped_accounts=ungrouped_accounts,
                           savings_accounts=savings_accounts,
                           fund_accounts=fund_accounts,
                           stock_accounts=stock_accounts,
                           savings_total=savings_total,
                           fund_total=fund_total,
                           stock_total=stock_total,
                           account_types=account_types,
                           snapshots=snapshots,
                           prev_snapshots=prev_snapshots,
                           latest_snapshots=latest_snapshots,
                           all_snapshots=all_snapshots,
                           account_theory=account_theory,
                           account_theory_details=account_theory_details,
                           exchange_rates=_get_exchange_rates(),
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')),
                           page_title='资产总览')


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
        current_balance=Decimal(initial_balance),
        group_id=request.form.get('group_id', type=int) or None,
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

    # 插入或更新（只操作 snapshot 记录，不覆盖 transfer 记录）
    existing = AccountBalance.query.filter_by(
        account_id=account_id, record_month=record_month
    ).filter(AccountBalance.source != 'transfer').first()

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

        # 插入或更新（只操作 snapshot 记录，不覆盖 transfer 记录）
        existing = AccountBalance.query.filter_by(
            account_id=account.id, record_month=record_month
        ).filter(AccountBalance.source != 'transfer').first()

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

    # 处理分组级别输入：按比例分配到组内未单独填写的账户
    groups = AccountGroup.query.filter_by(user_id=user_id).order_by(AccountGroup.display_order).all()
    for group in groups:
        group_balance_str = request.form.get(f'group_balance_{group.id}', '').strip()
        if not group_balance_str:
            continue
        group_balance = Decimal(group_balance_str)
        # 获取组内账户
        group_accounts = [a for a in accounts if a.group_id == group.id]
        if not group_accounts:
            continue
        # 计算上月余额用于按比例分配
        prev_month = record_month - relativedelta(months=1)
        prev_balances = {}
        for a in group_accounts:
            if request.form.get(f'balance_{a.id}', '').strip():
                continue  # 已单独填写，跳过
            prev_rec = AccountBalance.query.filter_by(account_id=a.id, record_month=prev_month).first()
            if prev_rec:
                prev_balances[a.id] = Decimal(str(prev_rec.balance))
            else:
                prev_balances[a.id] = Decimal('0')

        # 未单独填写的账户
        unfilled = [a for a in group_accounts if not request.form.get(f'balance_{a.id}', '').strip()]
        if not unfilled:
            continue

        # 计算需要分配的金额（组总额 - 已单独填写的子账户合计）
        filled_total = Decimal('0')
        for a in group_accounts:
            bal_str = request.form.get(f'balance_{a.id}', '').strip()
            if bal_str:
                filled_total += Decimal(bal_str)

        remaining = group_balance - filled_total
        unfilled_prev_total = sum(prev_balances.get(a.id, Decimal('0')) for a in unfilled)

        for a in unfilled:
            if unfilled_prev_total > 0:
                ratio = prev_balances.get(a.id, Decimal('0')) / unfilled_prev_total
            else:
                ratio = Decimal('1') / Decimal(str(len(unfilled)))
            allocated = (remaining * ratio).quantize(Decimal('0.01'))

            prev_bal = prev_balances.get(a.id, Decimal('0'))
            change_amount = allocated - prev_bal if prev_bal else None

            existing = AccountBalance.query.filter_by(
                account_id=a.id, record_month=record_month
            ).filter(AccountBalance.source != 'transfer').first()

            if existing:
                existing.balance = allocated
                existing.change_amount = change_amount
                existing.recorded_by = user_id
            else:
                snapshot = AccountBalance(
                    account_id=a.id, balance=allocated,
                    change_amount=change_amount, record_month=record_month,
                    recorded_by=user_id
                )
                db.session.add(snapshot)

            # 更新账户当前余额
            latest_snapshot = AccountBalance.query.filter_by(
                account_id=a.id
            ).order_by(AccountBalance.record_month.desc()).first()

            if latest_snapshot and latest_snapshot.record_month <= record_month:
                a.current_balance = allocated
            elif not latest_snapshot:
                a.current_balance = allocated
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


# 账户分组管理路由


@account_bp.route('/groups', methods=['GET'])
def list_groups():
    """获取用户的所有账户分组 (API)"""
    user_id = session.get('user_id')
    groups = AccountGroup.query.filter_by(user_id=user_id).order_by(AccountGroup.display_order).all()
    return {'groups': [g.to_dict() for g in groups]}, 200


@account_bp.route('/groups/create', methods=['POST'])
def create_group():
    """创建账户分组"""
    user_id = session.get('user_id')
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#D4A574').strip()

    if not name:
        flash('分组名称不能为空', 'error')
        return redirect(url_for('account.account_list'))

    # 检查是否已存在同名分组
    existing = AccountGroup.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        flash('该分组名称已存在', 'error')
        return redirect(url_for('account.account_list'))

    # 获取最大的 display_order
    max_order = db.session.query(db.func.max(AccountGroup.display_order)).filter_by(
        user_id=user_id
    ).scalar() or 0

    group = AccountGroup(
        user_id=user_id,
        name=name,
        description=description or None,
        color=color,
        display_order=max_order + 1
    )
    db.session.add(group)
    db.session.commit()

    flash(f'分组 "{name}" 创建成功', 'success')
    return redirect(url_for('account.account_list'))


@account_bp.route('/groups/<int:group_id>/update', methods=['POST'])
def update_group(group_id):
    """更新账户分组"""
    user_id = session.get('user_id')
    group = AccountGroup.query.get_or_404(group_id)

    if group.user_id != user_id:
        return "无权操作此分组", 403

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', group.color).strip()

    if not name:
        flash('分组名称不能为空', 'error')
        return redirect(url_for('account.account_list'))

    # 检查新名称是否与其他分组冲突
    existing = AccountGroup.query.filter(
        AccountGroup.user_id == user_id,
        AccountGroup.name == name,
        AccountGroup.id != group_id
    ).first()
    if existing:
        flash('新的分组名称已存在', 'error')
        return redirect(url_for('account.account_list'))

    group.name = name
    group.description = description or None
    group.color = color
    group.updated_at = datetime.utcnow()
    db.session.commit()

    flash(f'分组 "{name}" 已更新', 'success')
    return redirect(url_for('account.account_list'))


@account_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    """删除账户分组"""
    user_id = session.get('user_id')
    group = AccountGroup.query.get_or_404(group_id)

    if group.user_id != user_id:
        return "无权操作此分组", 403

    # 将分组内的账户设为未分组
    Account.query.filter_by(group_id=group_id).update({'group_id': None})
    
    # 删除分组
    group_name = group.name
    db.session.delete(group)
    db.session.commit()

    flash(f'分组 "{group_name}" 已删除，其中的账户已转为未分组', 'success')
    return redirect(url_for('account.account_list'))


@account_bp.route('/groups/<int:group_id>/reorder', methods=['POST'])
def reorder_groups(group_id):
    """重新排序分组"""
    user_id = session.get('user_id')
    group = AccountGroup.query.get_or_404(group_id)

    if group.user_id != user_id:
        return "无权操作此分组", 403

    display_order = request.form.get('display_order', type=int)
    if display_order is not None:
        group.display_order = display_order
        group.updated_at = datetime.utcnow()
        db.session.commit()

    return redirect(url_for('account.account_list'))


@account_bp.route('/<int:account_id>/move-to-group', methods=['POST'])
def move_account_to_group(account_id):
    """将账户移动到指定分组"""
    user_id = session.get('user_id')
    account = Account.query.get_or_404(account_id)

    if account.user_id != user_id:
        return "无权操作此账户", 403

    group_id = request.form.get('group_id', type=int)
    
    # 如果 group_id 为 None 或 0，则将账户设为未分组
    if not group_id:
        account.group_id = None
    else:
        # 验证分组存在且属于该用户
        group = AccountGroup.query.filter_by(id=group_id, user_id=user_id).first()
        if not group:
            return "分组不存在", 404
        account.group_id = group_id

    db.session.commit()
    flash('账户分组已更新', 'success')
    return redirect(url_for('account.account_list'))
