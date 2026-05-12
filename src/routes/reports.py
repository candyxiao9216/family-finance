"""
报表路由模块
提供月度收支趋势和分类占比的数据 API，以及月度总结报告
"""

from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, render_template, request, session
from sqlalchemy import func, extract

from models import (db, Transaction, Category, User, Account, AccountType,
                    AccountBalance, BabyFund, SavingsPlan, SavingsRecord, MonthlyTodo,
                    MonthlySummaryCache)
from routes.account import _get_exchange_rates

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_user_filter(user_id, current_view):
    """根据视图模式返回用户过滤条件

    Args:
        user_id: 当前登录用户 ID
        current_view: 'personal' 或 'family'

    Returns:
        SQLAlchemy 过滤条件
    """
    if current_view == 'family':
        user = User.query.get(user_id)
        if user and user.family:
            family_member_ids = [m.id for m in user.family.members]
            return Transaction.user_id.in_(family_member_ids)
    # 默认返回个人视图过滤
    return Transaction.user_id == user_id


def _get_account_ids(user_id, current_view):
    """根据视图模式返回账户 ID 列表"""
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        family_member_ids = [m.id for m in user.family.members]
        accounts = Account.query.filter(Account.user_id.in_(family_member_ids)).all()
    else:
        accounts = Account.query.filter_by(user_id=user_id).all()
    return [a.id for a in accounts]


@reports_bp.route('/')
def reports_page():
    """报表页面"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    # 无家庭时回退到个人视图
    if current_view == 'family' and not family:
        current_view = 'personal'

    return render_template('reports.html',
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')),
                           page_title='数据报表')


@reports_bp.route('/api/trend')
def api_trend():
    """月度收支趋势 API

    参数:
        months: 查询月数，1|3|6|12，默认 6
        view: 视图模式，personal|family，默认 personal

    返回:
        { labels: ["2026-01", ...], income: [100.0, ...], expense: [200.0, ...] }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    # 解析参数
    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6
    current_view = request.args.get('view', 'personal')
    user_filter = _get_user_filter(user_id, current_view)

    # 计算起始日期（当月 1 号往前推 months-1 个月）
    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    # 按月聚合收入和支出（排除转账）
    results = db.session.query(
        func.strftime('%Y-%m', Transaction.transaction_date).label('month'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        user_filter,
        Transaction.transaction_date >= start_date,
        Transaction.type.in_(['income', 'expense'])
    ).group_by(
        func.strftime('%Y-%m', Transaction.transaction_date),
        Transaction.type
    ).all()

    # 生成完整的月份标签列表
    labels = []
    current = start_date
    end_month = today.replace(day=1)
    while current <= end_month:
        labels.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)

    # 组装数据，确保每个月都有值
    income_map = {}
    expense_map = {}
    for row in results:
        val = float(row.total) if row.total else 0.0
        if row.type == 'income':
            income_map[row.month] = val
        else:
            expense_map[row.month] = val

    income = [income_map.get(m, 0.0) for m in labels]
    expense = [expense_map.get(m, 0.0) for m in labels]

    return jsonify({
        'labels': labels,
        'income': income,
        'expense': expense
    })


