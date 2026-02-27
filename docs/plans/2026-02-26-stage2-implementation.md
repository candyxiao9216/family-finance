# 家庭财务管理系统 第二阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现用户认证和自定义分类管理，支持多用户独立使用系统。

**新增功能:**
- 用户注册与登录
- 会话管理
- 自定义分类的增删改查
- 交易记录与用户关联

**技术变更:**
- 新增 User 数据模型
- 修改 Transaction 和 Category 模型添加 user_id 字段
- 添加认证路由和分类管理路由
- 实现数据迁移脚本

---

## Task 1: 更新数据模型

**Files:**
- Modify: `src/models.py`

**Step 1: 添加 User 模型**

```python
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
```

**Step 2: 修改 Transaction 模型**

```python
# 在 Transaction 类中添加 user_id 字段
user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
```

**Step 3: 修改 Category 模型**

```python
# 在 Category 类中添加 user_id 和 is_default 字段
user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
is_default = db.Column(db.Boolean, default=False)
```

**Step 4: 提交**

```bash
git add src/models.py
git commit -m "feat: 添加 User 模型，更新 Transaction 和 Category 模型"
```

---

## Task 2: 创建数据迁移脚本

**Files:**
- Create: `src/migration_v2.py`

**Step 1: 创建迁移脚本**

```python
from src.database import create_app
from src.models import db, User, Category, Transaction
from werkzeug.security import generate_password_hash

def migrate_to_v2():
    """第二阶段数据迁移：添加用户关联"""
    app = create_app()

    with app.app_context():
        # 创建 users 表
        db.create_all()

        # 创建默认用户（admin）
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("创建默认用户: admin/admin123")

        # 为现有分类添加 user_id = NULL（系统预设）
        categories = Category.query.all()
        for category in categories:
            if category.user_id is None:
                category.user_id = None  # 标记为系统预设
                category.is_default = True

        # 为现有交易关联默认用户
        transactions = Transaction.query.all()
        for transaction in transactions:
            if transaction.user_id is None:
                transaction.user_id = admin_user.id

        db.session.commit()
        print(f"迁移完成: {len(categories)} 个分类, {len(transactions)} 条交易")

if __name__ == '__main__':
    migrate_to_v2()
```

**Step 2: 提交**

```bash
git add src/migration_v2.py
git commit -m "feat: 创建第二阶段数据迁移脚本"
```

---

## Task 3: 更新数据库初始化模块

**Files:**
- Modify: `src/database.py`

**Step 1: 更新初始化逻辑**

```python
def init_database(app: Flask) -> None:
    """初始化数据库表和预设分类"""
    with app.app_context():
        # 创建所有表
        db.create_all()

        # 插入预设分类（仅当不存在时）
        for cat_data in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(name=cat_data['name']).first()
            if not existing:
                category = Category(**cat_data, user_id=None, is_default=True)
                db.session.add(category)

        db.session.commit()
        print(f"数据库初始化完成: {SQLALCHEMY_DATABASE_URI}")
        print(f"预设分类: {len(DEFAULT_CATEGORIES)} 个")
```

**Step 2: 提交**

```bash
git add src/database.py
git commit -m "feat: 更新数据库初始化逻辑支持用户关联"
```

---

## Task 4: 实现认证路由

**Files:**
- Create: `src/routes/auth.py`

**Step 1: 创建认证路由模块**

```python
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from src.models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('auth/register.html')

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在')
            return render_template('auth/register.html')

        # 创建新用户
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # 自动登录
        session['user_id'] = user.id
        session['username'] = user.username

        return redirect(url_for('index'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('auth/login.html')

        # 验证用户
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
            return render_template('auth/login.html')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """用户登出"""
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('auth.login'))
```

**Step 2: 提交**

```bash
git add src/routes/auth.py
git commit -m "feat: 实现用户认证路由"
```

---

## Task 5: 实现分类管理路由

**Files:**
- Create: `src/routes/categories.py`

**Step 1: 创建分类管理路由模块**

