# 账户余额追踪 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现多账户管理、余额快照、交易关联账户、资产趋势图

**Architecture:** 新增 3 个数据模型（AccountType, Account, AccountBalance），1 个路由蓝图（account_bp），扩展 Transaction 模型和 reports 蓝图。沿用现有 Flask + SQLAlchemy + Chart.js 架构。

**Tech Stack:** Flask, SQLAlchemy, Chart.js 4, Jinja2

---

## Task 1: 数据模型 — AccountType + Account + AccountBalance

**Files:**
- Modify: `src/models.py`
- Modify: `src/database.py`（初始化预设账户类型）

**Step 1: 在 `src/models.py` 末尾添加三个新模型**

在 `TransactionModification` 类之后添加：

```python
# ===== 账户相关模型 =====

class AccountType(db.Model):
    """账户类型表"""
    __tablename__ = 'account_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 'savings' 或 'investment'
    is_default = db.Column(db.Boolean, default=False)

    accounts = db.relationship('Account', backref='account_type', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'is_default': self.is_default
        }


DEFAULT_ACCOUNT_TYPES = [
    {'name': '银行', 'category': 'savings', 'is_default': True},
    {'name': '微众', 'category': 'savings', 'is_default': True},
    {'name': '中金', 'category': 'savings', 'is_default': True},
    {'name': '富途', 'category': 'investment', 'is_default': True},
    {'name': '中银国际', 'category': 'investment', 'is_default': True},
]


class Account(db.Model):
    """账户表"""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('account_types.id'), nullable=False)
    initial_balance = db.Column(db.Numeric(10, 2), default=0)
    current_balance = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='accounts', lazy=True)
    balance_records = db.relationship('AccountBalance', backref='account', lazy=True,
                                      order_by='AccountBalance.record_month.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type_id': self.type_id,
            'type_name': self.account_type.name if self.account_type else None,
            'category': self.account_type.category if self.account_type else None,
            'initial_balance': float(self.initial_balance),
            'current_balance': float(self.current_balance),
            'user_id': self.user_id
        }


class AccountBalance(db.Model):
    """账户月度余额快照表"""
    __tablename__ = 'account_balance'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    balance = db.Column(db.Numeric(10, 2), nullable=False)
    change_amount = db.Column(db.Numeric(10, 2), nullable=True)
    record_month = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('account_id', 'record_month', name='uq_account_month'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'balance': float(self.balance),
            'change_amount': float(self.change_amount) if self.change_amount else 0,
            'record_month': self.record_month.strftime('%Y-%m') if self.record_month else None
        }
```

**Step 2: 在 Transaction 模型中新增 account_id 字段**

在 `Transaction` 类中 `created_at` 字段之后、`last_modified_by` 之前添加：

```python
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    account = db.relationship('Account', backref='transactions', lazy=True)
```

在 `Transaction.to_dict()` 中添加 `'account_id': self.account_id`。

**Step 3: 更新 `src/database.py` 初始化预设账户类型**

导入新模型，在 `init_database` 函数中 `db.session.commit()` 之前插入预设账户类型的初始化逻辑：

```python
from models import db, Category, DEFAULT_CATEGORIES, AccountType, DEFAULT_ACCOUNT_TYPES

# 在 init_database 中，预设分类循环之后添加：
        for at_data in DEFAULT_ACCOUNT_TYPES:
            existing = AccountType.query.filter_by(name=at_data['name']).first()
            if not existing:
                account_type = AccountType(**at_data)
                db.session.add(account_type)
```

**Step 4: 重启应用验证表创建**

Run: `lsof -ti:5001 | xargs kill -9 2>/dev/null; sleep 1 && python3 src/main.py`
Expected: 应用正常启动，日志中无报错，新表自动创建

**Step 5: Commit**

```bash
git add src/models.py src/database.py
git commit -m "feat: 添加账户相关数据模型（AccountType, Account, AccountBalance）"
```

---

## Task 2: 账户管理路由蓝图