@reports_bp.route('/api/category')
def api_category():
    """分类占比 API

    参数:
        type: 交易类型，income|expense，默认 expense
        months: 查询月数，1|3|6|12，默认 6
        view: 视图模式，personal|family，默认 personal

    返回:
        { labels: ["餐饮", ...], values: [500.0, ...] }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    # 解析参数
    txn_type = request.args.get('type', 'expense')
    if txn_type not in ('income', 'expense'):
        txn_type = 'expense'
    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6
    current_view = request.args.get('view', 'personal')
    user_filter = _get_user_filter(user_id, current_view)

    # 计算起始日期
    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    # 按分类聚合金额（LEFT JOIN 以包含未分类交易）
    results = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).outerjoin(
        Category, Transaction.category_id == Category.id
    ).filter(
        user_filter,
        Transaction.type == txn_type,
        Transaction.transaction_date >= start_date
    ).group_by(
        Category.name
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).all()

    # 组装数据，将 None 分类名替换为"未分类"
    labels = []
    values = []
    for row in results:
        labels.append(row.name if row.name else '未分类')
        values.append(float(row.total) if row.total else 0.0)

    return jsonify({
        'labels': labels,
        'values': values
    })


@reports_bp.route('/api/asset-trend')
def api_asset_trend():
    """资产趋势 API

    基于 account_balance 月度快照数据，返回储蓄/投资/总资产按月汇总

    参数:
        months: 查询月数，1|3|6|12，默认 6
        view: 视图模式，personal|family，默认 personal

    返回:
        { labels: ["2026-01", ...], savings: [...], investment: [...], total: [...] }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6
    current_view = request.args.get('view', 'personal')

    account_ids = _get_account_ids(user_id, current_view)
    if not account_ids:
        return jsonify({'labels': [], 'savings': [], 'investment': [], 'total': []})

    # 计算起始日期
    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    # 查询快照数据，JOIN AccountType 获取 category
    results = db.session.query(
        func.strftime('%Y-%m', AccountBalance.record_month).label('month'),
        AccountType.category,
        func.sum(AccountBalance.balance).label('total_balance')
    ).join(
        Account, AccountBalance.account_id == Account.id
    ).join(
        AccountType, Account.type_id == AccountType.id
    ).filter(
        AccountBalance.account_id.in_(account_ids),
        AccountBalance.record_month >= start_date
    ).group_by(
        func.strftime('%Y-%m', AccountBalance.record_month),
        AccountType.category
    ).all()

    # 生成完整月份标签
    labels = []
    current = start_date
    end_month = today.replace(day=1)
    while current <= end_month:
        labels.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)

    # 组装数据
    savings_map = {}
    investment_map = {}
    for row in results:
        val = float(row.total_balance) if row.total_balance else 0.0
        if row.category == 'savings':
            savings_map[row.month] = val
        else:
            investment_map[row.month] = val

    savings = [savings_map.get(m, 0.0) for m in labels]
    investment = [investment_map.get(m, 0.0) for m in labels]
    total = [s + i for s, i in zip(savings, investment)]

    return jsonify({
        'labels': labels,
        'savings': savings,
        'investment': investment,
        'total': total
    })