```python
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from src.models import db, Category

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')

@categories_bp.route('/')
def list_categories():
    """分类列表页面"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取当前用户可用的分类（系统预设 + 用户自定义）
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == session['user_id'])
    ).order_by(Category.user_id.desc(), Category.name).all()

    return render_template('categories/list.html', categories=categories)

@categories_bp.route('/add', methods=['POST'])
def add_category():
    """添加分类"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    name = request.form.get('name')
    category_type = request.form.get('type')

    if not name or not category_type:
        flash('分类名称和类型不能为空')
        return redirect(url_for('categories.list_categories'))

    # 检查是否已存在同名分类
    existing = Category.query.filter_by(name=name, user_id=session['user_id']).first()
    if existing:
        flash('分类名称已存在')
        return redirect(url_for('categories.list_categories'))

    # 创建分类
    category = Category(
        name=name,
        type=category_type,
        user_id=session['user_id'],
        is_default=False
    )
    db.session.add(category)
    db.session.commit()

    flash('分类添加成功')
    return redirect(url_for('categories.list_categories'))

@categories_bp.route('/edit/<int:category_id>', methods=['POST'])
def edit_category(category_id):
    """编辑分类"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    category = Category.query.get_or_404(category_id)

    # 只能编辑自己的分类
    if category.user_id != session['user_id']:
        flash('无权编辑此分类')
        return redirect(url_for('categories.list_categories'))

    name = request.form.get('name')
    if not name:
        flash('分类名称不能为空')
        return redirect(url_for('categories.list_categories'))

    category.name = name
    db.session.commit()

    flash('分类更新成功')
    return redirect(url_for('categories.list_categories'))

@categories_bp.route('/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    """删除分类"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    category = Category.query.get_or_404(category_id)

    # 系统预设分类不可删除
    if category.user_id is None:
        flash('系统预设分类不可删除')
        return redirect(url_for('categories.list_categories'))

    # 只能删除自己的分类
    if category.user_id != session['user_id']:
        flash('无权删除此分类')
        return redirect(url_for('categories.list_categories'))

    # 检查是否有关联交易
    if category.transactions:
        flash('该分类下有关联交易，无法删除')
        return redirect(url_for('categories.list_categories'))

    db.session.delete(category)
    db.session.commit()

    flash('分类删除成功')
    return redirect(url_for('categories.list_categories'))
```

**Step 2: 提交**

```bash
git add src/routes/categories.py
git commit -m "feat: 实现分类管理路由"
```

---

## Task 6: 更新主应用路由

**Files:**
- Modify: `src/main.py`

**Step 1: 更新主应用添加认证和分类路由**

```python
# 导入新增的路由模块
from src.routes.auth import auth_bp
from src.routes.categories import categories_bp

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(categories_bp)

# 添加登录检查装饰器
@app.before_request
def require_login():
    """登录状态检查"""
    allowed_routes = ['auth.login', 'auth.register', 'static']
    if request.endpoint and request.endpoint not in allowed_routes:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

# 更新首页路由，只显示当前用户的交易
@app.route('/')
def index():
    """首页 - 交易列表"""
    # 获取当前用户的交易，按日期降序
    transactions = Transaction.query.filter_by(
        user_id=session.get('user_id')
    ).order_by(Transaction.transaction_date.desc()).all()

    # 获取当前用户可用的分类
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == session.get('user_id'))
    ).all()

    # 计算本月统计（仅当前用户）
    # ... 现有统计逻辑，添加 user_id 过滤 ...

    return render_template('index.html',
                          transactions=transactions,
                          categories=categories,
                          username=session.get('username'))

# 更新添加交易路由，关联当前用户
@app.route('/add', methods=['POST'])
def add_transaction():
    """添加交易"""
    # ... 现有逻辑 ...

    # 创建交易记录时关联当前用户
    transaction = Transaction(
        amount=Decimal(amount),
        type=transaction_type,
        category_id=int(category_id),
        description=description or None,
        transaction_date=transaction_date,
        user_id=session.get('user_id')  # 新增
    )

    # ... 现有逻辑 ...

# 更新删除交易路由，只能删除自己的交易
@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    """删除交易"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # 只能删除自己的交易
    if transaction.user_id != session.get('user_id'):
        return "无权删除此交易", 403

    # ... 现有逻辑 ...
```

**Step 2: 提交**

```bash
git add src/main.py
git commit -m "feat: 更新主应用路由支持用户认证和分类管理"
```

---

## Task 7: 创建认证页面模板

**Files:**
- Create: `src/templates/auth/login.html`
- Create: `src/templates/auth/register.html`

