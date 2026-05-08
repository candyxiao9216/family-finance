# FamilyFin 项目架构分析

## 1. 数据模型结构 (src/models.py)

### 核心财务模型

#### Account（账户）三分类架构
```python
class AccountType(db.Model):
    """账户类型表 - 定义储蓄/基金/股票等账户类型"""
    name = db.Column(db.String(50), unique=True)
    category = db.Column(db.String(20))  # 'savings' / 'fund' / 'stock'
    is_default = db.Column(db.Boolean)
    accounts = db.relationship('Account', backref='account_type')

DEFAULT_ACCOUNT_TYPES = [
    {'name': '银行', 'category': 'savings'},
    {'name': '微众', 'category': 'fund'},
    {'name': '富途', 'category': 'stock'},
    # ... 等
]
```

#### Account（账户主体）
```python
class Account(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(100))
    type_id = db.Column(db.Integer, db.ForeignKey('account_types.id'))
    currency = db.Column(db.String(3), default='CNY')  # CNY/HKD/USD
    initial_balance = db.Column(db.Numeric(10, 2), default=0)
    current_balance = db.Column(db.Numeric(10, 2), default=0)
    balance_records = db.relationship('AccountBalance', ...)  # 月度快照
    
    def to_dict(self):
        return {
            'category': self.account_type.category,  # 三分类属性
            'type_name': self.account_type.name,
            'current_balance': float(self.current_balance),
        }
```

#### AccountBalance（月度余额快照）
```python
class AccountBalance(db.Model):
    """账户余额月度快照 - 记录每月账户余额变化"""
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    balance = db.Column(db.Numeric(10, 2))  # 当月余额
    change_amount = db.Column(db.Numeric(10, 2))  # 月度变化额
    record_month = db.Column(db.Date)  # 如 2024-03-01
    note = db.Column(db.String(200))  # 本月备注
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'record_month'),  # 每账户每月唯一
    )
```

#### Transaction（交易）
```python
class Transaction(db.Model):
    amount = db.Column(db.Numeric(10, 2))
    type = db.Column(db.String(10))  # 'income' 或 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    description = db.Column(db.Text)
    transaction_date = db.Column(db.Date)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))  # 关联账户
    
    # 修改追踪
    last_modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_modified_at = db.Column(db.DateTime)
    modification_count = db.Column(db.Integer, default=0)
    last_modifier = db.relationship('User', foreign_keys=[last_modified_by])
    
    def to_dict(self):
        return {
            'category_name': self.category.name,
            'account_id': self.account_id,  # 可追踪关联账户
            'modification_count': self.modification_count,
        }
```

#### TransactionModification（修改审计）
```python
class TransactionModification(db.Model):
    """交易修改记录表 - 记录每次交易修改的详细信息"""
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    field_name = db.Column(db.String(50))  # '金额', '分类', '日期' 等
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### StockHolding（股票持仓）
```python
class StockHolding(db.Model):
    """股票持仓 - 记录个股买入信息"""
    stock_code = db.Column(db.String(20))  # 00700, 600519, AAPL
    stock_name = db.Column(db.String(100))
    market = db.Column(db.String(10))  # HK / A / US
    shares = db.Column(db.Float)  # 股数
    avg_cost = db.Column(db.Float)  # 摊薄成本
    currency = db.Column(db.String(3), default='HKD')
```

#### FundHolding（基金持仓）
```python
class FundHolding(db.Model):
    """基金持仓 - 记录基金份额和收益"""
    fund_code = db.Column(db.String(30))
    fund_name = db.Column(db.String(100))
    fund_type = db.Column(db.String(30))  # 指数型/混合型/QDII/债券型/货币型
    shares = db.Column(db.Float)  # 份额
    amount = db.Column(db.Float)  # 持有金额
    profit = db.Column(db.Float)  # 收益
    profit_rate = db.Column(db.String(20))  # 收益率
    status = db.Column(db.String(20), default='holding')  # holding/redeemed
