# 快捷记账功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 添加常用交易模板（一键填充）和定期交易自动生成（每月固定支出自动创建），减少日常记账操作步骤。

**Architecture:** 新增 2 个数据模型（TransactionTemplate、RecurringTransaction）和 2 个蓝图路由。模板功能在首页添加快捷按钮区域；定期交易在首页路由中触发自动执行。两个功能独立，可分别测试。

**Tech Stack:** Flask/Jinja2、SQLAlchemy、原生 JS

**设计文档:** `docs/superpowers/specs/2026-03-28-quick-entry-design.md`

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `src/models.py` | 新增 TransactionTemplate + RecurringTransaction 模型 |
| 新建 | `src/routes/template.py` | 快捷模板 CRUD 蓝图 |
| 新建 | `src/routes/recurring.py` | 定期交易 CRUD + 自动执行蓝图 |
| 新建 | `src/templates/quick_templates.html` | 快捷模板管理页面 |
| 新建 | `src/templates/recurring.html` | 定期交易管理页面 |
| 修改 | `src/templates/index.html` | 添加交易表单上方增加模板快捷按钮 |
| 修改 | `src/templates/base.html` | 导航「设置 ▾」和侧滑菜单增加两个入口 |
| 修改 | `src/main.py` | 注册蓝图 + 首页路由调用定期交易处理 |

---

### Task 1: 新增数据模型

**Files:**
- Modify: `src/models.py`

**上下文：** models.py 当前约 330 行，包含 12 个模型。在文件末尾追加 2 个新模型。参考现有模型风格（如 SavingsPlan）。

- [ ] **Step 1: 在 models.py 末尾追加 TransactionTemplate 模型**

```python
class TransactionTemplate(db.Model):
    """常用交易模板"""
    __tablename__ = 'transaction_templates'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' / 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    use_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[user_id])
    category = db.relationship('Category', foreign_keys=[category_id])
    account = db.relationship('Account', foreign_keys=[account_id])
```

- [ ] **Step 2: 追加 RecurringTransaction 模型**

```python
class RecurringTransaction(db.Model):
    """定期交易"""
    __tablename__ = 'recurring_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' / 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    frequency = db.Column(db.String(20), nullable=False)  # 'monthly' / 'weekly' / 'custom'
    interval_days = db.Column(db.Integer, nullable=True)  # frequency=custom 时
    day_of_month = db.Column(db.Integer, nullable=True)   # frequency=monthly 时，1-28
    day_of_week = db.Column(db.Integer, nullable=True)    # frequency=weekly 时，0=周一
    next_run_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[user_id])
    category = db.relationship('Category', foreign_keys=[category_id])
    account = db.relationship('Account', foreign_keys=[account_id])
```

- [ ] **Step 3: 启动应用验证模型加载无错误**

Run: `cd src && python3 -c "from models import TransactionTemplate, RecurringTransaction; print('OK')" && cd ..`

- [ ] **Step 4: Commit**

```bash
git add src/models.py
git commit -m "feat: 新增 TransactionTemplate 和 RecurringTransaction 数据模型"
```

---

### Task 2: 快捷模板路由 + 管理页面

**Files:**
- Create: `src/routes/template.py`
- Create: `src/templates/quick_templates.html`
- Modify: `src/main.py` (注册蓝图)
- Modify: `src/templates/base.html` (导航新增入口)

**上下文：** 参考 `src/routes/savings.py` 的蓝图结构和 `src/templates/savings.html` 的页面布局。

- [ ] **Step 1: 创建 src/routes/template.py**

```python
"""快捷模板路由模块"""
from decimal import Decimal
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from models import db, User, TransactionTemplate, Category, Account

template_bp = Blueprint('template', __name__, url_prefix='/templates')


@template_bp.route('/')
def template_list():
    """快捷模板管理页面"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    templates = TransactionTemplate.query.filter_by(user_id=user_id)\
        .order_by(TransactionTemplate.use_count.desc()).all()

    categories = Category.query.all()
    accounts = Account.query.filter_by(user_id=user_id).all()

    return render_template('quick_templates.html',
                           templates=templates,
                           categories=categories,
                           accounts=accounts,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@template_bp.route('/add', methods=['POST'])
def add_template():
    """创建快捷模板"""
    user_id = session.get('user_id')
    name = request.form.get('name')
    amount = request.form.get('amount')
    tx_type = request.form.get('type')
    category_id = request.form.get('category_id', type=int)
    description = request.form.get('description')
    account_id = request.form.get('account_id', type=int)

    if not all([name, amount, tx_type]):
        flash('请填写模板名称、金额和类型', 'error')
        return redirect(url_for('template.template_list'))

    tpl = TransactionTemplate(
        user_id=user_id, name=name,
        amount=Decimal(amount), type=tx_type,
        category_id=category_id or None,
        description=description or None,
        account_id=account_id or None
    )
    db.session.add(tpl)
    db.session.commit()
    flash('模板创建成功', 'success')
    return redirect(url_for('template.template_list'))


@template_bp.route('/<int:tpl_id>/edit', methods=['POST'])
def edit_template(tpl_id):
    """编辑快捷模板"""
    tpl = TransactionTemplate.query.get_or_404(tpl_id)
    tpl.name = request.form.get('name', tpl.name)
    tpl.amount = Decimal(request.form.get('amount', str(tpl.amount)))
    tpl.type = request.form.get('type', tpl.type)
    tpl.category_id = request.form.get('category_id', type=int) or None
    tpl.description = request.form.get('description') or None
    tpl.account_id = request.form.get('account_id', type=int) or None
    db.session.commit()
    flash('模板已更新', 'success')
    return redirect(url_for('template.template_list'))


@template_bp.route('/<int:tpl_id>/delete', methods=['POST'])
def delete_template(tpl_id):
    """删除快捷模板"""
    tpl = TransactionTemplate.query.get_or_404(tpl_id)
    db.session.delete(tpl)
    db.session.commit()
    flash('模板已删除', 'success')
    return redirect(url_for('template.template_list'))
```