**Step 1: 创建登录页面模板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - 家庭财务管理</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <h1>家庭财务管理</h1>

            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for message in messages %}
                            <div class="flash-message">{{ message }}</div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}

            <form method="POST" class="auth-form">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>

                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <button type="submit" class="btn-primary">登录</button>
            </form>

            <div class="auth-links">
                <a href="{{ url_for('auth.register') }}">没有账号？立即注册</a>
            </div>
        </div>
    </div>
</body>
</html>
```

**Step 2: 创建注册页面模板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - 家庭财务管理</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <h1>用户注册</h1>

            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for message in messages %}
                            <div class="flash-message">{{ message }}</div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}

            <form method="POST" class="auth-form">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>

                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <button type="submit" class="btn-primary">注册</button>
            </form>

            <div class="auth-links">
                <a href="{{ url_for('auth.login') }}">已有账号？立即登录</a>
            </div>
        </div>
    </div>
</body>
</html>
```

**Step 3: 提交**

```bash
git add src/templates/auth/
git commit -m "feat: 创建认证页面模板"
```

---

## Task 8: 创建分类管理页面模板

**Files:**
- Create: `src/templates/categories/list.html`

**Step 1: 创建分类列表页面模板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>分类管理 - 家庭财务管理</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>分类管理</h1>
            <div class="header-actions">
                <span class="username">{{ username }}</span>
                <a href="{{ url_for('index') }}" class="btn-secondary">返回首页</a>
                <a href="{{ url_for('auth.logout') }}" class="btn-secondary">退出</a>
            </div>
        </header>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="flash-messages">
                    {% for message in messages %}
                        <div class="flash-message">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <section class="add-category-section">
            <h2>添加分类</h2>
            <form method="POST" action="{{ url_for('categories.add_category') }}" class="category-form">
                <div class="form-row">
                    <input type="text" name="name" placeholder="分类名称" required>
                    <select name="type" required>
                        <option value="">选择类型</option>
                        <option value="income">收入</option>
                        <option value="expense">支出</option>
                    </select>
                    <button type="submit" class="btn-primary">添加</button>
                </div>
            </form>
        </section>

        <section class="categories-section">
            <h2>我的分类</h2>
            <div class="categories-list">
                {% for category in categories %}
                    <div class="category-item">
                        <div class="category-info">
                            <span class="category-name">{{ category.name }}</span>
                            <span class="category-type {{ category.type }}">{{ '收入' if category.type == 'income' else '支出' }}</span>
                            {% if category.user_id is None %}
                                <span class="system-badge">系统预设</span>
                            {% endif %}
                        </div>

                        {% if category.user_id is not None %}
                            <div class="category-actions">
                                <form method="POST" action="{{ url_for('categories.edit_category', category_id=category.id) }}" class="inline-form">
                                    <input type="text" name="name" value="{{ category.name }}" required>
                                    <button type="submit" class="btn-small">更新</button>
                                </form>

                                <form method="POST" action="{{ url_for('categories.delete_category', category_id=category.id) }}" class="inline-form">
                                    <button type="submit" class="btn-small btn-danger" onclick="return confirm('确定删除此分类？')">删除</button>
                                </form>
                            </div>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
        </section>
    </div>
</body>
</html>
```

**Step 2: 提交**

```bash
git add src/templates/categories/
git commit -m "feat: 创建分类管理页面模板"
```

---

## Task 9: 更新首页模板

**Files:**
- Modify: `src/templates/index.html`

**Step 1: 更新首页添加用户信息和导航**

```html
<!-- 在 header 部分添加用户信息 -->
<header class="header">
    <h1>家庭财务</h1>
    <div class="header-actions">
        <span class="username">{{ username }}</span>
        <a href="{{ url_for('categories.list_categories') }}" class="btn-secondary">分类管理</a>
        <a href="{{ url_for('auth.logout') }}" class="btn-secondary">退出</a>
    </div>
</header>

<!-- 更新分类选择框，使用用户可用的分类 -->
<select id="category" name="category" required>
    <option value="">选择分类</option>
    {% for category in categories %}
        {% if category.type == 'expense' %}
            <option value="{{ category.id }}">{{ category.name }}</option>
        {% endif %}
    {% endfor %}