**Files:**
- Create: `src/routes/account.py`
- Modify: `src/main.py`（注册蓝图 + 导入）

**Step 1: 创建 `src/routes/account.py`**

```python
"""
账户管理路由模块
"""
from datetime import datetime, date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, render_template, request, session, url_for

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

    # 获取本月快照记录（用于显示月度变化）
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

    return render_template('accounts.html',
                           savings_accounts=savings_accounts,
                           investment_accounts=investment_accounts,
                           savings_total=savings_total,
                           investment_total=investment_total,
                           account_types=account_types,
                           snapshots=snapshots,
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

    if not name or not type_id:
        return "缺少必填字段", 400

    account = Account(
        user_id=user_id,
        name=name,
        type_id=type_id,
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

    # 权限检查：自己的账户或同家庭
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
        account_id=account_id,
        record_month=prev_month
    ).first()
    change_amount = balance - Decimal(str(prev_record.balance)) if prev_record else None

    # 插入或更新（同账户同月份覆盖）
    existing = AccountBalance.query.filter_by(
        account_id=account_id,
        record_month=record_month
    ).first()

    if existing:
        existing.balance = balance
        existing.change_amount = change_amount
    else:
        snapshot = AccountBalance(
            account_id=account_id,
            balance=balance,
            change_amount=change_amount,
            record_month=record_month
        )
        db.session.add(snapshot)

    # 更新账户当前余额为最新快照
    account.current_balance = balance
    db.session.commit()

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
```

**Step 2: 在 `src/main.py` 注册蓝图**

导入行添加：
```python
from routes.account import account_bp
```

注册行添加：
```python
app.register_blueprint(account_bp)
```

**Step 3: 重启验证**

Run: 重启应用，访问 /accounts 应返回 500（模板还没创建），但路由已注册不报 404
Expected: 路由注册成功

**Step 4: Commit**

```bash
git add src/routes/account.py src/main.py
git commit -m "feat: 添加账户管理路由蓝图（CRUD + 月度快照）"
```

---

## Task 3: 账户管理页面模板

**Files:**
- Create: `src/templates/accounts.html`
- Modify: `src/templates/index.html`（顶栏添加"账户"导航链接）
- Modify: `src/static/css/style.css`（账户页面样式）

**Step 1: 创建 `src/templates/accounts.html`**

页面布局：
- 顶栏：标题 + 导航（首页/报表/账户/退出）
- 视图切换（我的/家庭）
- 资产总览卡片：储蓄总额 | 投资总额 | 总资产
- 储蓄账户列表（每个账户：名称、类型、当前余额、本月变化）
- 投资账户列表（同上）
- 创建账户表单（折叠式）
- 录入月度快照表单（折叠式）

沿用现有 CSS 类：`.container`, `.header`, `.card`, `.form-group`, `.form-input`, `.form-select`, `.btn-submit`, `.stats-bar`, `.stat-item`

**Step 2: 在 `src/templates/index.html` 顶栏添加"账户"链接**

在导航区的"报表"链接之后添加：
```html
<a href="{{ url_for('account.account_list', view=current_view) }}" class="nav-link">账户</a>
```

**Step 3: 在 `src/static/css/style.css` 添加账户页样式**

添加账户列表项样式、折叠表单样式等。

**Step 4: 重启验证**

访问 /accounts，应正常渲染账户管理页。

**Step 5: Commit**

```bash
git add src/templates/accounts.html src/templates/index.html src/static/css/style.css
git commit -m "feat: 创建账户管理页面模板"
```

---

## Task 4: 交易关联账户

**Files:**
- Modify: `src/main.py`（add_transaction, edit_transaction, delete_transaction）
- Modify: `src/templates/index.html`（添加账户下拉框）
- Modify: `src/templates/edit_transaction.html`（添加账户下拉框）

**Step 1: 修改首页交易表单，添加账户选填下拉框**