- [ ] **Step 2: 创建 src/templates/quick_templates.html**

继承 `base.html`，参照 `categories.html` 的卡片列表风格。包含：
- 统计栏（模板数量）
- 添加模板按钮（打开抽屉表单）
- 模板列表（名称、金额、类型badge、分类、使用次数、编辑/删除按钮）
- 抽屉浮层：添加/编辑模板表单（名称、金额、类型选择、分类下拉、账户下拉、备注）
- 空状态提示

- [ ] **Step 3: 注册蓝图到 main.py**

在 `src/main.py` 的 import 区域添加：
```python
from routes.template import template_bp
```
在 register_blueprint 区域添加：
```python
app.register_blueprint(template_bp)
```

- [ ] **Step 4: 更新 base.html 导航**

在桌面端导航「设置 ▾」下拉菜单中添加：
```html
<a href="{{ url_for('template.template_list') }}" class="nav-dropdown-item">快捷模板</a>
```

在侧滑菜单的「分类管理」之后添加：
```html
<a href="{{ url_for('template.template_list') }}" class="side-menu-item">⚡ 快捷模板</a>
```

- [ ] **Step 5: 验证页面可访问**

启动应用，登录后访问 `/templates/` 确认页面正常渲染。

- [ ] **Step 6: Commit**

```bash
git add src/routes/template.py src/templates/quick_templates.html src/main.py src/templates/base.html
git commit -m "feat: 快捷模板管理（CRUD + 管理页面 + 导航入口）"
```

---

### Task 3: 首页集成模板快捷按钮

**Files:**
- Modify: `src/main.py` (首页路由传入模板数据)
- Modify: `src/templates/index.html` (添加模板按钮区域)
- Modify: `src/routes/template.py` (新增 API 端点：使用模板时 use_count+1)

**上下文：** 首页路由在 `src/main.py` 第 49 行 `@app.route('/')`。需要查询用户的模板列表传给模板。index.html 在「添加交易」表单（第 49-86 行）上方插入模板按钮区域。

- [ ] **Step 1: 修改首页路由，查询模板数据**

在首页路由函数中添加查询：
```python
from models import TransactionTemplate
# 在 render_template 调用之前
quick_templates = TransactionTemplate.query.filter_by(user_id=user_id)\
    .order_by(TransactionTemplate.use_count.desc()).limit(6).all()
```

将 `quick_templates=quick_templates` 传入 render_template。

- [ ] **Step 2: 修改 index.html，在「添加交易」表单上方添加模板按钮**

在 `<!-- 添加交易表单 -->` 之前插入：
```html
{% if quick_templates %}
<div class="card">
    <div class="card-header">
        <h2 class="card-title">快捷录入</h2>
        <a href="{{ url_for('template.template_list') }}" class="chart-detail-link">管理模板</a>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 8px; padding: 16px;">
        {% for tpl in quick_templates %}
        <button class="quick-tpl-btn" type="button"
                data-amount="{{ tpl.amount }}"
                data-type="{{ tpl.type }}"
                data-category="{{ tpl.category_id or '' }}"
                data-description="{{ tpl.description or '' }}"
                data-account="{{ tpl.account_id or '' }}"
                data-id="{{ tpl.id }}"
                onclick="applyTemplate(this)">
            {{ tpl.name }} <span style="opacity:0.6">¥{{ "%.0f"|format(tpl.amount) }}</span>
        </button>
        {% endfor %}
    </div>
</div>
{% endif %}
```

- [ ] **Step 3: 在 index.html 的 scripts block 中添加 applyTemplate 函数**