```

#### WealthHolding（理财产品）
```python
class WealthHolding(db.Model):
    """理财产品 - 记录理财产品持仓"""
    product_name = db.Column(db.String(200))
    manager = db.Column(db.String(100))  # 管理机构
    buy_amount = db.Column(db.Float)
    current_amount = db.Column(db.Float)
    annual_rate = db.Column(db.Float)  # 年化收益率
    product_type = db.Column(db.String(20))  # fixed/flexible/closed
```

#### AI 缓存与历史
```python
class AiAdviceCache(db.Model):
    """AI建议短期缓存（1小时TTL）"""
    advice_key = db.Column(db.String(100), unique=True)
    advice_text = db.Column(db.Text)
    model_used = db.Column(db.String(50))
    generated_at = db.Column(db.DateTime)

class AiAdviceHistory(db.Model):
    """AI建议永久历史记录"""
    advice_type = db.Column(db.String(30))  # comprehensive/stocks/funds/wealth/savings
    advice_text = db.Column(db.Text)
    model_used = db.Column(db.String(50))
    generated_at = db.Column(db.DateTime)
```

#### StockHolding（股票持仓）
```python
class StockHolding(db.Model):
    """股票持仓 - 记录个股买入信息"""
    stock_code = db.Column(db.String(20))  # 00700, 600519, AAPL
    stock_name = db.Column(db.String(100))
    market = db.Column(db.String(10))  # HK / A / US
    shares = db.Column(db.Float)  # 股数
    avg_cost = db.Column(db.Float)  # 摊薄成本
    currency = db.Column(db.String(3), default='HKD')
```

#### FundHolding（基金持仓）
```python
class FundHolding(db.Model):
    """基金持仓 - 记录基金份额和收益"""
    fund_code = db.Column(db.String(30))
    fund_name = db.Column(db.String(100))
    fund_type = db.Column(db.String(30))  # 指数型/混合型/QDII/债券型/货币型
    shares = db.Column(db.Float)  # 份额
    amount = db.Column(db.Float)  # 持有金额
    profit = db.Column(db.Float)  # 收益
    profit_rate = db.Column(db.String(20))  # 收益率
    status = db.Column(db.String(20), default='holding')  # holding/redeemed
```

#### WealthHolding（理财产品）
```python
class WealthHolding(db.Model):
    """理财产品 - 记录理财产品持仓"""
    product_name = db.Column(db.String(200))
    manager = db.Column(db.String(100))  # 管理机构
    buy_amount = db.Column(db.Float)
    current_amount = db.Column(db.Float)
    annual_rate = db.Column(db.Float)  # 年化收益率
    product_type = db.Column(db.String(20))  # fixed/flexible/closed
```

#### AI 缓存与历史
```python
class AiAdviceCache(db.Model):
    """AI建议短期缓存（1小时TTL）"""
    advice_key = db.Column(db.String(100), unique=True)
    advice_text = db.Column(db.Text)
    model_used = db.Column(db.String(50))
    generated_at = db.Column(db.DateTime)

class AiAdviceHistory(db.Model):
    """AI建议永久历史记录"""
    advice_type = db.Column(db.String(30))  # comprehensive/stocks/funds/wealth/savings
    advice_text = db.Column(db.Text)
    model_used = db.Column(db.String(50))
    generated_at = db.Column(db.DateTime)
```

### 其他主要模型

#### User（用户）& Family（家庭）
- User.family_id → Foreign Key to Family
- Family 支持邀请码机制
- User 支持 role（成员、管理员等）

#### Category（分类）
- 系统预设分类（is_default=True）
- 用户自定义分类（user_id != NULL）
- 支持收入/支出两种类型

#### SavingsPlan & SavingsRecord（储蓄计划）
```python
class SavingsPlan:
    type = 'monthly' | 'annual'  # 月度/年度计划
    target_amount = Numeric(10,2)
    records = relationship('SavingsRecord')  # 多笔储蓄记录

class SavingsRecord:
    plan_id → SavingsPlan
    user_id → User
    amount = Numeric(10,2)
    account_id → Account
    record_date = Date