在 `index.html` 的分类选择之后、日期输入之前，添加账户 select：
```html
<div class="form-group">
    <label class="form-label">账户（选填）</label>
    <select name="account_id" class="form-select">
        <option value="">不关联账户</option>
        {% for a in accounts %}
        <option value="{{ a.id }}">{{ a.name }}（{{ a.account_type.name }}）</option>
        {% endfor %}
    </select>
</div>
```

**Step 2: 修改 `main.py` 的 index 函数，传递 accounts 给模板**

```python
from models import Account
# 在 index() 中，查询用户账户
accounts = Account.query.filter_by(user_id=user_id).all()
# 传给 render_template
```

**Step 3: 修改 `main.py` 的 add_transaction，处理 account_id**

```python
account_id = request.form.get('account_id', type=int)
# 创建 transaction 时加上 account_id=account_id or None
# 如果 account_id 有值，更新账户余额：
if account_id:
    account = Account.query.get(account_id)
    if account:
        if transaction_type == 'income':
            account.current_balance += Decimal(amount)
        else:
            account.current_balance -= Decimal(amount)
```

**Step 4: 修改 edit_transaction，处理 account_id 变更时的余额修正**

编辑时如果账户变了，需要反向修正旧账户余额并更新新账户余额。

**Step 5: 修改 delete_transaction，删除时反向修正账户余额**

```python
if transaction.account_id:
    account = Account.query.get(transaction.account_id)
    if account:
        if transaction.type == 'income':
            account.current_balance -= transaction.amount
        else:
            account.current_balance += transaction.amount
```

**Step 6: 修改编辑页面 `edit_transaction.html`，添加账户下拉框**

**Step 7: 重启验证**

添加一笔关联账户的交易，验证账户余额变化正确。

**Step 8: Commit**

```bash
git add src/main.py src/templates/index.html src/templates/edit_transaction.html
git commit -m "feat: 交易支持可选关联账户，自动更新账户余额"
```

---

## Task 5: 资产趋势图 API + 报表页集成

**Files:**
- Modify: `src/routes/reports.py`（添加 asset-trend API）
- Modify: `src/templates/reports.html`（添加资产趋势图）

**Step 1: 在 `src/routes/reports.py` 添加资产趋势 API**

```python
@reports_bp.route('/api/asset-trend')
def api_asset_trend():
    """资产趋势 API
    基于 account_balance 快照数据，返回储蓄/投资/总资产按月汇总
    参数: months (1|3|6|12), view (personal|family)
    返回: { labels: [...], savings: [...], investment: [...], total: [...] }
    """
```

逻辑：
- 查询 AccountBalance JOIN Account JOIN AccountType
- 按月份和 category(savings/investment) 分组汇总
- 生成完整月份标签
- 返回三条曲线数据

**Step 2: 在 `src/templates/reports.html` 添加资产趋势图**

在分类饼图之后添加新的 card：
```html
<!-- 资产趋势图 -->
<div class="card chart-section">
    <div class="card-header">
        <h2 class="card-title">资产趋势</h2>
    </div>
    <div class="chart-container">
        <canvas id="assetTrendChart"></canvas>
    </div>
</div>
```

JS 中添加 `loadAssetTrendChart()` 函数，绘制三条线（储蓄、投资、总资产），使用不同颜色区分。

**Step 3: 重启验证**

在账户管理页录入几个月的快照数据，访问报表页验证资产趋势图显示正确。

**Step 4: Commit**

```bash
git add src/routes/reports.py src/templates/reports.html
git commit -m "feat: 添加资产趋势图（储蓄/投资/总资产曲线）"
```

---

## Task 6: 更新文档和任务清单

**Files:**
- Modify: `TASKS.md`
- Modify: `PROJECT_BRIEF.md`

**Step 1: 更新 TASKS.md，标记 TASK-006 为 DONE**

**Step 2: 更新 PROJECT_BRIEF.md 已完成能力和下一步计划**

**Step 3: Commit**

```bash
git add TASKS.md PROJECT_BRIEF.md
git commit -m "docs: 更新任务清单，标记 TASK-006 为已完成"
```
