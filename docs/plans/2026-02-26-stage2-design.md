# 家庭财务管理系统 第二阶段设计文档

**创建日期:** 2026-02-26
**版本:** 1.0.0
**状态:** 设计中

---

## 1. 概述

### 1.1 目标
实现用户认证和自定义分类管理，支持多用户独立使用系统。

### 1.2 新增功能
- 用户注册与登录
- 会话管理
- 自定义分类的增删改查
- 交易记录与用户关联

### 1.3 安全考虑
- 密码使用 werkzeug.security 生成哈希
- 使用 Flask session 管理登录状态
- SECRET_KEY 使用环境变量

---

## 2. 数据库设计变更

### 2.1 新增 users 表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 修改 transactions 表

```sql
ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id);
```

### 2.3 修改 categories 表

```sql
ALTER TABLE categories ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE categories ADD COLUMN is_default INTEGER DEFAULT 0;
```

**说明：**
- `user_id` 为 NULL 表示系统预设分类（所有用户可见）
- `user_id` 不为 NULL 表示用户自定义分类（仅该用户可见）

---

## 3. API 路由设计

### 3.1 认证路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/auth/register` | GET/POST | 用户注册页面/处理注册 |
| `/auth/login` | GET/POST | 用户登录页面/处理登录 |
| `/auth/logout` | POST | 用户登出 |

### 3.2 分类管理路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/categories` | GET | 分类列表页面 |
| `/categories/add` | POST | 添加分类 |
| `/categories/edit/<id>` | POST | 编辑分类 |
| `/categories/delete/<id>` | POST | 删除分类 |

### 3.3 修改现有路由

| 路由 | 变更 |
|------|------|
| `/` | 需要用户登录才能访问，只显示当前用户的交易 |
| `/add` | 新增交易时关联当前用户 |
| `/delete/<id>` | 只能删除当前用户的交易 |

---

## 4. 前端设计

### 4.1 登录页面

```
┌─────────────────────────────┐
│      家庭财务管理          │
│                             │
│    ┌───────────────────┐   │
│    │  用户名 [______]  │   │
│    │  密码   [______]  │   │
│    │                   │   │
│    │    [登录] [注册]  │   │
│    └───────────────────┘   │
└─────────────────────────────┘
```

### 4.2 分类管理页面

```
┌─────────────────────────────────────┐
│  分类管理            [返回首页]    │
├─────────────────────────────────────┤
│  添加分类                            │
│  ┌─────────────────────────────┐    │
│  │ 名称 [______]              │    │
│  │ 类型 [收入/支出]           │    │
│  │        [添加]               │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  我的分类                            │
│  ┌─────────────────────────────┐    │
│  │ 餐饮 [编辑] [删除]          │    │
│  │ 交通 [编辑] [删除]          │    │
│  │ 工资 (系统预设)             │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### 4.3 首页新增登出按钮

在头部添加用户信息和登出按钮：
```
┌─────────────────────────────────────┐
│  家庭财务          [用户名] [退出] │
└─────────────────────────────────────┘
```

---

## 5. 核心逻辑

### 5.1 用户注册
1. 检查用户名是否已存在
2. 使用 `generate_password_hash` 生成密码哈希
3. 创建用户记录
4. 自动登录新用户
5. 重定向到首页

### 5.2 用户登录
1. 根据用户名查询用户
2. 使用 `check_password_hash` 验证密码
3. 设置 session['user_id']
4. 重定向到首页

### 5.3 权限检查
```python
# 使用装饰器保护需要登录的路由
@app.before_request
def require_login():
    allowed_routes = ['login', 'register']
    if request.endpoint and request.endpoint not in allowed_routes:
        if 'user_id' not in session:
            return redirect(url_for('login'))
```

### 5.4 分类查询逻辑
```python
# 获取当前用户可用的分类（系统预设 + 用户自定义）
categories = Category.query.filter(
    (Category.user_id == None) | (Category.user_id == current_user.id)
).all()
```

### 5.5 删除分类逻辑
- 系统预设分类（user_id = NULL）不可删除
- 自定义分类删除前检查是否有关联交易，有的话不允许删除或同时更新交易为未分类

---

## 6. 数据迁移

需要创建数据库迁移脚本来处理现有数据：

### migration_v2.py
```python
def migrate_to_v2():
    # 添加 users 表
    # 添加 user_id 列到 transactions 和 categories
    # 为现有数据创建默认用户（用户名: admin, 密码: admin123）
    # 更新现有记录的 user_id 为默认用户 ID
    # 添加 is_default 列到 categories
```

---

## 7. 依赖清单更新

```
flask==3.0.0
flask-sqlalchemy==3.1.1
python-dotenv==1.0.0
werkzeug==3.x  # 用于密码哈希（Flask 自带）
```

---

## 8. 验收标准

### 用户认证
- [ ] 可以注册新用户
- [ ] 可以用注册的用户名和密码登录
- [ ] 登录后 session 正确设置
- [ ] 未登录访问首页会重定向到登录页
- [ ] 可以正常登出

### 分类管理
- [ ] 可以查看所有可用的分类（系统预设 + 自定义）
- [ ] 可以添加自定义分类
- [ ] 可以编辑自定义分类的名称
- [ ] 可以删除自定义分类
- [ ] 系统预设分类不可删除
- [ ] 添加交易时可以选择自定义分类

### 数据隔离
- [ ] 用户只能看到自己的交易记录
- [ ] 用户只能看到自己的自定义分类
- [ ] 系统预设分类对所有用户可见

---

## 9. 实施任务清单

1. 创建用户模型 User
2. 修改 Transaction 模型添加 user_id 字段
3. 修改 Category 模型添加 user_id 和 is_default 字段
4. 创建数据库迁移脚本
5. 实现注册路由和模板
6. 实现登录路由和模板
7. 实现登出功能
8. 添加登录状态检查装饰器
9. 修改首页路由添加用户过滤
10. 实现分类列表页面
11. 实现添加分类功能
12. 实现编辑分类功能
13. 实现删除分类功能
14. 更新首页添加用户信息和登出按钮
15. 更新添加交易表单加载用户可用分类

---

**文档状态:** 设计中，等待实施