```javascript
function applyTemplate(btn) {
    // 填充表单
    var form = document.querySelector('#add-form form');
    var typeRadios = form.querySelectorAll('input[name="type"]');
    typeRadios.forEach(function(r) { r.checked = r.value === btn.dataset.type; });

    form.querySelector('input[name="amount"]').value = btn.dataset.amount;

    var catSelect = form.querySelector('select[name="category"]');
    if (catSelect && btn.dataset.category) catSelect.value = btn.dataset.category;

    var descInput = form.querySelector('input[name="description"]');
    if (descInput && btn.dataset.description) descInput.value = btn.dataset.description;

    var acctSelect = form.querySelector('select[name="account"]');
    if (acctSelect && btn.dataset.account) acctSelect.value = btn.dataset.account;

    // 滚动到表单
    form.scrollIntoView({behavior: 'smooth'});

    // 更新使用次数
    fetch('/templates/' + btn.dataset.id + '/use', {method: 'POST'});
}
```

- [ ] **Step 4: 在 template.py 添加 use 端点**

```python
@template_bp.route('/<int:tpl_id>/use', methods=['POST'])
def use_template(tpl_id):
    """记录模板使用次数"""
    tpl = TransactionTemplate.query.get_or_404(tpl_id)
    tpl.use_count = (tpl.use_count or 0) + 1
    db.session.commit()
    return '', 204
```

- [ ] **Step 5: 添加快捷按钮 CSS**

在 `src/static/css/style.css` 末尾添加：
```css
/* --- 快捷模板按钮 --- */
.quick-tpl-btn {
    padding: 8px 16px;
    background: var(--color-income-light);
    border: 1px solid var(--color-income);
    border-radius: var(--radius-full);
    cursor: pointer;
    font-size: 13px;
    color: var(--color-text-primary);
    transition: background var(--transition-fast);
    min-height: 36px;
}

.quick-tpl-btn:hover {
    background: var(--color-income);
    color: white;
}
```

- [ ] **Step 6: Commit**

```bash
git add src/main.py src/templates/index.html src/routes/template.py src/static/css/style.css
git commit -m "feat: 首页集成快捷模板按钮（一键填充表单）"
```

---

### Task 4: 定期交易路由 + 管理页面

**Files:**
- Create: `src/routes/recurring.py`
- Create: `src/templates/recurring.html`
- Modify: `src/main.py` (注册蓝图)
- Modify: `src/templates/base.html` (导航新增入口)

**上下文：** 参考 Task 2 的模板路由结构。定期交易多了频率字段（monthly/weekly/custom）和启用/暂停开关。

- [ ] **Step 1: 创建 src/routes/recurring.py**

```python
"""定期交易路由模块"""
from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from models import db, User, RecurringTransaction, Transaction, Category, Account

recurring_bp = Blueprint('recurring', __name__, url_prefix='/recurring')


def _calculate_next_run(item):
    """计算下次执行日期"""
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
    return current + timedelta(days=30)  # fallback


def process_recurring_transactions(user_id):
    """处理到期的定期交易，自动创建交易记录"""
    today = date.today()
    due_items = RecurringTransaction.query.filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_run_date <= today
    ).all()

    created_count = 0
    for item in due_items:
        # 补漏：可能有多个周期到期
        while item.next_run_date <= today:
            tx = Transaction(
                user_id=user_id,
                amount=item.amount,
                type=item.type,
                category_id=item.category_id,
                description=f"[定期] {item.name}" + (f" - {item.description}" if item.description else ""),
                transaction_date=item.next_run_date,
                source='recurring',
                account_id=item.account_id
            )
            db.session.add(tx)
            created_count += 1
            item.next_run_date = _calculate_next_run(item)

    if created_count:
        db.session.commit()
    return created_count


@recurring_bp.route('/')
def recurring_list():
    """定期交易管理页面"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    items = RecurringTransaction.query.filter_by(user_id=user_id)\
        .order_by(RecurringTransaction.is_active.desc(), RecurringTransaction.next_run_date).all()

    categories = Category.query.all()
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
    tx_type = request.form.get('type')
    frequency = request.form.get('frequency')
    category_id = request.form.get('category_id', type=int)
    description = request.form.get('description')
    account_id = request.form.get('account_id', type=int)

    if not all([name, amount, tx_type, frequency]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('recurring.recurring_list'))

    day_of_month = request.form.get('day_of_month', type=int)
    day_of_week = request.form.get('day_of_week', type=int)
    interval_days = request.form.get('interval_days', type=int)

    # 计算首次执行日期
    today = date.today()
    if frequency == 'monthly':
        dom = min(day_of_month or 1, 28)
        if today.day <= dom:
            next_run = date(today.year, today.month, dom)
        else:
            m = today.month + 1
            y = today.year
            if m > 12:
                m, y = 1, y + 1
            next_run = date(y, m, dom)
    elif frequency == 'weekly':
        dow = day_of_week or 0
        days_ahead = dow - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = today + timedelta(days=days_ahead)
    else:
        next_run = today + timedelta(days=interval_days or 30)

    item = RecurringTransaction(
        user_id=user_id, name=name,
        amount=Decimal(amount), type=tx_type,
        category_id=category_id or None,
        description=description or None,
        account_id=account_id or None,
        frequency=frequency,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        interval_days=interval_days,
        next_run_date=next_run
    )
    db.session.add(item)
    db.session.commit()
    flash('定期交易创建成功', 'success')
    return redirect(url_for('recurring.recurring_list'))


@recurring_bp.route('/<int:item_id>/toggle', methods=['POST'])
def toggle_recurring(item_id):
    """启用/暂停定期交易"""
    item = RecurringTransaction.query.get_or_404(item_id)
    item.is_active = not item.is_active
    if item.is_active and item.next_run_date < date.today():
        item.next_run_date = date.today()
    db.session.commit()
    flash('已' + ('启用' if item.is_active else '暂停'), 'success')
    return redirect(url_for('recurring.recurring_list'))


@recurring_bp.route('/<int:item_id>/delete', methods=['POST'])
def delete_recurring(item_id):
    """删除定期交易"""
    item = RecurringTransaction.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('recurring.recurring_list'))
```

