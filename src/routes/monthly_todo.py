"""月度待办 Checklist 路由模块

每月固定 4 项待办（3 必选 + 1 可选），支持自动检测 + 手动打钩。
"""
from datetime import datetime, date

from flask import Blueprint, redirect, request, session, url_for, flash, jsonify, render_template
from sqlalchemy import func, extract

from models import (
    db, User, MonthlyTodo, Transaction, Account, AccountBalance,
    SavingsRecord, BabyFund
)

monthly_todo_bp = Blueprint('monthly_todo', __name__, url_prefix='/monthly-todo')


# ── 固定 4 项 Checklist 定义 ──────────────────────────────────

CHECKLIST_ITEMS = [
    {
        'detect_key': 'transaction',
        'category': 'transaction',
        'title': '录入本月交易记录',
        'description': '记录本月的收入和支出',
        'tips': '录完后打钩即可',
        'is_required': True,
        'priority': 5,
        'action_url_endpoint': 'transaction.transaction_list',
        'action_label': '去录入',
    },
    {
        'detect_key': 'snapshot',
        'category': 'snapshot',
        'title': '更新账户余额快照',
        'description': '记录各账户本月最新余额',
        'tips': '所有账户都填好后自动完成',
        'is_required': True,
        'priority': 4,
        'action_url_endpoint': 'account.account_list',
        'action_label': '去更新',
    },
    {
        'detect_key': 'savings',
        'category': 'savings',
        'title': '录入储蓄记录',
        'description': '记录本月的储蓄情况',
        'tips': '有储蓄记录后自动完成',
        'is_required': True,
        'priority': 4,
        'action_url_endpoint': 'savings.savings_list',
        'action_label': '去录入',
    },
    {
        'detect_key': 'baby_fund',
        'category': 'baby_fund',
        'title': '录入宝宝基金',
        'description': '记录本月宝宝收到的礼金',
        'tips': '本月没有可跳过',
        'is_required': False,
        'priority': 2,
        'action_url_endpoint': 'baby_fund.baby_fund_list',
        'action_label': '去录入',
    },
]


# ── 核心函数：生成 + 自动检测 ────────────────────────────────

def ensure_monthly_checklist(user_id, year, month):
    """确保当月 checklist 已生成（没有则创建），然后执行自动检测。

    返回当月所有 checklist 项（list[MonthlyTodo]）。
    """
    existing = MonthlyTodo.query.filter_by(
        user_id=user_id, year=year, month=month
    ).all()

    # 如果已有记录，按 detect_key 索引
    existing_keys = {t.detect_key for t in existing if t.detect_key}

    created = False
    for item in CHECKLIST_ITEMS:
        if item['detect_key'] not in existing_keys:
            todo = MonthlyTodo(
                user_id=user_id,
                year=year,
                month=month,
                detect_key=item['detect_key'],
                category=item['category'],
                title=item['title'],
                description=item['description'],
                tips=item['tips'],
                is_required=item['is_required'],
                priority=item['priority'],
                action_url=item.get('action_url_endpoint', ''),
                status='pending',
            )
            db.session.add(todo)
            created = True

    if created:
        db.session.commit()
        # 重新查询
        existing = MonthlyTodo.query.filter_by(
            user_id=user_id, year=year, month=month
        ).all()

    # 执行自动检测
    auto_detect_completion(user_id, year, month, existing)

    return existing


def auto_detect_completion(user_id, year, month, todos=None):
    """对支持自动检测的项执行检测，按当前登录用户的数据判断。

    检测规则（只看 user_id 本人的数据）：
    - snapshot: 该用户名下所有账户都有本月快照 → 完成
    - savings: 该用户本月有至少 1 条储蓄记录 → 完成
    - transaction / baby_fund: 纯手动打钩，不自动检测
    """
    if todos is None:
        todos = MonthlyTodo.query.filter_by(
            user_id=user_id, year=year, month=month
        ).all()

    # 本月日期范围
    month_start = date(year, month, 1)

    changed = False
    for todo in todos:
        if todo.status == 'completed':
            continue  # 已完成的不重复检测

        detected = False

        if todo.detect_key == 'snapshot':
            # 该用户名下所有账户都有本月快照
            total_accounts = Account.query.filter(
                Account.user_id == user_id
            ).count()
            if total_accounts > 0:
                snapshot_count = AccountBalance.query.filter(
                    AccountBalance.account.has(Account.user_id == user_id),
                    AccountBalance.record_month == month_start
                ).count()
                detected = (snapshot_count >= total_accounts)

        elif todo.detect_key == 'savings':
            # 该用户本月有至少 1 条储蓄记录
            count = SavingsRecord.query.filter(
                SavingsRecord.user_id == user_id,
                extract('year', SavingsRecord.record_date) == year,
                extract('month', SavingsRecord.record_date) == month
            ).count()
            detected = (count > 0)

        # transaction 和 baby_fund 不自动检测

        if detected:
            todo.status = 'completed'
            todo.auto_detected = True
            todo.completed_at = datetime.utcnow()
            changed = True

    if changed:
        db.session.commit()


