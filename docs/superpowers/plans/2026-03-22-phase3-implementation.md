# Phase 3 实施计划：储蓄计划 + 宝宝基金 + 批量导入

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为家庭财务系统添加储蓄计划管理、宝宝基金记录和 CSV/Excel 批量导入功能

**Architecture:** 三个独立 Flask Blueprint（savings_bp、baby_fund_bp、upload_bp），各自拥有路由、模板和测试。共享的数据模型统一定义在 models.py。文件解析逻辑独立为 utils/importers.py。

**Tech Stack:** Flask, SQLAlchemy, openpyxl (Excel), Chart.js (已有), Tailwind-style CSS (已有)

**Spec:** `docs/superpowers/specs/2026-03-22-phase3-design.md`

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `src/routes/savings.py` | 储蓄计划蓝图：列表、创建/编辑/删除计划、录入/删除记录 |
| `src/routes/baby_fund.py` | 宝宝基金蓝图：列表、创建/编辑/删除记录（含交易联动） |
| `src/routes/upload.py` | 批量导入蓝图：上传页面、解析、确认导入、模板下载 |
| `src/utils/importers.py` | 文件解析器：微信/支付宝/标准模板 CSV/Excel 解析 |
| `src/templates/savings.html` | 储蓄计划页面模板 |
| `src/templates/baby_fund.html` | 宝宝基金页面模板 |
| `src/templates/upload.html` | 批量导入页面模板 |
| `src/static/import_template.csv` | 标准导入模板文件 |
| `tests/test_savings.py` | 储蓄计划测试 |
| `tests/test_baby_fund.py` | 宝宝基金测试 |
| `tests/test_importers.py` | 文件解析器测试 |
| `tests/test_upload.py` | 批量导入路由测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/models.py:276+` | 新增 SavingsPlan、SavingsRecord、BabyFund、ImportRecord 4个模型 |
| `src/database.py:37` | 在 create_app 中添加 `MAX_CONTENT_LENGTH` 配置 |
| `src/main.py:8-23` | import 并注册三个新蓝图 |
| `src/templates/index.html:24-29` | header nav 添加储蓄/宝宝/导入链接 |
| `src/templates/accounts.html:23-26` | header nav 添加储蓄/宝宝/导入链接 |
| `src/templates/reports.html` | header nav 添加储蓄/宝宝/导入链接 |
| `src/templates/categories.html` | header nav 添加储蓄/宝宝/导入链接 |
| `src/static/css/style.css` | 追加储蓄/宝宝基金/导入页面样式 |
| `requirements.txt` | 添加 `openpyxl==3.1.2` |

---

## Task 1: 数据模型 — 新增 4 个模型

**Files:**
- Modify: `src/models.py:276+`（在文件末尾追加）
- Modify: `src/database.py:2`（import 新模型名）
- Test: `tests/test_savings.py`

- [ ] **Step 1: 写 SavingsPlan 和 SavingsRecord 模型的失败测试**

创建 `tests/test_savings.py`:
```python
"""储蓄计划模型和路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date
from models import db, User, Family, SavingsPlan, SavingsRecord
from database import create_app


def _create_test_app():
    """创建测试用 Flask 应用"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['TESTING'] = True
    return app, temp_db.name


