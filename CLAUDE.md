# CLAUDE.md - 家庭财务管理系统

## 项目概述

**项目名称:** 0225-FamilyFinance
**项目类型:** 个人财务管理 Web 应用
**状态:** 设计完成，待开发 (v1.0.0)
**创建日期:** 2026-02-25

## 项目目标

构建一个智能家庭财务管理工具，帮助用户：
- 自动追踪收入和支出，支持多银行账户同步
- 追踪账户余额变化（储蓄账户：银行、微众、中金；投资账户：富途、中银国际）
- 创建和跟踪储蓄计划（月度/年度目标）
- 记录宝宝基金（谁给的、金额、哪个账户）
- 记录贷款记录（房贷）
- 生成多维度数据可视化报表

## 技术栈

| 组件 | 技术选择 |
|------|---------|
| 后端框架 | Python Flask |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 前端样式 | Tailwind CSS |
| 数据可视化 | Chart.js |
| 文件处理 | CSV/Excel 导入导出 |

## 核心业务逻辑

### 1. 交易分类
- 支持自定义分类，初始为空
- 分类有两种类型：`income` (收入) 和 `expense` (支出)
- 每个分类由类型标签区分

### 2. 账户月度变化计算
```
月度变化 = 当前月余额 - 上个月余额
```

### 3. 储蓄进度计算
```
储蓄进度 = 当前已储蓄金额 / 年度储蓄目标 × 100%
```

### 4. 重复导入处理
- 通过 `import_id` 字段检测重复（基于 source + date + amount 生成哈希）
- 检测到重复后，让用户手动选择：
  - 保留原记录，跳过新记录
  - 覆盖原记录
  - 保留两条记录

### 5. 权限隔离
- MVP 阶段：多账号之间不需要权限隔离
- 所有用户可以看到所有数据
- 记录通过 `user_id` 标识归属，用于后续数据分析

## 数据库设计

### 表结构 (10 张表)

#### 1. users - 用户表
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,        -- 登录用户名
    password_hash TEXT NOT NULL,          -- 密码哈希
    nickname TEXT,                        -- 显示昵称
    role TEXT DEFAULT 'member',           -- 角色
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. categories - 交易分类表
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,            -- 分类名称
    type TEXT NOT NULL,                   -- 'income' 或 'expense'
    is_default BOOLEAN DEFAULT 0,         -- 是否默认分类
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. transactions - 交易记录表
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount DECIMAL(10,2) NOT NULL,        -- 交易金额
    type TEXT NOT NULL,                   -- 'income' 或 'expense'
    category_id INTEGER REFERENCES categories(id),
    description TEXT,                     -- 交易描述
    source TEXT DEFAULT 'manual',         -- 'manual' 或 'import'
    import_source TEXT,                   -- 导入来源标识
    import_id TEXT,                       -- 用于去重的唯一标识
    transaction_date DATE NOT NULL,       -- 交易日期
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. account_types - 账户类型表
```sql
CREATE TABLE account_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,            -- 账户类型名称
    category TEXT                         -- 'savings' (储蓄) 或 'investment' (投资)
);
```
**预设类型：**
- 储蓄类：银行、微众、中金
- 投资类：富途、中银国际

#### 5. accounts - 账户表
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,                   -- 账户名称
    type_id INTEGER REFERENCES account_types(id),
    initial_balance DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. account_balance - 账户余额历史表
```sql
CREATE TABLE account_balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    balance DECIMAL(10,2) NOT NULL,       -- 当前月余额
    change_amount DECIMAL(10,2),          -- 月度变化量
    record_month DATE NOT NULL,           -- 记录年月（YYYY-MM-01）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, record_month),     -- 每个账户每月只能有一条记录
    change_type TEXT                      -- 'increase' 或 'decrease'
);
```

