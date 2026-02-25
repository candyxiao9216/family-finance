# 家庭财务管理系统 MVP 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建家庭财务管理的最小可用产品，实现交易录入、列表展示、删除功能和基础统计。

**Architecture:** Flask + SQLAlchemy + SQLite 的简单三层架构，无用户认证，单页面应用。

**Tech Stack:**
- Flask 3.0.0 - Web 框架
- Flask-SQLAlchemy 3.1.1 - ORM
- SQLite 3 - 数据库
- Python 3.8+

---

## Task 1: 创建项目基础文件

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `data/.gitkeep`

**Step 1: 创建 requirements.txt**

创建 `requirements.txt` 文件，包含项目依赖：

```txt
flask==3.0.0
flask-sqlalchemy==3.1.1
python-dotenv==1.0.0
```

**Step 2: 创建 .gitignore**

创建 `.gitignore` 文件：

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
env/
ENV/

# 数据库
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp

# 系统文件
.DS_Store
Thumbs.db
```

**Step 3: 创建 data 目录占位符**

创建 `data/.gitkeep` 文件（空文件即可），确保 data 目录被 git 跟踪。

**Step 4: 提交**

```bash
git add requirements.txt .gitignore data/.gitkeep
git commit -m "chore: 添加项目基础配置文件"
```

---

## Task 2: 数据库配置文件

**Files:**
- Create: `src/config.py`

**Step 1: 创建配置文件**

创建 `src/config.py`：

```python
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库配置
DATABASE_PATH = DATA_DIR / "family_finance.db"
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 应用配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
```

**Step 2: 提交**

```bash
git add src/config.py
git commit -m "feat: 添加数据库配置"
```

---

## Task 3: 数据模型定义

**Files:**
- Create: `src/models.py`
- Test: (本 MVP 跳过单元测试，留待后续迭代)

**Step 1: 创建数据模型**

创建 `src/models.py`：

```python
from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 数据关联：交易与分类
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def category_name(self):
        return self.category.name if self.category else None

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount),
            'type': self.type,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'description': self.description,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 预设分类
DEFAULT_CATEGORIES = [
    {'name': '工资', 'type': 'income'},
    {'name': '奖金', 'type': 'income'},
    {'name': '餐饮', 'type': 'expense'},
    {'name': '交通', 'type': 'expense'},
]
```

**Step 2: 提交**

```bash
git add src/models.py
git commit -m "feat: 定义 Category 和 Transaction 数据模型"
```

---

## Task 4: 数据库初始化

**Files:**
- Create: `src/database.py`

**Step 1: 创建数据库初始化模块**

创建 `src/database.py`：

```python
from flask import Flask
from src.models import db, Category, DEFAULT_CATEGORIES
from src.config import BASE_DIR, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS


def init_database(app: Flask) -> None:
    """初始化数据库表和预设分类"""
    with app.app_context():
        # 创建所有表
        db.create_all()

        # 插入预设分类（仅当不存在时）
        for cat_data in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(name=cat_data['name']).first()
            if not existing:
                category = Category(**cat_data)
                db.session.add(category)

        db.session.commit()
        print(f"数据库初始化完成: {SQLALCHEMY_DATABASE_URI}")
        print(f"预设分类: {len(DEFAULT_CATEGORIES)} 个")


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # 初始化数据库
    db.init_app(app)

    # 静态文件和模板目录
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    return app
```

**Step 2: 提交**

```bash
git add src/database.py
git commit -m "feat: 实现数据库初始化模块"
```

---

## Task 5: Flask 应用路由

**Files:**
- Create: `src/main.py`

**Step 1: 创建主应用文件**

创建 `src/main.py`：

```python
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func, extract

from src.database import create_app, init_database
from src.models import db, Transaction, Category

app = create_app()


@app.route('/init-db')
def init_db_route():
    """初始化数据库（开发用路由）"""
    init_database(app)
    return "数据库初始化成功！<a href='/'>返回首页</a>"


@app.route('/')
def index():
    """首页 - 交易列表"""
    # 获取所有交易，按日期降序
    transactions = Transaction.query.order_by(Transaction.transaction_date.desc()).all()

    # 计算本月统计
    current_month = date.today().month
    current_year = date.today().year

    month_stats = db.session.query(
        func.sum(
            func.case(
                ((Transaction.type == 'income') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year)), Transaction.amount, else_=0
            )
        ).label('income'),
        func.sum(
            func.case(
                ((Transaction.type == 'expense') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year)), Transaction.amount, else_=0
            )
        ).label('expense')
    ).first()

    monthly_income = month_stats.income or Decimal('0')
    monthly_expense = month_stats.expense or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    return render_template('index.html',
                          transactions=transactions,
                          monthly_income=float(monthly_income),
                          monthly_expense=float(monthly_expense),
                          monthly_balance=float(monthly_balance))


@app.route('/add', methods=['POST'])
def add_transaction():
    """添加交易"""
    transaction_type = request.form.get('type')
    amount = request.form.get('amount')
    category_id = request.form.get('category')
    transaction_date_str = request.form.get('date')
    description = request.form.get('description')

    # 基本验证
    if not all([transaction_type, amount, category_id, transaction_date_str]):
        return "缺少必填字段", 400

    try:
        transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
    except ValueError:
        return "日期格式错误", 400

    # 创建交易记录
    transaction = Transaction(
        amount=Decimal(amount),
        type=transaction_type,
        category_id=int(category_id),
        description=description or None,
        transaction_date=transaction_date
    )

    db.session.add(transaction)
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    """删除交易"""
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for('index'))