```

#### MonthlyTodo（月度待办）
```python
class MonthlyTodo:
    user_id, year, month  # 确定月份范围
    category = 'transaction' | 'snapshot' | 'savings' | 'baby_fund'
    title, description
    is_required = Boolean  # 是否必选项
    priority = Integer  # 1-5
    status = 'pending' | 'completed'
    auto_detected = Boolean  # 是否自动检测
    action_url = String  # 引导链接
    __table_args__ = (UniqueConstraint('user_id', 'year', 'month', 'title'),)
```

---

## 2. 蓝图注册标准模式 (src/main.py)

### 蓝图创建与注册

```python
# 1. 在各路由模块中创建蓝图
# src/routes/auth.py
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# src/routes/account.py
account_bp = Blueprint('account', __name__, url_prefix='/accounts')

# src/routes/transaction.py
transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

# 2. 在 main.py 中注册所有蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(account_bp)
app.register_blueprint(category_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(savings_bp)
app.register_blueprint(baby_fund_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(template_bp)
app.register_blueprint(recurring_bp)
app.register_blueprint(monthly_todo_bp)
```

### 蓝图内路由定义规范

```python
# 列表视图：获取 view 参数以支持个人/家庭视图切换
@blueprint_bp.route('/')
def list():
    current_view = request.args.get('view', 'personal')
    if current_view == 'family' and family:
        # 查询家庭成员数据
        member_ids = [m.id for m in family.members]
        records = Model.query.filter(Model.user_id.in_(member_ids)).all()
    else:
        # 查询个人数据
        records = Model.query.filter_by(user_id=user_id).all()

# 表单提交：统一使用 redirect() 返回到列表视图
@blueprint_bp.route('/add', methods=['POST'])
def add():
    # ... 处理表单数据 ...
    return redirect(url_for('blueprint.list'))

# 删除操作：通过 POST 方法（避免 GET 删除）
@blueprint_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    # ... 删除逻辑 ...
    return redirect(url_for('blueprint.list'))
```

### 辅助函数模式

```python
# 在 route 模块中定义通用函数，供多个 route 使用

# src/routes/savings.py
def _get_family_member_ids(user_id, current_view):
    """获取当前视图下的用户 ID 列表"""
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        return [m.id for m in user.family.members]
    return [user_id]

# src/routes/account.py
def _get_family_accounts(user_id, current_view):
    """获取当前视图下的所有账户"""
    user = User.query.get(user_id)
    if current_view == 'family' and user and user.family:
        family_member_ids = [m.id for m in user.family.members]
        return Account.query.filter(Account.user_id.in_(family_member_ids)).all()
    return Account.query.filter_by(user_id=user_id).all()

def _get_exchange_rates():
    """获取汇率（模拟）"""
    return {'CNY': 1.0, 'HKD': 0.128, 'USD': 6.5}
```

---

## 3. 导航栏结构 (src/templates/base.html)

### 桌面端导航

```html
<!-- 桌面端导航栏 -->
<header class="header desktop-nav">
    <div class="header-main">
        <h1>家庭财务</h1>
        <p id="current-date"></p>
    </div>
    <div class="user-info">
        <span class="username">{{ username }}</span>
        <div class="user-actions">
            <!-- 主导航链接 -->
            <a href="{{ url_for('index') }}" class="nav-link">首页</a>
            <a href="{{ url_for('transaction.transaction_list') }}" class="nav-link">月度收支</a>
            <a href="{{ url_for('account.account_list') }}" class="nav-link">资产总览</a>
            <a href="{{ url_for('savings.savings_list') }}" class="nav-link">储蓄计划</a>
            
            <!-- 下拉菜单：管理功能 -->
            <div class="nav-dropdown">
                <a href="#" class="nav-link nav-dropdown-trigger">管理 ▾</a>
                <div class="nav-dropdown-menu">
                    <a href="{{ url_for('baby_fund.baby_fund_list') }}" class="nav-dropdown-item">宝宝基金</a>
                    <a href="{{ url_for('category.category_list') }}" class="nav-dropdown-item">分类管理</a>
                    <a href="{{ url_for('template.template_list') }}" class="nav-dropdown-item">快捷模板</a>
                    <a href="{{ url_for('recurring.recurring_list') }}" class="nav-dropdown-item">定期交易</a>
                    <a href="{{ url_for('upload.upload_page') }}" class="nav-dropdown-item">批量导入</a>
                    <a href="{{ url_for('reports.reports_page', view=current_view) }}" class="nav-dropdown-item">报表</a>
                    {% if family %}
                    <a href="{{ url_for('family.family_info') }}" class="nav-dropdown-item">家庭</a>
                    {% endif %}
                </div>
            </div>
            
            <a href="{{ url_for('auth.logout') }}" class="logout-btn">退出</a>
        </div>
    </div>
</header>
```

### 移动端导航

```html
<!-- 移动端头部 -->
<header class="mobile-header">
    <div class="mobile-header-left">
        <span class="mobile-logo">💰</span>
        <h1>{% block mobile_title %}家庭财务{% endblock %}</h1>
    </div>
    <button class="hamburger-btn" id="hamburger-btn" aria-label="打开菜单">
        <span></span><span></span><span></span>
    </button>
</header>

<!-- 侧滑菜单 -->
<nav class="side-menu" id="side-menu">
    <div class="side-menu-header">
        <span class="side-menu-user">{{ username }}</span>
        <button class="side-menu-close" id="side-menu-close">&times;</button>
    </div>
    <div class="side-menu-items">
        <a href="{{ url_for('index') }}" class="side-menu-item">🏠 首页</a>
        <a href="{{ url_for('transaction.transaction_list') }}" class="side-menu-item">💵 月度收支</a>
        <div class="side-menu-divider"></div>
        <a href="{{ url_for('account.account_list') }}" class="side-menu-item">💳 资产总览</a>
        <a href="{{ url_for('savings.savings_list') }}" class="side-menu-item">🎯 储蓄计划</a>
        <div class="side-menu-divider"></div>
        <a href="{{ url_for('baby_fund.baby_fund_list') }}" class="side-menu-item">👶 宝宝基金</a>
        <a href="{{ url_for('category.category_list') }}" class="side-menu-item">🏷️ 分类管理</a>
        <!-- ... 更多菜单项 ... -->
    </div>
</nav>
```

### 导航项清单
| 链接 | URL | 蓝图 |
|------|-----|------|
| 首页 | `/` | 无 |
| 月度收支 | `/transactions/` | transaction_bp |
| 资产总览 | `/accounts/` | account_bp |
| 储蓄计划 | `/savings/` | savings_bp |
| 宝宝基金 | `/baby-fund/` | baby_fund_bp |
| 分类管理 | `/categories/` | category_bp |
| 快捷模板 | `/templates/` | template_bp |
| 定期交易 | `/recurring/` | recurring_bp |
| 批量导入 | `/upload/` | upload_bp |
| 报表 | `/reports/` | reports_bp |
| 家庭 | `/family/` | family_bp |

### 智能财务顾问路由 (src/routes/advisor.py)
- `GET /advisor/` — 总览仪表盘（资产配置饼图 + 各板块摘要）
- `GET /advisor/stocks` — 股票分析（持仓 + 实时行情 + AI分析）
- `GET /advisor/funds` — 基金分析（持仓 + 排序 + 赎回转投）
- `GET /advisor/wealth` — 理财分析
- `GET /advisor/savings` — 储蓄建议
- `GET /advisor/history` — AI分析历史
- `POST /advisor/api/stocks` — 股票持仓CRUD
- `POST /advisor/api/funds` — 基金持仓CRUD
- `POST /advisor/api/wealth` — 理财持仓CRUD
- `GET /advisor/api/ai/comprehensive` — AI综合分析
- `GET /advisor/api/ai/stocks-overall` — 股票整体分析
- `GET /advisor/api/ai/stock/<id>` — 个股分析
- `GET /advisor/api/ai/funds-overall` — 基金整体分析
- `GET /advisor/api/ai/fund/<id>` — 个基分析
- `GET /advisor/api/ai/wealth` — 理财分析
- `GET /advisor/api/ai/savings` — 储蓄建议

---

## 4. 全局样式系统 (src/static/css/style.css)

### CSS 变量定义

```css
:root {
    /* === 配色方案 === */
    /* 背景 */
    --color-bg: #F9F7F4;              /* 页面背景 */
    --color-bg-card: #FFFFFF;         /* 卡片背景 */
    
    /* 文本 */
    --color-text-primary: #2D2A2E;    /* 标题/主文本 */
    --color-text-secondary: #6B6B6B;  /* 副文本 */
    --color-text-muted: #9A9A9A;      /* 灰色文本 */
    
    /* 收入 - 温暖琥珀金 */
    --color-income: #D4A574;
    --color-income-light: #F5E6D3;
    --color-income-bg: rgba(212, 165, 116, 0.15);
    
    /* 支出 - 舒适靛蓝 */
    --color-expense: #7C8BA1;
    --color-expense-light: #E8ECF1;
    --color-expense-bg: rgba(124, 139, 161, 0.15);
    
    /* 强调色 - 温暖珊瑚橙 */
    --color-accent: #E8998D;
    --color-accent-hover: #D7877B;
    
    /* 分隔线 */
    --color-border: #E8E4E0;
    --color-border-light: #F0EDE9;
    
    /* === 阴影 - 柔和多层 === */
    --shadow-soft: 0 4px 20px rgba(45, 42, 46, 0.04);
    --shadow-card: 0 2px 12px rgba(45, 42, 46, 0.06);
    --shadow-hover: 0 8px 30px rgba(45, 42, 46, 0.1);
    
    /* === 间距系统 === */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
    
    /* === 圆角 === */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
    --radius-full: 9999px;
    
    /* === 过渡 === */
    --transition-fast: 0.15s ease;
    --transition-normal: 0.25s ease;
    --transition-slow: 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

### 关键类定义

```css
/* 卡片 */
.card {
    background: var(--color-bg-card);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-soft);
    padding: var(--space-xl);
    border: 1px solid var(--color-border-light);
    transition: var(--transition-normal);
}

.card:hover {
    box-shadow: var(--shadow-hover);
}

/* 表单 */
.form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--space-md);
}

.form-group {
    display: flex;
    flex-direction: column;
}

.form-group label {
    font-weight: 500;
    margin-bottom: var(--space-sm);
    color: var(--color-text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
    padding: var(--space-sm) var(--space-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-family: inherit;
    transition: var(--transition-fast);
}

/* 按钮 */
.btn {
    padding: var(--space-sm) var(--space-lg);
    border-radius: var(--radius-md);
    border: none;
    cursor: pointer;
    font-weight: 500;
    transition: var(--transition-fast);
}

.btn-primary {
    background: var(--color-accent);
    color: white;
}

.btn-primary:hover {
    background: var(--color-accent-hover);
}

.btn-secondary {
    background: var(--color-border-light);
    color: var(--color-text-primary);
}

/* 统计卡片 */
.stat-card {
    background: linear-gradient(135deg, var(--color-bg-card), var(--color-border-light));
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-primary);
}

.stat-label {
    font-size: 14px;
    color: var(--color-text-secondary);
}

/* 收入/支出标记 */
.income-tag {
    background: var(--color-income-bg);
    color: var(--color-income);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--radius-sm);
}

.expense-tag {
    background: var(--color-expense-bg);
    color: var(--color-expense);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--radius-sm);
}
```

### 响应式设计断点

```css
/* 移动端优先 */
/* 平板 */
@media (min-width: 768px) {
    .container {
        max-width: 900px;
    }
}

/* 桌面端 */
@media (min-width: 1024px) {
    .container {
        max-width: 1200px;
    }
    
    .desktop-nav {
        display: flex;
    }
    
    .mobile-header {
        display: none;
    }
}
```

---

## 5. 依赖项 (requirements.txt)

```
flask==3.0.0                    # Web 框架
flask-sqlalchemy==3.1.1         # ORM
python-dotenv==1.0.0            # 环境变量
python-dateutil==2.8.2          # 日期处理
openpyxl==3.1.2                 # Excel 导出
```

---

## 6. 项目目录结构

```
src/
├── main.py                      # 主应用入口，蓝图注册
├── models.py                    # 所有数据模型
├── database.py                  # 数据库初始化
├── config.py                    # 配置文件
├── routes/
│   ├── auth.py                  # 认证路由
│   ├── account.py               # 账户管理
│   ├── transaction.py           # 交易记录
│   ├── category.py              # 分类管理
│   ├── savings.py               # 储蓄计划
│   ├── baby_fund.py             # 宝宝基金
│   ├── family.py                # 家庭功能
│   ├── reports.py               # 报表
│   ├── upload.py                # 批量导入
│   ├── template.py              # 快捷模板
│   ├── recurring.py             # 定期交易
│   └── monthly_todo.py          # 月度待办
├── templates/
│   ├── base.html                # 基础模板（导航、布局）
│   ├── index.html               # 首页
│   ├── accounts.html            # 资产总览页
│   ├── transactions.html        # 月度收支页
│   ├── savings.html             # 储蓄计划页
│   ├── categories.html          # 分类管理页
│   └── ... (其他页面模板)
└── static/
    ├── css/
    │   └── style.css            # 全局样式
    └── js/
        └── ... (前端脚本)
```

---

## 7. 核心工作流模式

### 添加新数据的标准流程

1. **定义模型** (models.py)
   ```python
   class NewModel(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       # ... 字段定义 ...
       def to_dict(self):
           return {# ... 转换逻辑 ...}
   ```

2. **创建蓝图** (routes/new_feature.py)
   ```python
   new_bp = Blueprint('new_feature', __name__, url_prefix='/new-feature')
   
   @new_bp.route('/')
   def list():
       # 处理视图切换、查询、分页
   
   @new_bp.route('/add', methods=['POST'])
   def add():
       # 验证、创建、重定向
   ```

3. **注册蓝图** (main.py)
   ```python
   from routes.new_feature import new_bp
   app.register_blueprint(new_bp)
   ```

4. **添加导航入口** (templates/base.html)
   ```html
   <a href="{{ url_for('new_feature.list') }}" class="nav-link">新功能</a>
   ```

5. **创建模板** (templates/new_feature.html)
   ```html
   {% extends "base.html" %}
   {% block content %}
       <!-- 页面内容 -->
   {% endblock %}
   ```

### 修改追踪模式
```python
# 编辑交易时，记录所有修改
modifications = []
for field, (old_val, new_val) in field_changes.items():
    if old_val != new_val:
        mod = TransactionModification(
            transaction_id=transaction.id,
            modified_by=user_id,
            field_name=field,
            old_value=old_val,
            new_value=new_val
        )
        modifications.append(mod)

# 批量添加并提交
for mod in modifications:
    db.session.add(mod)
db.session.commit()
```

### 家庭视图切换模式
```python
# 获取视图参数
current_view = request.args.get('view', 'personal')

# 根据视图类型确定查询范围
if current_view == 'family' and family:
    member_ids = [m.id for m in family.members]
    records = Model.query.filter(Model.user_id.in_(member_ids)).all()
else:
    records = Model.query.filter_by(user_id=user_id).all()
```

---

## 总结：添加新功能的 5 步框架

| 步骤 | 文件 | 关键点 |
|------|------|-------|
| 1. 模型 | models.py | 定义字段、关系、to_dict() |
| 2. 蓝图 | routes/xx.py | 创建 blueprint，添加路由 |
| 3. 注册 | main.py | app.register_blueprint() |
| 4. 导航 | templates/base.html | 添加菜单项 |
| 5. 模板 | templates/xx.html | 继承 base.html，实现页面 |