#### 7. savings_plans - 储蓄计划表
```sql
CREATE TABLE savings_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                   -- 计划名称
    type TEXT NOT NULL,                   -- 'monthly' 或 'annual'
    target_amount DECIMAL(10,2) NOT NULL, -- 目标金额
    year INTEGER NOT NULL,                -- 年份
    month INTEGER,                        -- 月份（月度计划需要）
    account_id INTEGER REFERENCES accounts(id),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**预设计划：**
- 月度：用户 50k, 配偶 35k
- 年度：奖金储蓄

#### 8. savings_records - 储蓄记录表
```sql
CREATE TABLE savings_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES savings_plans(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount DECIMAL(10,2) NOT NULL,        -- 储蓄金额
    account_id INTEGER REFERENCES accounts(id),
    record_date DATE NOT NULL,            -- 储蓄日期
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 9. baby_funds - 宝宝基金表
```sql
CREATE TABLE baby_funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giver_name TEXT NOT NULL,             -- 给钱的人
    amount DECIMAL(10,2) NOT NULL,        -- 金额
    account_id INTEGER REFERENCES accounts(id),
    event_date DATE NOT NULL,             -- 日期
    event_type TEXT,                      -- 事件类型（满月、生日等）
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 10. import_records - 导入记录表
```sql
CREATE TABLE import_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    file_name TEXT NOT NULL,
    import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_rows INTEGER,
    imported_count INTEGER,
    skipped_count INTEGER,
    status TEXT DEFAULT 'completed'
);
```

## 系统架构

### 目录结构
```
src/
├── main.py                # Flask 应用入口
├── config.py              # 配置管理
├── database.py            # 数据库连接和初始化
├── models/                # SQLAlchemy 模型
│   ├── user.py
│   ├── transaction.py
│   ├── account.py
│   ├── savings.py
│   └── baby_fund.py
├── routes/                # 路由层
│   ├── auth.py            # 认证路由
│   ├── transaction.py     # 交易路由
│   ├── account.py         # 账户路由
│   ├── savings.py         # 储蓄路由
│   ├── baby_fund.py       # 宝宝基金路由
│   └── upload.py          # 文件上传路由
├── services/              # 业务逻辑层
│   ├── transaction_service.py
│   ├── account_service.py
│   ├── savings_service.py
│   ├── dashboard_service.py
│   └── import_service.py
├── utils/                 # 工具函数
│   ├── auth.py            # 密码哈希、JWT
│   ├── deduplication.py   # 去重逻辑
│   └── validators.py      # 数据验证
└── templates/             # HTML 模板
    ├── layout.html
    ├── dashboard.html
    ├── transactions.html
    ├── accounts.html
    └── ...
```

### API 路由设计

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/transactions` | GET/POST | 获取/创建交易 |
| `/api/transactions/<id>` | PUT/DELETE | 更新/删除交易 |
| `/api/accounts` | GET/POST | 获取/创建账户 |
| `/api/accounts/<id>/balance` | POST | 记录账户余额 |
| `/api/savings/plans` | GET/POST | 获取/创建储蓄计划 |
| `/api/savings/records` | GET/POST | 获取/创建储蓄记录 |
| `/api/baby-funds` | GET/POST | 获取/创建宝宝基金记录 |
| `/api/upload` | POST | CSV/Excel 导入 |
| `/api/dashboard/stats` | GET | 获取仪表盘统计数据 |

## 数据可视化需求

### 1. 趋势图
- 消费趋势：按月/季度/年度
- 收入趋势：按月/季度/年度

### 2. 构成图
- 收入构成（按分类）
- 支出构成（按分类）

### 3. 对比图
- 个人 vs 配偶的总支出对比
- 个人 vs 配偶的总收入对比

### 4. 资产曲线
- 现金资产变化曲线
- 股票资产变化曲线
- 总资产变化曲线

## MVP 范围

第一阶段（MVP）包含以下功能：
- ✅ 收入/支出记录录入
- ✅ 账户资产管理
- ✅ 储蓄计划追踪
- ✅ 宝宝基金记录
- ✅ 基础数据可视化
- ✅ CSV/Excel 批量导入

**暂不包含：**
- ❌ 银行流水自动同步
- ❌ 贷款管理模块
- ❌ 用户权限隔离

## 开发环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install flask sqlalchemy pandas openpyxl cryptography

# 运行应用
python src/main.py
```

## 部署方案

### 本地开发
- SQLite 数据库
- Flask 开发服务器
- 端口：5000

### 云部署
- PostgreSQL 数据库
- Gunicorn/Nginx
- Docker 容器化部署

## 功能实现记录

### 2026-02-27: User-Family 关联功能 ✅

**实现内容:**
- 在 User 模型中添加 `family_id` 外键字段（nullable=True，支持向后兼容）
- 建立 User-Family 一对多关系映射
- 增强 `to_dict()` 方法包含家庭信息
- 编写完整的测试用例验证关联功能

**技术细节:**
- User 模型：`family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=True)`
- Family 模型：`members = db.relationship('User', backref='family', lazy=True)`
- User.to_dict() 新增：`'family_name': self.family.name if self.family else None`
- Family.to_dict() 新增：`'member_count': len(self.members) if self.members else 0`

**测试验证:**
- ✅ 用户与家庭关联创建
- ✅ 家庭访问成员功能
- ✅ to_dict() 方法包含家庭信息
- ✅ 向后兼容性（用户可无家庭关联）
- ✅ 多用户关联同一家庭
- ✅ 家庭字典包含成员数量

**业务价值:**
- 为家庭级别的财务数据聚合提供基础
- 支持家庭成员间的协作功能
- 为后续权限管理奠定数据基础

## 经验教训

### 2026-02-27: User-Family 关联实现经验

**问题:** 测试过程中出现 invite_code 唯一约束冲突

**原因:** 临时数据库文件可能被重复使用，导致 invite_code 重复

**解决方案:**
- 使用随机生成的 invite_code 避免冲突
- 确保每次测试使用全新的临时数据库
- 测试完成后及时清理临时文件

**经验总结:**
- 测试环境隔离是保证测试可靠性的关键
- 唯一约束字段在测试中需要使用随机值
- TDD 流程有助于发现潜在的设计问题

---

**最后更新:** 2026-02-27
**文档版本:** 1.1.0