if __name__ == '__main__':
    # 首次运行时初始化数据库
    init_database(app)
    app.run(host='0.0.0.0', port=5000, debug=True)
```

**Step 2: 验证数据库查询逻辑**

检查 SQLAlchemy 函数导入是否正确：
- `func.case` - 条件聚合
- `extract` - 提取日期部分

**Step 3: 提交**

```bash
git add src/main.py
git commit -m "feat: 实现核心路由（首页、添加、删除）"
```

---

## Task 6: 更新前端模板

**Files:**
- Modify: `src/templates/index.html`

**Step 1: 更新日期显示脚本**

更新 `setCurrentDate` 函数，确保日期显示正确：

```javascript
function setCurrentDate() {
    const now = new Date();
    const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('zh-CN', options);
}
```

**Step 2: 测试分类联动逻辑**

确保切换收入/支出类型时，分类选择框正确更新：

```javascript
// 更新统计数据（从后端传入的变量渲染）
document.getElementById('stat-income').textContent = formatCurrency({{ monthly_income }});
document.getElementById('stat-expense').textContent = formatCurrency({{ monthly_expense }});
document.getElementById('stat-balance').textContent = formatCurrency({{ monthly_balance }});
```

**Step 3: 移除前端统计计算逻辑**

删除前端 JavaScript 中的 `updateStats` 函数，因为统计现在由后端计算：

删除以下代码块：
```javascript
// 删除这些行
function updateStats() { ... }
```

**Step 4: 在初始化时设置统计值**

在 script 标签末尾添加：

```javascript
// 设置统计值（后端传入）
document.getElementById('stat-income').textContent = formatCurrency({{ monthly_income }});
document.getElementById('stat-expense').textContent = formatCurrency({{ monthly_expense }});
document.getElementById('stat-balance').textContent = formatCurrency({{ monthly_balance }});

// 初始化
setCurrentDate();
setDefaultDate();
updateCategories('expense');
```

**Step 5: 提交**

```bash
git add src/templates/index.html
git commit -m "fix: 更新前端模板适配后端逻辑"
```

---

## Task 7: 本地测试

**Files:**
- None (测试验证)

**Step 1: 安装依赖**

```bash
pip install -r requirements.txt
```

**Step 2: 运行应用**

```bash
python src/main.py
```

**期望输出:**
```
数据库初始化完成: sqlite:////path/to/data/family_finance.db
预设分类: 4 个
 * Running on http://0.0.0.0:5000
```

**Step 3: 手动验证功能**

访问 `http://localhost:5000`，验证以下功能：

1. 首页正常加载，显示空交易列表
2. 添加一条收入交易（工资 15000），列表显示该记录
3. 添加一条支出交易（餐饮 50），列表按日期排序
4. 统计栏显示正确的收入/支出/结余
5. 点击删除按钮，交易被移除
6. 移动端视图响应式正常

**Step 4: 提交（测试通过）**

```bash
git add -A
git commit -m "test: MVP 第一阶段功能验证通过"
```

---

## Task 8: 创建用户文档

**Files:**
- Create: `README.md`

**Step 1: 创建 README.md**

创建 `README.md`：

```markdown
# 家庭财务管理系统

一个简洁、温暖的家庭财务管理工具。

## 功能

- 记录收入和支出
- 按分类管理交易
- 月度收支统计
- 简洁优雅的界面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python src/main.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:5000

## 技术栈

- Flask 3.0.0
- SQLAlchemy 2.x
- SQLite 3

## 项目结构

```
0225-FamilyFinance/
├── src/                    # 源代码
│   ├── main.py            # 应用入口
│   ├── models.py          # 数据模型
│   ├── database.py        # 数据库配置
│   └── config.py          # 配置文件
├── data/                  # 数据库文件
├── docs/                  # 设计文档
└── preview.html           # 静态预览
```

## 开发

### 初始化数据库

应用首次运行时会自动初始化数据库和预设分类。

手动初始化可访问: http://localhost:5000/init-db

### 预设分类

**收入：** 工资、奖金
**支出：** 餐饮、交通

## 许可

MIT License
```

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 添加用户文档"
```

---

## Task 9: 标签发布

**Files:**
- None (git tag)

**Step 1: 创建版本标签**

```bash
git tag -a v1.0.0-alpha -m "MVP 第一阶段发布
- 交易录入功能
- 交易列表展示
- 删除交易功能
- 月度收支统计"
```

**Step 2: 查看标签**

```bash
git tag -l
```

**Step 3: 提交（如有新增）**

```bash
git add -A
git commit -m "chore: 完成 MVP 第一阶段发布"
```

---

## 完成 Checklist

执行完所有任务后，验证以下内容：

- [x] requirements.txt 创建并提交
- [x] .gitignore 创建并提交
- [x] config.py 数据库配置完成
- [x] models.py 数据模型定义完成
- [x] database.py 初始化模块完成
- [x] main.py 核心路由实现完成
- [x] index.html 模板更新为后端渲染
- [x] 本地测试通过
- [x] README.md 用户文档创建
- [x] Git tag v1.0.0-alpha 创建

---

## 运行命令快速参考

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py

# 访问应用
open http://localhost:5000

# 查看数据库文件
sqlite3 data/family_finance.db
```

---

**计划创建日期：** 2026-02-26
**预计完成时间：** 约 1-2 小时