# ── 路由 ─────────────────────────────────────────────────────

@monthly_todo_bp.route('/')
def monthly_todo_list():
    """月度待办 Checklist 页面"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None

    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    if month < 1 or month > 12:
        month = today.month
    if year < 2020:
        year = today.year

    # 确保 checklist 已生成 + 自动检测
    todos = ensure_monthly_checklist(user_id, year, month)

    # 按 priority 降序排列
    todos.sort(key=lambda t: t.priority, reverse=True)

    # 统计
    required_todos = [t for t in todos if t.is_required]
    required_completed = sum(1 for t in required_todos if t.status == 'completed')
    total_required = len(required_todos)
    completion_rate = (required_completed / total_required * 100) if total_required > 0 else 0

    # 月份导航
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template('monthly_todo.html',
                         todos=todos,
                         year=year,
                         month=month,
                         required_completed=required_completed,
                         total_required=total_required,
                         completion_rate=completion_rate,
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month,
                         family=family,
                         checklist_items=CHECKLIST_ITEMS,
                         username=session.get('nickname', session.get('username', '用户')),
                         page_title='月度待办')


@monthly_todo_bp.route('/<int:todo_id>/toggle', methods=['POST'])
def toggle_todo(todo_id):
    """手动打钩 / 取消打钩（AJAX + 表单双支持）"""
    todo = MonthlyTodo.query.get_or_404(todo_id)

    if todo.user_id != session.get('user_id'):
        if request.is_json:
            return jsonify({'error': '无权操作'}), 403
        flash('无权操作', 'error')
        return redirect(url_for('monthly_todo.monthly_todo_list'))

    if todo.status == 'completed':
        # 取消打钩
        todo.status = 'pending'
        todo.completed_at = None
        todo.auto_detected = False
    else:
        # 手动打钩完成
        todo.status = 'completed'
        todo.completed_at = datetime.utcnow()
        todo.auto_detected = False

    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'status': todo.status,
            'completed_at': todo.completed_at.isoformat() if todo.completed_at else None
        })

    flash('待办状态已更新', 'success')
    return redirect(url_for('monthly_todo.monthly_todo_list', year=todo.year, month=todo.month))


@monthly_todo_bp.route('/api/summary', methods=['GET'])
def get_todo_summary():
    """获取当月待办摘要（用于仪表盘卡片）"""
    user_id = session.get('user_id')

    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    todos = ensure_monthly_checklist(user_id, year, month)

    result = []
    for todo in sorted(todos, key=lambda t: t.priority, reverse=True):
        # 找到对应的 action_label
        item_def = next((i for i in CHECKLIST_ITEMS if i['detect_key'] == todo.detect_key), None)
        result.append({
            'id': todo.id,
            'title': todo.title,
            'category': todo.category,
            'detect_key': todo.detect_key,
            'status': todo.status,
            'is_required': todo.is_required,
            'auto_detected': todo.auto_detected,
            'action_label': item_def['action_label'] if item_def else '查看',
            'action_url': item_def['action_url_endpoint'] if item_def else '',
        })

    required_todos = [t for t in todos if t.is_required]
    required_completed = sum(1 for t in required_todos if t.status == 'completed')
    total_required = len(required_todos)
    completion_rate = (required_completed / total_required * 100) if total_required > 0 else 0

    return jsonify({
        'year': year,
        'month': month,
        'items': result,
        'required_completed': required_completed,
        'total_required': total_required,
        'completion_rate': round(completion_rate, 1),
    })