def test_savings_plan_model():
    """测试储蓄计划模型 CRUD"""
    app, db_path = _create_test_app()
    with app.app_context():
        db.create_all()

        user = User(username='test_saver', nickname='储蓄者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        # 创建月度计划
        plan = SavingsPlan(
            name='月度储蓄', type='monthly',
            target_amount=Decimal('50000'), year=2026, month=3,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()

        assert plan.id is not None
        assert plan.name == '月度储蓄'
        assert plan.type == 'monthly'
        d = plan.to_dict()
        assert d['target_amount'] == 50000.0
        assert d['year'] == 2026
        print("✅ test_savings_plan_model passed")

    os.unlink(db_path)


def test_savings_record_model():
    """测试储蓄记录模型"""
    app, db_path = _create_test_app()
    with app.app_context():
        db.create_all()

        user = User(username='test_rec', nickname='记录者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        plan = SavingsPlan(
            name='年度储蓄', type='annual',
            target_amount=Decimal('600000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()

        record = SavingsRecord(
            plan_id=plan.id, user_id=user.id,
            amount=Decimal('35000'), record_date=date(2026, 3, 15),
            description='3月储蓄'
        )
        db.session.add(record)
        db.session.commit()

        assert record.id is not None
        assert record.plan_id == plan.id
        d = record.to_dict()
        assert d['amount'] == 35000.0
        print("✅ test_savings_record_model passed")

    os.unlink(db_path)


if __name__ == '__main__':
    test_savings_plan_model()
    test_savings_record_model()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_savings.py 2>&1 | tail -n 20`
Expected: ImportError: cannot import name 'SavingsPlan'

- [ ] **Step 3: 在 models.py 末尾实现 4 个模型**

在 `src/models.py` 文件末尾（第 276 行之后）追加：

```python
class SavingsPlan(db.Model):
    """储蓄计划表"""
    __tablename__ = 'savings_plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'monthly' 或 'annual'
    target_amount = db.Column(db.Numeric(10, 2), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=True)  # 仅月度计划，1-12
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='savings_plans')
    records = db.relationship('SavingsRecord', backref='plan', lazy=True,
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f"<SavingsPlan {self.id}: {self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'target_amount': float(self.target_amount),
            'year': self.year,
            'month': self.month,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SavingsRecord(db.Model):
    """储蓄记录表"""
    __tablename__ = 'savings_records'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('savings_plans.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    record_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship('User', foreign_keys=[user_id], backref='savings_records')
    account = db.relationship('Account', foreign_keys=[account_id])

    def __repr__(self):
        return f"<SavingsRecord {self.id}: plan={self.plan_id} amount={self.amount}>"

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'account_id': self.account_id,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BabyFund(db.Model):
    """宝宝基金表"""
    __tablename__ = 'baby_funds'

    VALID_EVENT_TYPES = ['满月', '生日', '红包', '其他']

    id = db.Column(db.Integer, primary_key=True)
    giver_name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='baby_funds')
    account = db.relationship('Account', foreign_keys=[account_id])
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id])

    def __repr__(self):
        return f"<BabyFund {self.id}: {self.giver_name} ¥{self.amount}>"

    def to_dict(self):
        return {
            'id': self.id,
            'giver_name': self.giver_name,
            'amount': float(self.amount),
            'account_id': self.account_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'event_type': self.event_type,
            'notes': self.notes,
            'transaction_id': self.transaction_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ImportRecord(db.Model):
    """导入记录表"""
    __tablename__ = 'import_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name = db.Column(db.String(200), nullable=False)
    import_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_rows = db.Column(db.Integer, nullable=True)
    imported_count = db.Column(db.Integer, nullable=True)
    skipped_count = db.Column(db.Integer, nullable=True)
    duplicate_count = db.Column(db.Integer, nullable=True)
    source_type = db.Column(db.String(20), nullable=True)  # 'wechat'/'alipay'/'template'
    status = db.Column(db.String(20), default='completed')

    importer = db.relationship('User', foreign_keys=[user_id], backref='import_records')

    def __repr__(self):
        return f"<ImportRecord {self.id}: {self.file_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'import_time': self.import_time.isoformat() if self.import_time else None,
            'total_rows': self.total_rows,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'duplicate_count': self.duplicate_count,
            'source_type': self.source_type,
            'status': self.status
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_savings.py 2>&1 | tail -n 20`
Expected: 两个测试都 ✅ passed

- [ ] **Step 5: 提交**

```bash
git add src/models.py tests/test_savings.py
git commit -m "feat(models): 添加 SavingsPlan、SavingsRecord、BabyFund、ImportRecord 模型"
```

---

## Task 2: 储蓄计划路由 + 模板

**Files:**
- Create: `src/routes/savings.py`
- Create: `src/templates/savings.html`
- Modify: `src/main.py:8-23`（注册蓝图）
- Test: `tests/test_savings.py`（追加路由测试）

- [ ] **Step 1: 写储蓄计划路由的失败测试**

在 `tests/test_savings.py` 末尾追加：
```python
def test_savings_routes():
    """测试储蓄计划路由"""
    app, db_path = _create_test_app()

    # 注册蓝图
    from routes.savings import savings_bp
    app.register_blueprint(savings_bp)

    with app.app_context():
        db.create_all()

        # 创建测试用户
        user = User(username='route_test', nickname='路由测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()

    # 模拟登录
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = 'route_test'

    # 测试列表页
    resp = client.get('/savings')
    assert resp.status_code == 200

    # 测试创建月度计划
    resp = client.post('/savings/plan/add', data={
        'name': '月度储蓄',
        'type': 'monthly',
        'target_amount': '50000',
        'year': '2026',
        'month': '3'
    }, follow_redirects=False)
    assert resp.status_code == 302

    # 验证计划已创建
    with app.app_context():
        plan = SavingsPlan.query.first()
        assert plan is not None
        assert plan.name == '月度储蓄'

        # 测试录入储蓄记录
        resp = client.post('/savings/record/add', data={
            'plan_id': str(plan.id),
            'amount': '35000',
            'record_date': '2026-03-15',
            'description': '3月储蓄'
        }, follow_redirects=False)
        assert resp.status_code == 302

        record = SavingsRecord.query.first()
        assert record is not None
        assert float(record.amount) == 35000.0

    print("✅ test_savings_routes passed")
    os.unlink(db_path)


def test_savings_progress_calculation():
    """测试进度计算逻辑"""
    app, db_path = _create_test_app()
    from routes.savings import savings_bp
    app.register_blueprint(savings_bp)

    with app.app_context():
        db.create_all()
        user = User(username='progress_test', nickname='进度测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        # 创建目标 10 万的计划
        plan = SavingsPlan(
            name='进度测试', type='annual',
            target_amount=Decimal('100000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()

        # 录入两笔：3万 + 4万 = 7万，进度应为 70%
        for amt in ['30000', '40000']:
            r = SavingsRecord(
                plan_id=plan.id, user_id=user.id,
                amount=Decimal(amt), record_date=date(2026, 3, 1)
            )
            db.session.add(r)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = 'progress_test'

    resp = client.get('/savings')
    assert resp.status_code == 200
    # 验证页面包含进度数据（70%）
    assert b'70' in resp.data

    # 测试进度上限 100%：再录入 5 万（总 12 万 > 10 万目标）
    with app.app_context():
        r = SavingsRecord(
            plan_id=plan.id, user_id=user.id,
            amount=Decimal('50000'), record_date=date(2026, 3, 2)
        )
        db.session.add(r)
        db.session.commit()

    resp = client.get('/savings')
    assert b'100' in resp.data  # 进度上限 100%

    print("✅ test_savings_progress_calculation passed")
    os.unlink(db_path)


def test_savings_edit_plan():
    """测试编辑储蓄计划"""
    app, db_path = _create_test_app()
    from routes.savings import savings_bp
    app.register_blueprint(savings_bp)

    with app.app_context():
        db.create_all()
        user = User(username='edit_test', nickname='编辑测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        plan = SavingsPlan(
            name='旧名称', type='annual',
            target_amount=Decimal('100000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()
        plan_id = plan.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id

    resp = client.post(f'/savings/plan/{plan_id}/edit', data={
        'name': '新名称', 'target_amount': '200000'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        plan = SavingsPlan.query.get(plan_id)
        assert plan.name == '新名称'
        assert float(plan.target_amount) == 200000.0

    print("✅ test_savings_edit_plan passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_savings_plan_model()
    test_savings_record_model()
    test_savings_routes()
    test_savings_progress_calculation()
    test_savings_edit_plan()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_savings.py 2>&1 | tail -n 20`
Expected: ImportError: cannot import name 'savings_bp'

- [ ] **Step 3: 实现储蓄计划路由**

创建 `src/routes/savings.py`（参考 `src/routes/account.py` 的模式：Blueprint + `_get_family_*` 辅助函数 + session 用户检查）：

```python
"""储蓄计划路由模块"""
from datetime import datetime
from decimal import Decimal

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
    current_view = request.args.get('view', 'personal')

    member_ids = _get_family_member_ids(user_id, current_view)

    # 查询计划
    plans = SavingsPlan.query.filter(
        SavingsPlan.created_by.in_(member_ids)
    ).order_by(SavingsPlan.created_at.desc()).all()

    # 为每个计划计算进度
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
        })
        total_target += plan.target_amount
        total_saved += saved

    overall_progress = float(total_saved / total_target * 100) if total_target else 0

    # 获取账户列表（用于录入储蓄记录表单）
    accounts = Account.query.filter(Account.user_id.in_(member_ids)).all()

    return render_template('savings.html',
                           plan_data=plan_data,
                           total_target=float(total_target),
                           total_saved=float(total_saved),
                           overall_progress=min(overall_progress, 100),
                           accounts=accounts,
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
        flash('请填写所有必填字段')
        return redirect(url_for('savings.savings_list'))

    # 年度计划强制置空 month
    if plan_type == 'annual':
        month = None
    elif plan_type == 'monthly' and (not month or month < 1 or month > 12):
        flash('月度计划需要选择有效月份(1-12)')
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
    db.session.delete(plan)  # cascade='all, delete-orphan' 会级联删除 records
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
        flash('请填写所有必填字段')
        return redirect(url_for('savings.savings_list'))

    try:
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('日期格式错误')
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


@savings_bp.route('/record/<int:record_id>/delete', methods=['POST'])
def delete_record(record_id):
    """删除储蓄记录"""
    record = SavingsRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    return redirect(url_for('savings.savings_list'))
```

- [ ] **Step 4: 创建储蓄计划模板**

创建 `src/templates/savings.html`。关键要素：
- 复制 `accounts.html` 的 header/nav/视图切换结构
- 顶部统计栏：年度目标、已储蓄、完成率
- 计划卡片列表（每个卡片含进度条）
- 两个抽屉浮层表单：创建计划 + 录入储蓄
- nav 链接加入：首页、分类、报表、账户、**储蓄**、宝宝、导入、家庭、退出

- [ ] **Step 5: 在 main.py 注册蓝图**

在 `src/main.py` 第 8 行的 import 区域添加：
```python
from routes.savings import savings_bp
```
在第 23 行后添加：
```python
app.register_blueprint(savings_bp)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_savings.py 2>&1 | tail -n 20`
Expected: 三个测试都 ✅ passed

- [ ] **Step 7: 手动验证**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && source venv/bin/activate && python src/main.py`
访问 http://localhost:5001/savings 确认页面正常渲染

- [ ] **Step 8: 提交**

```bash
git add src/routes/savings.py src/templates/savings.html src/main.py tests/test_savings.py
git commit -m "feat(savings): 储蓄计划管理功能（列表+创建+录入+删除+进度条）"
```

---

## Task 3: 宝宝基金路由 + 模板

**Files:**
- Create: `src/routes/baby_fund.py`
- Create: `src/templates/baby_fund.html`
- Modify: `src/main.py`（注册蓝图）
- Test: `tests/test_baby_fund.py`

- [ ] **Step 1: 写宝宝基金的失败测试**

创建 `tests/test_baby_fund.py`:
```python
"""宝宝基金模型和路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date
from models import db, User, Family, BabyFund, Transaction, Category, TransactionModification
from database import create_app


def _create_test_app():
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['TESTING'] = True
    return app, temp_db.name


def test_baby_fund_creates_transaction():
    """测试创建宝宝基金时自动生成收入交易"""
    app, db_path = _create_test_app()
    from routes.baby_fund import baby_fund_bp
    app.register_blueprint(baby_fund_bp)

    with app.app_context():
        db.create_all()

        # 创建预设分类（需要 '宝宝基金' 分类或使用现有收入分类）
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)

        user = User(username='parent', nickname='家长')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = 'parent'

    # 添加宝宝基金
    resp = client.post('/baby-fund/add', data={
        'giver_name': '外婆',
        'amount': '10000',
        'event_date': '2026-03-01',
        'event_type': '生日',
        'notes': '生日红包'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        fund = BabyFund.query.first()
        assert fund is not None
        assert fund.giver_name == '外婆'
        assert fund.transaction_id is not None

        # 验证自动生成的交易
        txn = Transaction.query.get(fund.transaction_id)
        assert txn is not None
        assert txn.type == 'income'
        assert float(txn.amount) == 10000.0

    print("✅ test_baby_fund_creates_transaction passed")
    os.unlink(db_path)


def test_baby_fund_delete_cascades():
    """测试删除宝宝基金时级联删除交易"""
    app, db_path = _create_test_app()
    from routes.baby_fund import baby_fund_bp
    app.register_blueprint(baby_fund_bp)

    with app.app_context():
        db.create_all()

        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='parent2', nickname='家长2')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = 'parent2'

    # 添加再删除
    client.post('/baby-fund/add', data={
        'giver_name': '奶奶', 'amount': '8000',
        'event_date': '2026-01-28', 'event_type': '红包'
    })

    with app.app_context():
        fund = BabyFund.query.first()
        fund_id = fund.id
        txn_id = fund.transaction_id

    resp = client.post(f'/baby-fund/{fund_id}/delete', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        assert BabyFund.query.get(fund_id) is None
        assert Transaction.query.get(txn_id) is None

    print("✅ test_baby_fund_delete_cascades passed")
    os.unlink(db_path)


def test_baby_fund_edit_syncs_transaction():
    """测试编辑宝宝基金时同步更新关联交易"""
    app, db_path = _create_test_app()
    from routes.baby_fund import baby_fund_bp
    app.register_blueprint(baby_fund_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='editor', nickname='编辑者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = 'editor'

    # 先添加
    client.post('/baby-fund/add', data={
        'giver_name': '姑姑', 'amount': '5000',
        'event_date': '2026-03-01', 'event_type': '红包'
    })

    with app.app_context():
        fund = BabyFund.query.first()
        fund_id = fund.id

    # 编辑金额和给钱人
    resp = client.post(f'/baby-fund/{fund_id}/edit', data={
        'giver_name': '姑妈', 'amount': '8000',
        'event_date': '2026-03-01', 'event_type': '生日'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        fund = BabyFund.query.get(fund_id)
        assert fund.giver_name == '姑妈'
        assert float(fund.amount) == 8000.0
        # 验证关联交易也更新了
        txn = Transaction.query.get(fund.transaction_id)
        assert float(txn.amount) == 8000.0

    print("✅ test_baby_fund_edit_syncs_transaction passed")
    os.unlink(db_path)


def test_baby_fund_invalid_event_type():
    """测试无效的事件类型被拒绝"""
    app, db_path = _create_test_app()
    from routes.baby_fund import baby_fund_bp
    app.register_blueprint(baby_fund_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='validator', nickname='校验者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id

    resp = client.post('/baby-fund/add', data={
        'giver_name': '测试', 'amount': '1000',
        'event_date': '2026-03-01', 'event_type': '无效类型'
    }, follow_redirects=True)

    with app.app_context():
        assert BabyFund.query.count() == 0  # 不应创建

    print("✅ test_baby_fund_invalid_event_type passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_baby_fund_creates_transaction()
    test_baby_fund_delete_cascades()
    test_baby_fund_edit_syncs_transaction()
    test_baby_fund_invalid_event_type()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_baby_fund.py 2>&1 | tail -n 20`
Expected: ImportError: cannot import name 'baby_fund_bp'

- [ ] **Step 3: 实现宝宝基金路由**

创建 `src/routes/baby_fund.py`。关键逻辑：
- `add`: 校验 event_type（必须在 `BabyFund.VALID_EVENT_TYPES` 中），创建 BabyFund + 自动创建 Transaction（type='income'，description=f"宝宝基金: {giver_name} ({event_type})"）
- `delete`: 先删 TransactionModification，再删 Transaction，最后删 BabyFund
- `edit`: 更新 BabyFund 字段，同步更新关联 Transaction 的金额和描述（`txn.amount = new_amount; txn.description = f"宝宝基金: {new_giver} ({new_event_type})"）
- 列表页：统计总额和记录数，支持个人/家庭视图
- `event_type` 校验（add 和 edit 中都要加）：
```python
if event_type and event_type not in BabyFund.VALID_EVENT_TYPES:
    flash('无效的事件类型')
    return redirect(url_for('baby_fund.baby_fund_list'))
```

- [ ] **Step 4: 创建宝宝基金模板**

创建 `src/templates/baby_fund.html`。关键要素：
- 复制 header/nav 结构
- 顶部统计栏：基金总额、记录数
- 记录列表（事件类型图标 + 给钱人 + 金额 + 日期）
- 抽屉浮层表单：添加宝宝基金

- [ ] **Step 5: 在 main.py 注册蓝图**

```python
from routes.baby_fund import baby_fund_bp
app.register_blueprint(baby_fund_bp)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_baby_fund.py 2>&1 | tail -n 20`
Expected: 两个测试都 ✅ passed

- [ ] **Step 7: 提交**

```bash
git add src/routes/baby_fund.py src/templates/baby_fund.html src/main.py tests/test_baby_fund.py
git commit -m "feat(baby-fund): 宝宝基金管理（添加/编辑/删除+交易联动）"
```

---

## Task 4: 文件解析器 (importers.py)

**Files:**
- Create: `src/utils/importers.py`
- Create: `src/static/import_template.csv`
- Modify: `requirements.txt`
- Test: `tests/test_importers.py`

- [ ] **Step 1: 添加 openpyxl 依赖**

在 `requirements.txt` 末尾添加：
```
openpyxl==3.1.2
```

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && source venv/bin/activate && pip install openpyxl==3.1.2`

- [ ] **Step 2: 创建标准导入模板**

创建 `src/static/import_template.csv`:
```csv
日期,类型,金额,分类,描述
2026-03-01,支出,35.50,餐饮,午餐
2026-03-01,收入,50000.00,工资,3月工资
```

- [ ] **Step 3: 写文件解析器的失败测试**

创建 `tests/test_importers.py`:
```python
"""文件解析器测试"""
import sys
import os
import tempfile
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.importers import parse_template_csv, parse_wechat_csv, parse_alipay_csv, sanitize_cell


def test_sanitize_cell():
    """测试 CSV 注入防护"""
    assert sanitize_cell('=cmd|xxx') == "cmd|xxx"
    assert sanitize_cell('+cmd') == "cmd"
    assert sanitize_cell('-cmd') == "cmd"
    assert sanitize_cell('@cmd') == "cmd"
    assert sanitize_cell('正常文本') == '正常文本'
    assert sanitize_cell(None) == ''
    print("✅ test_sanitize_cell passed")


def test_parse_template_csv():
    """测试标准模板 CSV 解析"""
    # 创建临时 CSV
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    writer = csv.writer(tmp)
    writer.writerow(['日期', '类型', '金额', '分类', '描述'])
    writer.writerow(['2026-03-01', '支出', '35.50', '餐饮', '午餐'])
    writer.writerow(['2026-03-02', '收入', '50000', '工资', '3月工资'])
    tmp.close()

    result = parse_template_csv(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    assert result[0]['category_name'] == '餐饮'
    assert result[1]['type'] == 'income'
    print("✅ test_parse_template_csv passed")
    os.unlink(tmp.name)


def test_parse_wechat_csv():
    """测试微信账单 CSV 解析"""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    # 微信账单前 16 行是概要
    for i in range(16):
        tmp.write(f'概要行{i}\n')
    # 列名行
    tmp.write('交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n')
    # 数据行
    tmp.write('2026-03-01 12:00:00,商户消费,肯德基,午餐,支出,¥35.50,微信支付,支付成功,TX001,,\n')
    tmp.write('2026-03-02 09:00:00,转账,张三,,收入,¥1000.00,微信支付,已收钱,TX002,,\n')
    tmp.close()

    result = parse_wechat_csv(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    assert result[0]['order_no'] == 'TX001'
    assert result[1]['type'] == 'income'
    assert result[1]['amount'] == 1000.0
    print("✅ test_parse_wechat_csv passed")
    os.unlink(tmp.name)


def test_parse_alipay_csv():
    """测试支付宝账单 CSV 解析"""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    # 支付宝头部信息
    tmp.write('支付宝交易记录\n')
    tmp.write('账号:xxx\n')
    tmp.write('起始日期:2026-03-01\n')
    tmp.write('终止日期:2026-03-31\n')
    tmp.write('\n')
    # 列名行
    tmp.write('交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n')
    # 数据行
    tmp.write('2026-03-01 12:00:00,餐饮美食,饿了么,,午餐外卖,支出,25.00,花呗,交易成功,ALI001,,\n')
    tmp.close()

    result = parse_alipay_csv(tmp.name)
    assert len(result) == 1
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 25.0
    assert result[0]['order_no'] == 'ALI001'
    print("✅ test_parse_alipay_csv passed")
    os.unlink(tmp.name)


def test_parse_excel():
    """测试标准模板 Excel 解析"""
    import openpyxl
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['日期', '类型', '金额', '分类', '描述'])
    ws.append(['2026-03-01', '支出', 35.50, '餐饮', '午餐'])
    ws.append(['2026-03-02', '收入', 50000, '工资', '3月工资'])
    wb.save(tmp.name)

    from utils.importers import parse_excel
    result = parse_excel(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    print("✅ test_parse_excel passed")
    os.unlink(tmp.name)


def test_detect_source_type():
    """测试文件类型自动检测"""
    from utils.importers import detect_source_type

    # 微信账单特征：前几行有"微信支付账单"
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp.write('微信支付账单明细\n')
    for i in range(15):
        tmp.write(f'行{i}\n')
    tmp.write('交易时间,交易类型,交易对方\n')
    tmp.close()
    assert detect_source_type(tmp.name) == 'wechat'
    os.unlink(tmp.name)

    # 支付宝特征：有"支付宝"
    tmp2 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp2.write('支付宝交易记录\n')
    tmp2.close()
    assert detect_source_type(tmp2.name) == 'alipay'
    os.unlink(tmp2.name)

    # 标准模板
    tmp3 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp3.write('日期,类型,金额,分类,描述\n')
    tmp3.close()
    assert detect_source_type(tmp3.name) == 'template'
    os.unlink(tmp3.name)

    print("✅ test_detect_source_type passed")


def test_map_category():
    """测试分类映射逻辑"""
    from utils.importers import map_category

    # 模拟分类列表
    categories = [
        {'id': 1, 'name': '餐饮'},
        {'id': 2, 'name': '交通'},
        {'id': 3, 'name': '工资'},
    ]

    # 精确匹配
    assert map_category('餐饮', categories) == 1
    # 模糊匹配
    assert map_category('餐饮美食', categories) == 1
    assert map_category('交通出行', categories) == 2
    # 无法匹配
    assert map_category('娱乐休闲', categories) is None
    assert map_category(None, categories) is None
    print("✅ test_map_category passed")


if __name__ == '__main__':
    test_sanitize_cell()
    test_parse_template_csv()
    test_parse_wechat_csv()
    test_parse_alipay_csv()
    test_parse_excel()
    test_detect_source_type()
    test_map_category()
```

- [ ] **Step 4: 运行测试验证失败**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_importers.py 2>&1 | tail -n 20`
Expected: ModuleNotFoundError: No module named 'utils.importers'

- [ ] **Step 5: 实现文件解析器**

创建 `src/utils/__init__.py`（空文件，如不存在）和 `src/utils/importers.py`。

关键函数：
- `sanitize_cell(value)`: 去除 `=+\-@` 开头的内容，防 CSV 注入
- `parse_template_csv(filepath)`: 解析标准模板 CSV，返回 `[{date, type, amount, category_name, description}]`
- `parse_wechat_csv(filepath)`: 跳过前 16 行，解析微信格式，清洗 `¥` 符号，返回含 `order_no` 的记录列表
- `parse_alipay_csv(filepath)`: 检测列名行开始解析，返回含 `order_no` 的记录列表
- `parse_excel(filepath)`: 用 openpyxl 解析 .xlsx（按标准模板格式）
- `detect_source_type(filepath)`: 读取前几行，检测"微信"/"支付宝"/标准模板列名，返回 `'wechat'`/`'alipay'`/`'template'`
- `map_category(raw_name, categories)`: 分类映射，精确匹配优先，回退到模糊匹配（检查 raw_name 是否包含某分类名），返回 category_id 或 None

每个函数返回统一格式的字典列表：
```python
{
    'date': '2026-03-01',   # str
    'type': 'expense',      # 'income' or 'expense'
    'amount': 35.50,        # float
    'description': '午餐',  # str
    'category_name': '餐饮', # str or None
    'order_no': 'TX001',    # str or None（微信/支付宝有）
}
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_importers.py 2>&1 | tail -n 20`
Expected: 四个测试都 ✅ passed

- [ ] **Step 7: 提交**

```bash
git add src/utils/ src/static/import_template.csv requirements.txt tests/test_importers.py
git commit -m "feat(importers): 微信/支付宝/标准模板文件解析器"
```

---

## Task 5: 批量导入路由 + 模板

**Files:**
- Create: `src/routes/upload.py`
- Create: `src/templates/upload.html`
- Modify: `src/main.py`（注册蓝图 + MAX_CONTENT_LENGTH）
- Test: `tests/test_upload.py`

- [ ] **Step 1: 写批量导入路由的失败测试**

创建 `tests/test_upload.py`:
```python
"""批量导入路由测试"""
import sys
import os
import io
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import db, User, Category, Transaction, ImportRecord
from database import create_app


def _create_test_app():
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['TESTING'] = True
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
    return app, temp_db.name


def test_upload_parse_template():
    """测试上传和解析标准模板 CSV"""
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='importer', nickname='导入者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id

    # 构造 CSV 文件
    csv_content = '日期,类型,金额,分类,描述\n2026-03-01,支出,35.50,餐饮,午餐\n'
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'source_type': 'template'}

    resp = client.post('/upload/parse', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert len(json_data['records']) == 1
    assert json_data['records'][0]['amount'] == 35.50

    print("✅ test_upload_parse_template passed")
    os.unlink(db_path)


def test_upload_confirm():
    """测试确认导入"""
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='confirmer', nickname='确认者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        cat_id = cat.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id

    # 直接提交确认数据
    import json
    resp = client.post('/upload/confirm',
                       data=json.dumps({
                           'records': [
                               {'date': '2026-03-01', 'type': 'expense', 'amount': 35.50,
                                'description': '午餐', 'category_id': cat_id}
                           ],
                           'source_type': 'template',
                           'file_name': 'test.csv'
                       }),
                       content_type='application/json')
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data['imported_count'] == 1

    with app.app_context():
        assert Transaction.query.count() == 1
        assert ImportRecord.query.count() == 1

    print("✅ test_upload_confirm passed")
    os.unlink(db_path)


def test_upload_detect_duplicate():
    """测试去重检测"""
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='dedup', nickname='去重测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        # 预先插入一条交易（模拟已有数据）
        from datetime import date as dt_date
        existing = Transaction(
            user_id=user.id, amount=Decimal('35.50'), type='expense',
            category_id=cat.id, description='午餐 [单号:TX001]',
            transaction_date=dt_date(2026, 3, 1)
        )
        db.session.add(existing)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id

    # 上传含相同订单号的文件
    csv_content = '交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n'
    csv_content += '2026-03-01 12:00:00,商户消费,肯德基,午餐,支出,¥35.50,微信支付,支付成功,TX001,,\n'
    csv_content += '2026-03-03 12:00:00,商户消费,麦当劳,午餐,支出,¥28.00,微信支付,支付成功,TX003,,\n'

    # 加上微信账单头部
    header = '\n'.join([f'概要行{i}' for i in range(16)]) + '\n'
    full_csv = header + csv_content

    data = {'file': (io.BytesIO(full_csv.encode('utf-8')), 'wechat.csv'),
            'source_type': 'wechat'}
    resp = client.post('/upload/parse', data=data, content_type='multipart/form-data')
    json_data = resp.get_json()

    # 应标记 TX001 为重复
    duplicates = [r for r in json_data['records'] if r.get('is_duplicate')]
    assert len(duplicates) == 1
    assert duplicates[0]['order_no'] == 'TX001'

    print("✅ test_upload_detect_duplicate passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_upload_parse_template()
    test_upload_confirm()
    test_upload_detect_duplicate()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_upload.py 2>&1 | tail -n 20`

- [ ] **Step 3: 实现批量导入路由**

创建 `src/routes/upload.py`。关键路由：
- `GET /upload`: 渲染导入页面 + 导入历史
- `POST /upload/parse`: 接收文件，调用 importers 解析，做去重检测，返回 JSON 预览
- `POST /upload/confirm`: 接收最终记录列表，逐条创建 Transaction，创建 ImportRecord
- `GET /upload/template`: 返回标准模板文件下载

**订单号存储逻辑（confirm 路由中）：**
当记录有 `order_no` 时，将其追加到 description：
```python
desc = record.get('description', '') or ''
if record.get('order_no'):
    desc = f"{desc} [单号:{record['order_no']}]".strip()
```

**分类映射（parse 路由中）：**
调用 `map_category(record['category_name'], user_categories)` 获取 category_id，返回给前端预览。

去重检测逻辑在 parse 路由中：
1. 查询用户近 6 个月交易
2. 对有 order_no 的记录：检查 description 中是否已有 `[单号:xxx]`
3. 对无 order_no 的记录：用 date+amount+description 组合比对
4. 标记重复项（`is_duplicate=True`）返回前端

- [ ] **Step 4: 创建导入页面模板**

创建 `src/templates/upload.html`。关键要素：
- 三步流程指示器（JS 控制步骤切换）
- 步骤 1：拖拽上传区域 + 来源类型选择按钮 + 模板下载
- 步骤 2：预览表格 + 重复项高亮 + 操作按钮（全部前端 JS 实现）
- 步骤 3：导入结果展示
- 底部：导入历史列表

- [ ] **Step 5: 在 main.py 注册蓝图 + 添加文件大小限制**

```python
from routes.upload import upload_bp
app.register_blueprint(upload_bp)
```

在 `src/database.py` 的 `create_app` 函数中（第 37 行前）添加：
```python
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin && python tests/test_upload.py 2>&1 | tail -n 20`

- [ ] **Step 7: 提交**

```bash
git add src/routes/upload.py src/templates/upload.html src/main.py src/database.py tests/test_upload.py
git commit -m "feat(upload): 批量导入功能（解析+预览+去重+确认导入）"
```

---

## Task 6: 导航整合 + CSS 样式

**Files:**
- Modify: `src/templates/index.html:24-29`
- Modify: `src/templates/accounts.html:23-26`
- Modify: `src/templates/reports.html`
- Modify: `src/templates/categories.html`
- Modify: `src/static/css/style.css`

- [ ] **Step 1: 更新所有模板的 header nav**

在每个模板的 `<div class="user-actions">` 中，在现有链接之间插入三个新链接：

```html
<a href="{{ url_for('savings.savings_list', view=current_view) }}" class="nav-link">储蓄</a>
<a href="{{ url_for('baby_fund.baby_fund_list', view=current_view) }}" class="nav-link">宝宝</a>
<a href="{{ url_for('upload.upload_page') }}" class="nav-link">导入</a>
```

需要修改的文件（在 `账户` 链接之后、`家庭` 链接之前插入）：
- `src/templates/index.html`
- `src/templates/accounts.html`
- `src/templates/reports.html`
- `src/templates/categories.html`

**注意：** 新建的三个页面模板（savings.html, baby_fund.html, upload.html）中，当前页面的 nav-link 应添加 active 类以高亮当前位置。

- [ ] **Step 2: 追加 CSS 样式**

在 `src/static/css/style.css` 末尾追加：
- 储蓄卡片样式（`.savings-card`, `.progress-bar`, `.progress-fill`）
- 宝宝基金列表样式（`.fund-item`, `.fund-icon`, `.fund-amount`）
- 导入页样式（`.upload-zone`, `.step-indicator`, `.preview-table`, `.duplicate-row`）
- 进度条渐变色（与设计稿一致）

- [ ] **Step 3: 手动验证所有页面导航正常**

访问每个页面，确认导航链接完整且可点击跳转。

- [ ] **Step 4: 提交**

```bash
git add src/templates/ src/static/css/style.css
git commit -m "feat(nav): 所有页面导航添加储蓄/宝宝/导入链接 + Phase 3 样式"
```

---

## Task 7: 端到端验证 + 文档更新

**Files:**
- Modify: `PROJECT_BRIEF.md`
- Modify: `TASKS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 启动应用完整测试**

```bash
cd /Users/candyxiao/ClaudeCode/0225-FamilyFin
source venv/bin/activate
python src/main.py
```

访问 http://localhost:5001 依次验证：
1. 储蓄计划：创建月度计划 → 录入储蓄 → 查看进度条 → 删除
2. 宝宝基金：添加记录 → 确认首页出现收入交易 → 删除确认交易也删除
3. 批量导入：下载模板 → 填写数据 → 上传 → 预览 → 确认导入

- [ ] **Step 2: 运行全部测试**

```bash
python tests/test_savings.py && python tests/test_baby_fund.py && python tests/test_importers.py && python tests/test_upload.py
```

Expected: 全部 ✅ passed

- [ ] **Step 3: 更新 PROJECT_BRIEF.md**

更新"当前状态"和"下一步 5 件事"：
- 已可用能力中添加：储蓄计划管理、宝宝基金记录、CSV/Excel 批量导入
- 下一步调整为 Phase 4 内容

- [ ] **Step 4: 更新 TASKS.md**

添加 Phase 3 任务记录（TASK-007 ~ TASK-009），全部标记 DONE

- [ ] **Step 5: 更新 CLAUDE.md**

在功能实现记录中添加 Phase 3 的实现记录

- [ ] **Step 6: 提交**

```bash
git add PROJECT_BRIEF.md TASKS.md CLAUDE.md
git commit -m "docs: 更新项目文档，标记 Phase 3 完成"
```