</select>
```

**Step 2: 提交**

```bash
git add src/templates/index.html
git commit -m "feat: 更新首页模板支持用户认证和分类管理"
```

---

## Task 10: 更新样式文件

**Files:**
- Modify: `src/static/css/style.css`

**Step 1: 添加认证和分类管理相关样式**

```css
/* 认证页面样式 */
.auth-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: #F9F7F4;
}

.auth-card {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    width: 100%;
    max-width: 400px;
}

.auth-form .form-group {
    margin-bottom: 1rem;
}

.auth-links {
    margin-top: 1rem;
    text-align: center;
}

/* 分类管理样式 */
.category-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #eee;
}

.category-info {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.category-type.income {
    color: #D4A574;
}

.category-type.expense {
    color: #7C8BA1;
}

.system-badge {
    background: #E8998D;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
}

.category-actions {
    display: flex;
    gap: 0.5rem;
}

.inline-form {
    display: inline;
}

.btn-small {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
}

.btn-danger {
    background: #E8998D;
}

.btn-danger:hover {
    background: #D47C6F;
}

/* 闪存消息样式 */
.flash-messages {
    margin-bottom: 1rem;
}

.flash-message {
    padding: 0.75rem;
    border-radius: 6px;
    background: #E8998D;
    color: white;
    margin-bottom: 0.5rem;
}
```

**Step 2: 提交**

```bash
git add src/static/css/style.css
git commit -m "feat: 更新样式文件支持认证和分类管理界面"
```

---

## Task 11: 执行数据迁移

**Files:**
- Execute: `src/migration_v2.py`

**Step 1: 运行迁移脚本**

```bash
python src/migration_v2.py
```

**期望输出:**
```
创建默认用户: admin/admin123
迁移完成: 4 个分类, X 条交易
```

**Step 2: 提交**

```bash
git add -A
git commit -m "feat: 执行第二阶段数据迁移"
```

---

## Task 12: 本地测试

**Files:**
- None (测试验证)

**Step 1: 运行应用**

```bash
python src/main.py
```

**Step 2: 验证功能**

访问 `http://localhost:5001`，验证以下功能：

1. **认证功能**
   - [ ] 未登录访问首页重定向到登录页
   - [ ] 可以注册新用户
   - [ ] 可以用注册的用户名和密码登录
   - [ ] 登录后 session 正确设置
   - [ ] 可以正常登出

2. **分类管理功能**
   - [ ] 可以查看所有可用的分类（系统预设 + 自定义）
   - [ ] 可以添加自定义分类
   - [ ] 可以编辑自定义分类的名称
   - [ ] 可以删除自定义分类
   - [ ] 系统预设分类不可删除
   - [ ] 添加交易时可以选择自定义分类

3. **数据隔离**
   - [ ] 用户只能看到自己的交易记录
   - [ ] 用户只能看到自己的自定义分类
   - [ ] 系统预设分类对所有用户可见

**Step 3: 提交（测试通过）**

```bash
git add -A
git commit -m "test: 第二阶段功能验证通过"
```

---

## Task 13: 创建版本标签

**Files:**
- None (git tag)

**Step 1: 创建版本标签**

```bash
git tag -a v1.0.0-beta -m "MVP 第二阶段发布
- 用户认证功能
- 自定义分类管理
- 数据隔离和权限控制"
```

**Step 2: 查看标签**

```bash
git tag -l
```

**Step 3: 提交**

```bash
git add -A
git commit -m "chore: 完成 MVP 第二阶段发布"
```

---

## 完成 Checklist

执行完所有任务后，验证以下内容：

- [x] User 模型已创建
- [x] Transaction 和 Category 模型已更新
- [x] 数据迁移脚本已创建和执行
- [x] 认证路由已实现
- [x] 分类管理路由已实现
- [x] 主应用路由已更新
- [x] 认证页面模板已创建
- [x] 分类管理页面模板已创建
- [x] 首页模板已更新
- [x] 样式文件已更新
- [x] 本地测试通过
- [x] Git tag v1.0.0-beta 创建

---

## 运行命令快速参考

```bash
# 运行数据迁移
python src/migration_v2.py

# 运行应用
python src/main.py

# 访问应用
open http://localhost:5001

# 测试用户
用户名: admin
密码: admin123
```

---

**计划创建日期：** 2026-02-26
**预计完成时间：** 约 2-3 小时