"""储蓄计划路由模块"""
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from sqlalchemy import func

from models import db, User, SavingsPlan, SavingsRecord, Account

savings_bp = Blueprint('savings', __name__, url_prefix='/savings')


def _get_family_member_ids(user_id, current_view):
    """获取当前视图下的用户 ID 列表"""
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        return [m.id for m in user.family.members]
    return [user_id]


@savings_bp.route('/')
def savings_list():
    """储蓄计划列表页"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = 'family'  # 储蓄计划始终使用家庭视图

    member_ids = _get_family_member_ids(user_id, current_view)

    plans = SavingsPlan.query.filter(
        SavingsPlan.created_by.in_(member_ids)
    ).order_by(SavingsPlan.created_at.desc()).all()

    plan_data = []
    total_target = Decimal('0')
    total_saved = Decimal('0')

    for plan in plans:
        saved = db.session.query(func.sum(SavingsRecord.amount)).filter(
            SavingsRecord.plan_id == plan.id
        ).scalar() or Decimal('0')

        progress = float(saved / plan.target_amount * 100) if plan.target_amount else 0
        plan_data.append({
            'plan': plan,
            'saved': float(saved),
            'progress': min(progress, 100),
            'records': plan.records,
        })
        total_target += plan.target_amount
        total_saved += saved

    overall_progress = float(total_saved / total_target * 100) if total_target else 0

    accounts = Account.query.filter(Account.user_id.in_(member_ids)).all()

    # === 图表数据：按月汇总储蓄趋势 ===
    all_records = SavingsRecord.query.filter(
        SavingsRecord.plan_id.in_([item['plan'].id for item in plan_data])
    ).order_by(SavingsRecord.record_date).all()

    # 汇总趋势（所有计划合计，按月累计）
    monthly_totals = defaultdict(lambda: Decimal('0'))
    for rec in all_records:
        month_key = rec.record_date.strftime('%Y-%m')
        monthly_totals[month_key] += rec.amount

    # 排序月份，计算累计值
    sorted_months = sorted(monthly_totals.keys())
    chart_labels = sorted_months
    chart_cumulative = []
    running_total = Decimal('0')
    for m in sorted_months:
        running_total += monthly_totals[m]
        chart_cumulative.append(float(running_total))

    # 每个计划的迷你图数据（按月累计）
    for item in plan_data:
        plan_records = [r for r in all_records if r.plan_id == item['plan'].id]
        plan_monthly = defaultdict(lambda: Decimal('0'))
        for rec in plan_records:
            mk = rec.record_date.strftime('%Y-%m')
            plan_monthly[mk] += rec.amount
        p_months = sorted(plan_monthly.keys())
        p_cumulative = []
        p_running = Decimal('0')
        for mk in p_months:
            p_running += plan_monthly[mk]
            p_cumulative.append(float(p_running))
        item['chart_labels'] = p_months
        item['chart_data'] = p_cumulative

    return render_template('savings.html',
                           plan_data=plan_data,
                           total_target=float(total_target),
                           total_saved=float(total_saved),
                           overall_progress=min(overall_progress, 100),
                           accounts=accounts,
                           all_records=sorted(all_records, key=lambda r: r.created_at or datetime.min, reverse=True),
                           chart_labels=chart_labels,
                           chart_cumulative=chart_cumulative,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@savings_bp.route('/plan/add', methods=['POST'])
def add_plan():
    """创建储蓄计划"""
    user_id = session.get('user_id')
    name = request.form.get('name')
    plan_type = request.form.get('type')
    target_amount = request.form.get('target_amount')
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)

    if not all([name, plan_type, target_amount, year]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('savings.savings_list'))

    if plan_type == 'annual':
        month = None
    elif plan_type == 'monthly' and (not month or month < 1 or month > 12):
        flash('月度计划需要选择有效月份(1-12)', 'error')
        return redirect(url_for('savings.savings_list'))

    plan = SavingsPlan(
        name=name, type=plan_type,
        target_amount=Decimal(target_amount),
        year=year, month=month,
        created_by=user_id
    )
    db.session.add(plan)
    db.session.commit()

    return redirect(url_for('savings.savings_list'))


@savings_bp.route('/plan/<int:plan_id>/edit', methods=['POST'])
def edit_plan(plan_id):
    """编辑储蓄计划"""
    plan = SavingsPlan.query.get_or_404(plan_id)
    plan.name = request.form.get('name', plan.name)
    plan.target_amount = Decimal(request.form.get('target_amount', str(plan.target_amount)))
    db.session.commit()
    return redirect(url_for('savings.savings_list'))


@savings_bp.route('/plan/<int:plan_id>/delete', methods=['POST'])
def delete_plan(plan_id):
    """删除储蓄计划（级联删除记录）"""
    plan = SavingsPlan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    return redirect(url_for('savings.savings_list'))


@savings_bp.route('/record/add', methods=['POST'])
def add_record():
    """录入储蓄记录"""
    user_id = session.get('user_id')
    plan_id = request.form.get('plan_id', type=int)
    amount = request.form.get('amount')
    record_date_str = request.form.get('record_date')
    description = request.form.get('description')
    account_id = request.form.get('account_id', type=int)

    if not all([plan_id, amount, record_date_str]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('savings.savings_list'))

    try:
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('日期格式错误', 'error')
        return redirect(url_for('savings.savings_list'))

    record = SavingsRecord(
        plan_id=plan_id, user_id=user_id,
        amount=Decimal(amount), record_date=record_date,
        description=description or None,
        account_id=account_id or None
    )
    db.session.add(record)
    db.session.commit()

    return redirect(url_for('savings.savings_list'))


@savings_bp.route('/record/<int:record_id>/edit', methods=['POST'])
def edit_record(record_id):
    """编辑储蓄记录"""
    record = SavingsRecord.query.get_or_404(record_id)

    plan_id = request.form.get('plan_id', type=int)
    amount = request.form.get('amount')
    record_date_str = request.form.get('record_date')
    description = request.form.get('description')
    account_id = request.form.get('account_id', type=int)

    if not all([plan_id, amount, record_date_str]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('savings.savings_list'))

    try:
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('日期格式错误', 'error')
        return redirect(url_for('savings.savings_list'))

    record.plan_id = plan_id
    record.amount = Decimal(amount)
    record.record_date = record_date
    record.description = description or None
    record.account_id = account_id or None
    db.session.commit()
    flash('储蓄记录已更新', 'success')
    return redirect(url_for('savings.savings_list'))


@savings_bp.route('/record/<int:record_id>/delete', methods=['POST'])
def delete_record(record_id):
    """删除储蓄记录"""
    record = SavingsRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    flash('储蓄记录已删除', 'success')
    return redirect(url_for('savings.savings_list'))