- [ ] **Step 2: 创建 src/templates/recurring.html**

继承 `base.html`，参照 `quick_templates.html` 布局。包含：
- 定期交易列表（名称、金额、频率描述、下次执行日期、状态开关、删除按钮）
- 频率描述显示：monthly → "每月X号"、weekly → "每周X"、custom → "每X天"
- 状态开关：绿色=启用、灰色=暂停，点击切换
- 添加抽屉表单：名称、金额、类型、频率选择（monthly/weekly/custom）、对应的日期字段（day_of_month/day_of_week/interval_days）、分类、账户、备注
- JS 控制频率选择时显示/隐藏对应字段
- 空状态提示

- [ ] **Step 3: 注册蓝图 + 导航入口**

在 `src/main.py` 添加：
```python
from routes.recurring import recurring_bp
app.register_blueprint(recurring_bp)
```

在 `src/templates/base.html` 桌面导航和侧滑菜单中添加「定期交易」入口。

- [ ] **Step 4: 验证页面可访问**

- [ ] **Step 5: Commit**

```bash
git add src/routes/recurring.py src/templates/recurring.html src/main.py src/templates/base.html
git commit -m "feat: 定期交易管理（CRUD + 自动执行 + 管理页面）"
```

---

### Task 5: 首页集成定期交易自动执行

**Files:**
- Modify: `src/main.py` (首页路由调用 process_recurring_transactions)

**上下文：** 首页路由在 `src/main.py` 第 49 行。需要在渲染页面前调用 `process_recurring_transactions(user_id)` 自动创建到期的定期交易。

- [ ] **Step 1: 在首页路由中调用定期交易处理**

在首页路由函数开头（获取 user_id 后）添加：
```python
from routes.recurring import process_recurring_transactions

# 处理到期的定期交易
recurring_count = process_recurring_transactions(user_id)
if recurring_count:
    flash(f'已自动创建 {recurring_count} 笔定期交易', 'success')
```

- [ ] **Step 2: 验证自动执行**

创建一个定期交易（设置 next_run_date 为今天），访问首页确认自动创建了交易记录。

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: 首页自动执行到期的定期交易"
```

---

### Task 6: 测试 + 更新文档 + 部署

**Files:**
- Modify: `PROJECT_BRIEF.md`

- [ ] **Step 1: 运行现有测试确认无破坏**

Run: `python3 -m pytest tests/test_importers.py tests/test_upload.py -v`

- [ ] **Step 2: 浏览器验证**

1. 登录系统
2. 进入「快捷模板」页面，创建一个模板（如"午餐 30元 支出"）
3. 回到首页，确认看到快捷按钮，点击后表单自动填充
4. 进入「定期交易」页面，创建一个定期交易（如"房租 每月1号"）
5. 确认首页自动创建交易

- [ ] **Step 3: 更新 PROJECT_BRIEF.md**

在已可用能力中添加：
```
- [x] 快捷模板（常用交易一键填充，按使用频率排序）
- [x] 定期交易自动生成（月/周/自定义周期，请求触发 + 补漏）
```

更新下一步 5 件事。

- [ ] **Step 4: Commit + 推送 + 部署**

```bash
git add PROJECT_BRIEF.md
git commit -m "docs: 更新 PROJECT_BRIEF 记录快捷记账功能"
git push origin main
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137 "sudo bash -c 'cd /opt/family-finance && git pull origin main && systemctl restart family-finance'"
```