@reports_bp.route('/api/family-contribution')
def api_family_contribution():
    """家庭成员贡献 API

    按家庭成员汇总收入、支出、资产数据。仅在 view=family 时返回数据。

    参数:
        months: 查询月数，1|3|6|12，默认 6
        view: 必须为 family，否则返回空数据

    返回:
        { members: [{name, income, expense, assets}, ...],
          total_income, total_expense, total_assets }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    current_view = request.args.get('view', 'personal')
    if current_view != 'family':
        return jsonify({'members': [], 'total_income': 0,
                        'total_expense': 0, 'total_assets': 0})

    user = User.query.get(user_id)
    if not user or not user.family:
        return jsonify({'members': [], 'total_income': 0,
                        'total_expense': 0, 'total_assets': 0})

    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6

    today = date.today()
    start_date = today.replace(day=1) - relativedelta(months=months - 1)

    family_members = user.family.members
    rates = _get_exchange_rates()

    # 按用户聚合收入
    income_rows = db.session.query(
        Transaction.user_id,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id.in_([m.id for m in family_members]),
        Transaction.type == 'income',
        Transaction.transaction_date >= start_date
    ).group_by(Transaction.user_id).all()
    income_map = {row.user_id: float(row.total or 0) for row in income_rows}

    # 按用户聚合支出
    expense_rows = db.session.query(
        Transaction.user_id,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id.in_([m.id for m in family_members]),
        Transaction.type == 'expense',
        Transaction.transaction_date >= start_date
    ).group_by(Transaction.user_id).all()
    expense_map = {row.user_id: float(row.total or 0) for row in expense_rows}

    # 按用户聚合资产（Account.current_balance * 汇率）
    asset_rows = db.session.query(
        Account.user_id,
        Account.currency,
        func.sum(Account.current_balance).label('total')
    ).filter(
        Account.user_id.in_([m.id for m in family_members])
    ).group_by(Account.user_id, Account.currency).all()
    asset_map = {}
    for row in asset_rows:
        rate = rates.get(row.currency or 'CNY', 1.0)
        asset_map[row.user_id] = asset_map.get(row.user_id, 0) + float(row.total or 0) * rate

    # 组装结果
    members = []
    total_income = 0
    total_expense = 0
    total_assets = 0
    for m in family_members:
        inc = round(income_map.get(m.id, 0), 2)
        exp = round(expense_map.get(m.id, 0), 2)
        ast = round(asset_map.get(m.id, 0), 2)
        members.append({
            'name': m.nickname or m.username,
            'income': inc,
            'expense': exp,
            'assets': ast
        })
        total_income += inc
        total_expense += exp
        total_assets += ast

    return jsonify({
        'members': members,
        'total_income': round(total_income, 2),
        'total_expense': round(total_expense, 2),
        'total_assets': round(total_assets, 2)
    })


def _get_ai_summary(user_id, year, month, section, data):
    """获取 AI 月度总结文案（带缓存）。
    先查缓存，有就返回；没有就调 AI 生成，存缓存后返回。
    AI 不可用时返回降级文案。
    """
    # 1. 查缓存
    cached = MonthlySummaryCache.query.filter_by(
        user_id=user_id, year=year, month=month, section=section
    ).first()
    if cached:
        return cached.content

    # 2. 构造 prompt
    if section.startswith('asset'):
        if not data.get('income_details'):
            return "本月暂无收入记录。"
        income_lines = '、'.join([f"{d['desc']}(¥{d['amount']:,.0f})" for d in data['income_details']])
        prompt = (
            f"帮我用1-2句话总结本月资产变动，要求：纯数据驱动，量化说明变动来源，不要感性描述，不要给建议，不要用markdown。\n"
            f"数据：收入 ¥{data['income_total']:,.0f}，支出 ¥{data['expense_total']:,.0f}，"
            f"资产从 ¥{data['asset_start']:,.0f} → ¥{data['asset_end']:,.0f}（{'+'if data['asset_growth']>=0 else ''}{data['asset_growth']:,.0f}）。"
            f"主要收入：{income_lines}。"
            f"\n示例风格：'本月资产增长¥X，主要来自工资¥A和公积金¥B，支出¥C以信用卡还款为主。'"
        )
    elif section.startswith('baby_fund'):
        if data['month_count'] == 0:
            return "本月暂无新增宝宝基金。"
        details_lines = '、'.join([f"{d['giver']}{('(' + d['event'] + ')') if d['event'] else ''} ¥{d['amount']:,.0f}" for d in data['details']])
        prompt = (
            f"帮我用1句话总结本月宝宝基金变动，纯数据，不要感性描述，不要用markdown。\n"
            f"数据：本月新增 {data['month_count']} 笔共 ¥{data['month_amount']:,.0f}，"
            f"明细：{details_lines}。累计 ¥{data['cumulative_total']:,.0f}。"
            f"\n示例风格：'本月新增2笔共¥6,000（爷爷¥3,000、奶奶¥3,000），累计¥50,000。'"
        )
    else:
        return ""

    # 3. 调用 AI
    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    if not advisor.available:
        # AI 不可用，降级为模板文案
        if section.startswith('asset'):
            income_lines = '、'.join([f"{d['desc']}(¥{d['amount']:,.0f})" for d in data['income_details']])
            return f"本月资产变动主要来源于{income_lines}。"
        elif section.startswith('baby_fund'):
            details_lines = '、'.join([f"{d['giver']}{('(' + d['event'] + ')') if d['event'] else ''} ¥{d['amount']:,.0f}" for d in data['details']])
            return f"本月宝宝基金新增：{details_lines}。"
        return ""

    result = advisor._call_api(prompt)
    if not result or result.startswith('❌') or result.startswith('⏳'):
        # 调用失败，返回降级文案，不缓存
        if section.startswith('asset'):
            income_lines = '、'.join([f"{d['desc']}(¥{d['amount']:,.0f})" for d in data['income_details']])
            return f"本月资产变动主要来源于{income_lines}。"
        elif section.startswith('baby_fund'):
            details_lines = '、'.join([f"{d['giver']}{('(' + d['event'] + ')') if d['event'] else ''} ¥{d['amount']:,.0f}" for d in data['details']])
            return f"本月宝宝基金新增：{details_lines}。"
        return ""

    # 4. 存缓存
    from datetime import datetime
    cache = MonthlySummaryCache(
        user_id=user_id, year=year, month=month,
        section=section, content=result, created_at=datetime.utcnow()
    )
    db.session.add(cache)
    db.session.commit()

    return result


@reports_bp.route('/monthly-summary')
def monthly_summary():
    """月度总结报告页面

    参数:
        year: 年份，默认当前年
        month: 月份，默认当前月
    """
    user_id = session.get('user_id')
    if not user_id:
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')
    if current_view == 'family' and not family:
        current_view = 'personal'

    # 解析月份参数
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    if month < 1 or month > 12:
        month = today.month
    if year < 2020 or year > 2099:
        year = today.year

    month_start = date(year, month, 1)
    next_month_start = month_start + relativedelta(months=1)

    # 上/下月导航
    prev_month = month_start - relativedelta(months=1)
    next_month = month_start + relativedelta(months=1)

    user_filter = _get_user_filter(user_id, current_view)
    account_ids = _get_account_ids(user_id, current_view)

    # ── 1. 收支概况 ──
    income_expense = db.session.query(
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        user_filter,
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date < next_month_start,
        Transaction.type.in_(['income', 'expense'])
    ).group_by(Transaction.type).all()

    income_total = 0.0
    expense_total = 0.0
    for row in income_expense:
        if row.type == 'income':
            income_total = float(row.total) if row.total else 0.0
        elif row.type == 'expense':
            expense_total = float(row.total) if row.total else 0.0
    balance = income_total - expense_total

    # ── 2. 资产变化 ──
    # 本月快照
    current_month_balances = db.session.query(
        func.sum(AccountBalance.balance).label('total')
    ).filter(
        AccountBalance.account_id.in_(account_ids),
        AccountBalance.record_month >= month_start,
        AccountBalance.record_month < next_month_start
    ).first() if account_ids else None

    # 上月快照
    prev_month_start_date = month_start - relativedelta(months=1)
    prev_balances = db.session.query(
        func.sum(AccountBalance.balance).label('total')
    ).filter(
        AccountBalance.account_id.in_(account_ids),
        AccountBalance.record_month >= prev_month_start_date,
        AccountBalance.record_month < month_start
    ).first() if account_ids else None

    asset_start = float(prev_balances.total) if prev_balances and prev_balances.total else 0.0

    # 月末资产：如果是当月，用 current_balance；否则用本月快照
    if year == today.year and month == today.month:
        end_total = db.session.query(
            func.sum(Account.current_balance)
        ).filter(
            Account.id.in_(account_ids)
        ).scalar() if account_ids else 0
        asset_end = float(end_total) if end_total else 0.0
    else:
        asset_end = float(current_month_balances.total) if current_month_balances and current_month_balances.total else 0.0

    asset_growth = asset_end - asset_start
    asset_growth_pct = (asset_growth / asset_start * 100) if asset_start > 0 else 0.0

    # AI 摘要：从收入交易的 description 生成
    income_transactions = Transaction.query.filter(
        user_filter,
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date < next_month_start,
        Transaction.type == 'income'
    ).order_by(Transaction.amount.desc()).all()

    # 资产变动 AI 总结（带缓存，按视图区分）
    asset_ai_summary = _get_ai_summary(user_id, year, month, f'asset_{current_view}', {
        'income_total': income_total,
        'expense_total': expense_total,
        'asset_start': asset_start,
        'asset_end': asset_end,
        'asset_growth': asset_growth,
        'income_details': [{'desc': t.description or '未备注', 'amount': float(t.amount)} for t in income_transactions[:5]],
    })

    # ── 3. 转账记录 ──
    transfers = Transaction.query.filter(
        user_filter,
        Transaction.transaction_date >= month_start,
        Transaction.transaction_date < next_month_start,
        Transaction.type == 'transfer_out'
    ).order_by(Transaction.transaction_date.desc()).all()

    transfer_count = len(transfers)
    transfer_total = sum(float(t.amount) for t in transfers)

    # ── 4. 宝宝基金 ──
    if current_view == 'family' and user and user.family:
        family_member_ids = [m.id for m in user.family.members]
    else:
        family_member_ids = [user_id]

    baby_funds_this_month = BabyFund.query.filter(
        BabyFund.created_by.in_(family_member_ids),
        BabyFund.event_date >= month_start,
        BabyFund.event_date < next_month_start
    ).order_by(BabyFund.event_date.desc()).all()

    baby_month_count = len(baby_funds_this_month)
    baby_month_amount = sum(float(bf.amount) for bf in baby_funds_this_month)

    baby_cumulative = db.session.query(
        func.sum(BabyFund.amount)
    ).filter(
        BabyFund.created_by.in_(family_member_ids)
    ).scalar()
    baby_cumulative_total = float(baby_cumulative) if baby_cumulative else 0.0

    # 宝宝基金 AI 摘要（带缓存）
    baby_ai_summary = _get_ai_summary(user_id, year, month, f'baby_fund_{current_view}', {
        'month_count': baby_month_count,
        'month_amount': baby_month_amount,
        'cumulative_total': baby_cumulative_total,
        'details': [{'giver': bf.giver_name, 'event': bf.event_type or '', 'amount': float(bf.amount)} for bf in baby_funds_this_month[:5]],
    })

    # ── 5. 储蓄目标 ──
    annual_plan = SavingsPlan.query.filter_by(
        year=year, type='annual'
    ).first()
    annual_target = float(annual_plan.target_amount) if annual_plan else 0.0

    year_start = date(year, 1, 1)
    year_end = date(year + 1, 1, 1)
    annual_saved = db.session.query(
        func.sum(SavingsRecord.amount)
    ).filter(
        SavingsRecord.record_date >= year_start,
        SavingsRecord.record_date < year_end
    ).scalar()
    annual_saved_total = float(annual_saved) if annual_saved else 0.0

    monthly_saved = db.session.query(
        func.sum(SavingsRecord.amount)
    ).filter(
        SavingsRecord.record_date >= month_start,
        SavingsRecord.record_date < next_month_start
    ).scalar()
    monthly_saved_total = float(monthly_saved) if monthly_saved else 0.0

    monthly_plan = SavingsPlan.query.filter_by(
        year=year, month=month, type='monthly'
    ).first()
    monthly_target = float(monthly_plan.target_amount) if monthly_plan else 0.0

    annual_progress = (annual_saved_total / annual_target * 100) if annual_target > 0 else 0.0

    # ── 6. 月度待办 ──
    todos = MonthlyTodo.query.filter_by(
        user_id=user_id, year=year, month=month
    ).order_by(MonthlyTodo.priority.desc()).all()

    todos_total = len(todos)
    todos_completed = sum(1 for t in todos if t.status == 'completed')
    todos_required = sum(1 for t in todos if t.is_required)
    todos_required_completed = sum(1 for t in todos if t.is_required and t.status == 'completed')

    return render_template('monthly_summary.html',
                           year=year,
                           month=month,
                           prev_year=prev_month.year,
                           prev_month_num=prev_month.month,
                           next_year=next_month.year,
                           next_month_num=next_month.month,
                           income_total=income_total,
                           expense_total=expense_total,
                           balance=balance,
                           asset_start=asset_start,
                           asset_end=asset_end,
                           asset_growth=asset_growth,
                           asset_growth_pct=asset_growth_pct,
                           asset_ai_summary=asset_ai_summary,
                           transfers=transfers,
                           transfer_count=transfer_count,
                           transfer_total=transfer_total,
                           baby_funds=baby_funds_this_month,
                           baby_month_count=baby_month_count,
                           baby_month_amount=baby_month_amount,
                           baby_cumulative_total=baby_cumulative_total,
                           baby_ai_summary=baby_ai_summary,
                           monthly_saved=monthly_saved_total,
                           monthly_target=monthly_target,
                           annual_saved=annual_saved_total,
                           annual_target=annual_target,
                           annual_progress=annual_progress,
                           todos=todos,
                           todos_total=todos_total,
                           todos_completed=todos_completed,
                           todos_required=todos_required,
                           todos_required_completed=todos_required_completed,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')),
                           page_title=f'{year}年{month}月总结')


@reports_bp.route('/api/refresh-summary', methods=['POST'])
def refresh_summary():
    """手动刷新月度总结 AI 文案（清除缓存，下次访问重新生成）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)

    # 删除该月的缓存
    MonthlySummaryCache.query.filter_by(
        user_id=user_id, year=year, month=month
    ).delete()
    db.session.commit()

    return jsonify({'ok': True, 'message': f'{year}年{month}月 AI 总结已刷新，请重新打开页面查看。'})
