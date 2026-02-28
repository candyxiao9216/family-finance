"""
报表路由模块
提供月度收支趋势和分类占比的数据 API
"""

from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, render_template, request, session
from sqlalchemy import func

from models import db, Transaction, Category, User

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
                           username=session.get('nickname', session.get('username', '用户')))


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

    # 按月聚合收入和支出
    results = db.session.query(
        func.strftime('%Y-%m', Transaction.transaction_date).label('month'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        user_filter,
        Transaction.transaction_date >= start_date
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
