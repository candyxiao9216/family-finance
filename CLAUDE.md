# CLAUDE.md - 家庭财务管理系统

## 项目概述

**项目名称:** 0225-FamilyFinance
**项目类型:** 个人财务管理 Web 应用
**状态:** 🎉 里程碑一完成 (v2.0.0) — 家庭资产数据数字化
**创建日期:** 2026-02-25

## 项目目标

构建一个智能家庭财务管理工具，帮助用户：
- 自动追踪收入和支出，支持多银行账户同步
- 追踪账户余额变化（储蓄账户：银行；基金理财：微众、中金、招行理财、招行基金、微众基金、富途基金；股票账户：富途、中银国际）
- 创建和跟踪储蓄计划（月度/年度目标）
- 记录宝宝基金（谁给的、金额、哪个账户）
- 记录贷款记录（房贷）
- 生成多维度数据可视化报表

## 技术栈

| 组件 | 技术选择 |
|------|---------|
| 后端框架 | Python Flask |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 前端样式 | 原生 CSS（CSS 变量 + 媒体查询） |
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
    category TEXT                         -- 'savings' (储蓄), 'fund' (基金理财) 或 'stock' (股票)
);
```
**预设类型：**
- 储蓄类(savings)：银行
- 基金理财类(fund)：微众、中金、招行基金、微众基金、富途基金、招行理财
- 股票类(stock)：富途、中银国际

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
├── main.py                # Flask 应用入口（仪表盘首页 + 交易增删改）
├── models.py              # 所有数据模型（12 个）
├── database.py            # 数据库连接和初始化
├── routes/                # 路由层（Flask 蓝图）
│   ├── auth.py            # 认证路由
│   ├── account.py         # 账户路由
│   ├── category.py        # 分类路由
│   ├── savings.py         # 储蓄路由
│   ├── baby_fund.py       # 宝宝基金路由
│   ├── upload.py          # 文件上传路由
│   ├── family.py          # 家庭路由
│   ├── transaction.py     # 月度收支路由（记账表单+交易列表）
│   ├── template.py        # 快捷模板路由
│   └── recurring.py       # 定期交易路由
├── utils/                 # 工具函数
│   └── importers.py       # CSV/Excel 解析
├── static/
│   ├── css/style.css      # 全局样式（含移动端响应式）
│   └── js/app.js          # 公共交互 JS（菜单、Toast、小眼睛隐藏）
└── templates/             # HTML 模板（Jinja2 继承）
    ├── base.html          # 公共模板（导航、Tab、Toast、确认弹窗）
    ├── auth_base.html     # 认证页公共模板
    ├── index.html         # 首页（三模块仪表盘）
    ├── transactions.html  # 月度收支（记账表单+交易列表+分页）
    ├── accounts.html      # 资产总览
    ├── reports.html       # 数据报表
    ├── categories.html    # 分类管理
    ├── savings.html       # 储蓄计划
    ├── baby_fund.html     # 宝宝基金
    ├── upload.html        # 批量导入
    ├── edit_transaction.html
    ├── quick_templates.html # 快捷模板管理
    ├── recurring.html     # 定期交易管理
    ├── auth/              # 登录/注册
    └── family/            # 家庭信息/成员
```

### API 路由设计

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页仪表盘（三模块概览） |
| `/transactions` | GET | 月度收支页（记账表单+交易列表+分页） |
| `/add` | POST | 添加交易 |
| `/edit/<id>` | GET/POST | 编辑交易 |
| `/delete/<id>` | POST | 删除交易 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/accounts` | GET | 资产总览 |
| `/accounts/<id>/balance` | POST | 记录账户余额 |
| `/savings` | GET | 储蓄计划 |
| `/savings/records` | GET/POST | 储蓄记录 |
| `/baby-funds` | GET/POST | 宝宝基金 |
| `/upload` | GET/POST | CSV/Excel 导入 |
| `/reports` | GET | 数据报表 |
| `/reports/api/trend` | GET | 趋势图数据 API |

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
- ✅ 账户资产管理（三分类：储蓄/基金理财/股票）
- ✅ 储蓄计划追踪
- ✅ 宝宝基金记录
- ✅ 基础数据可视化
- ✅ CSV/Excel 批量导入
- ✅ 移动端适配（底部 Tab + 汉堡菜单）
- ✅ 交互优化（Toast、确认弹窗、空状态、loading）
- ✅ 月度待办 Checklist（自动检测 + 手动打钩 + 聚焦气泡引导）

**暂不包含：**
- ❌ 银行流水自动同步
- ❌ 贷款管理模块
- ❌ 用户权限隔离
- ❌ 暗色模式

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
- SQLite 数据库
- Gunicorn + Nginx 反向代理
- systemd 服务管理
- 端口：5001（Gunicorn）→ 80（Nginx）

## 功能实现记录

### 2026-04-06: Phase 9 — 资产总览三分类重构 + 首页视图切换 + 布局优化 ✅

**实现内容:**

**资产账户三分类重构:**
- account_types 从二分类(savings/investment)改为三分类(savings/fund/stock)
- 新增 4 个 account_type：招行基金、微众基金、富途基金、招行理财
- 线上 12 个账户安全迁移，余额数据零损失
- 储蓄账户(3个)：招行储蓄(小美)、中国银行(小帅)、招行(小帅)
- 基金理财(7个)：微众理财×2、中金理财、微众基金、招行基金、招行理财、富途基金
- 股票账户(2个)：富途股票、中银股票

**首页我的/家庭视图切换:**
- 首页增加「我的 | 家庭」切换按钮（与月度收支逻辑一致）
- current_view 从 URL 参数读取，默认家庭视图
- 收支、资产、储蓄三个模块都随视图切换

**资产总览页布局优化:**
- 顶部概览改为一行四列（储蓄/基金理财/股票/总资产）
- 三个账户卡片一行三列展示（平板两列，手机单列）
- 资产页容器加宽至 1100px
- 去掉每行冗余的 category badge
- 账户名 4em 宽 + word-break 两字换行
- name 区域 flex-shrink:0，金额区域 flex:1 右对齐
- 卡片内 padding 和 gap 缩小，整体紧凑

**底部 Tab 栏美化（续）:**
- 修复 CSS 类名不匹配（bottom-tabs → bottom-tab-bar / tab-item）
- 电脑端和移动端统一显示
- 移动端 stats-bar 改为两列

**导航栏调整:**
- 桌面端：月度收支提升为一级导航（首页和资产总览之间）
- 宝宝基金收入管理菜单（排第一）
- 底部 Tab：首页 | 月度收支 | 资产总览 | 更多

**新增/修改文件:**
- `src/models.py` — DEFAULT_ACCOUNT_TYPES 更新为 9 个类型（含 fund/stock）
- `src/routes/account.py` — 三分类逻辑（savings/fund/stock）
- `src/templates/accounts.html` — 三栏展示 + 批量快照三分组 + 容器加宽
- `src/main.py` — 首页三分类资产总览 + 视图切换支持
- `src/templates/index.html` — 仪表盘模块 2 改三行 + 视图切换按钮
- `src/templates/base.html` — 导航调整 + 底部 Tab 类名修复
- `src/static/css/style.css` — acct-grid 三列 + 紧凑排版 + Tab 栏美化
- `src/routes/auth.py` — 登出改为 session.clear()

**数据库变更:**
- account_types 表：id=2(微众) → fund, id=3(中金) → fund, id=4(富途) → stock, id=5(中银国际) → stock
- 新增 account_types：id=6(招行基金/fund), id=7(微众基金/fund), id=8(富途基金/fund), id=9(招行理财/fund)
- accounts 表：4 个账户 type_id 更新（id=5→8, id=7→9, id=8→7, id=9→6）

### 2026-04-05: Phase 8 — 月度待办 Checklist + 聚焦气泡引导 ✅

**实现内容:**

**月度待办 Checklist（固定 4 项）:**
- 每月自动生成 4 项待办（用户首次访问时触发）：
  - ✅ 录入本月交易记录（必选，手动打钩）
  - ✅ 更新账户余额快照（必选，自动检测：所有账户都有快照→完成）
  - ✅ 录入储蓄记录（必选，自动检测：本月有记录→完成）
  - ☐ 录入宝宝基金（可选，手动打钩）
- 自动检测按当前登录用户判断，小美和小帅各自独立
- 手动打钩永远有效，可兜底自动检测未覆盖的情况

**首页仪表盘模块 4 改造:**
- 从通用任务摘要改为 checklist 卡片（☑/☐ + 跳转链接 + 进度条）
- 进度条只统计必选项，100% 时变绿
- 已完成项显示删除线 + 灰色，自动检测项显示「自动检测」badge
- 未完成项右侧显示「去录入 →」跳转链接

**聚焦遮罩 + 气泡引导:**
- 有未完成必选项时，登录后自动启动引导（每次登录触发一次）
- 页面变暗，高亮当前步骤的待办项，下方弹出气泡
- 气泡显示：步骤标签 + 标题 + 说明 + 步骤点 + 下一步按钮
- 最后一步按钮变为「知道了」，点遮罩可关闭
- 已完成项自动跳过，只引导未完成项
- 纯原生 JS 实现，四块遮罩拼接聚焦窗口

**导航栏调整:**
- 桌面端：首页 | 月度收支 | 资产总览 | 储蓄计划 | 管理 ▾（宝宝基金排第一）| 退出
- 移动端底部 Tab：🏠首页 | 💵月度收支 | 💳资产总览 | ⚙️更多
- 移动端侧边菜单：月度收支提升至首页后第一项，宝宝基金归入管理区

**底部 Tab 栏美化:**
- 修复 CSS 类名不匹配问题（HTML `bottom-tabs` → `bottom-tab-bar`）
- 电脑端和移动端统一显示，居中布局
- 白色背景 + 细阴影 + hover/active 棕金色主色

**登出 session 清理:**
- `session.clear()` 替代逐个 `session.pop`，确保 todo_popup 标记被清除

**新增/修改文件:**
- `src/models.py` — MonthlyTodo 新增 5 字段（detect_key/is_required/auto_detected/action_url），移除 related_entity_type/id
- `src/routes/monthly_todo.py` — **完全重写**：固定 4 项 checklist + 自动检测 + toggle 路由
- `src/main.py` — index() 增加 checklist 数据 + 弹窗逻辑 + MonthlyTodo 导入
- `src/templates/index.html` — 模块 4 改为 checklist 卡片 + 聚焦遮罩引导
- `src/templates/monthly_todo.html` — **完全重写**为简洁 checklist 详情页
- `src/templates/base.html` — 导航栏调整 + 底部 Tab 类名修复
- `src/routes/auth.py` — 登出改为 session.clear()
- `src/static/css/style.css` — 底部 Tab 栏美化 + 全尺寸显示

**数据库变更:**
- monthly_todos 表：新增 detect_key/is_required/auto_detected/action_url 列
- 本地开发：DROP TABLE 重建即可（无历史数据）
- 生产部署：需执行 ALTER TABLE 或 DROP TABLE 重建

### 2026-04-05: Phase 7 — 首页重做为仪表盘 + 小眼睛统一 ✅

**实现内容:**

**首页重做为三模块仪表盘:**
- 首页（`/`）从记账页改为概览仪表盘，包含三个卡片模块：
  - 模块 1：月度收支概览（收入/支出/结余 + 近 6 月趋势折线图）
  - 模块 2：资产总览（储蓄总额/投资总额/总资产，含多币种汇率换算）
  - 模块 3：储蓄计划概览（年度目标/已储蓄/进度条/完成率）
- 每个模块底部「查看详情 →」链接跳转到对应子页面

**月度收支独立页面:**
- 新建 `transaction_bp` 蓝图（`/transactions`），完整迁移原首页的记账功能
- 包含：记账表单 + 交易列表 + 分页 + 快捷模板 + 视图切换 + 迷你趋势图
- 交易增删改路由（`/add`、`/edit/<id>`、`/delete/<id>`）重定向目标从 `/` 改为 `/transactions`

**导航文案更新:**
- 桌面端：首页 | 资产总览 | 储蓄计划 | 宝宝基金 | 管理▾（含月度收支）| 退出
- 移动端底栏：🏠首页 | 💳资产总览 | 🎯储蓄计划 | ⚙️更多
- 汉堡菜单：新增「💵 月度收支」入口

**小眼睛金额隐藏统一:**
- 扩展 app.js 选择器，覆盖所有页面金额元素：`.stat-value`、`.dash-stat-value`、`.asset-row-value`、`.amount-hide`
- 首页仪表盘在第一个卡片头部自动插入小眼睛按钮
- 新增 `window.ffReapplyHide()` 全局函数，解决 JS 动态赋值后覆盖隐藏状态的问题
- 所有页面默认隐藏金额（🙈），状态通过 localStorage 全局同步
- 储蓄进度条和百分比不受小眼睛影响

**新增/修改文件:**
- `src/routes/transaction.py` — **新建**，月度收支蓝图
- `src/templates/transactions.html` — **新建**，月度收支页面模板
- `src/main.py` — 重写 index 路由为仪表盘；注册 transaction_bp；交易重定向改为 `/transactions`
- `src/templates/index.html` — **重写**为三模块仪表盘
- `src/templates/base.html` — 导航文案更新（资产总览/储蓄计划/月度收支）
- `src/static/js/app.js` — 小眼睛选择器扩展 + ffReapplyHide 全局函数

### 2026-04-04: Phase 6 — 体验细节优化 ✅

**实现内容:**

**千分位金额格式:**
- 在 database.py 注册 Jinja2 `currency` 自定义过滤器（支持 0/1/2 位小数）
- 替换所有模板中的 `"%.2f"|format` 为 `|currency`，含 accounts/savings/baby_fund/index/recurring/quick_templates 共 6 个模板
- upload.html 的 JS `toFixed(2)` 改为 `toLocaleString`

**账户列表左右两列精简排版:**
- 用 `.acct-grid` 两列 grid 布局替代上下排列的表格
- 每行精简为：账户名（含类型 badge + 归属人彩色圆形 icon）| 余额 | 操作
- 归属人 icon 按用户区分颜色：小帅=莫兰迪蓝(#6B9EB5)、小美=莫兰迪紫(#9B8EC4)
- 移动端自动降为单列

**首页交易列表分页:**
- main.py 用 SQLAlchemy `paginate(per_page=10)` 替代 `.all()`
- index.html 底部添加分页导航（上/下页 + 页码 + 省略号）
- 分页样式：圆角按钮，当前页高亮

**储蓄计划 / 宝宝基金去除个人视图:**
- savings.py 和 baby_fund.py 的 `current_view` 固定为 `'family'`
- 删除两个模板中的「我的/家庭」视图切换按钮
- 无家庭用户自动回退到个人数据

**新增/修改文件:**
- `src/database.py` — 新增 currency 过滤器
- `src/static/css/style.css` — 新增 acct-grid/acct-compact-*/pagination 样式 + owner icon 颜色
- `src/templates/accounts.html` — 两列精简布局 + 彩色归属 icon
- `src/templates/index.html` — 分页导航
- `src/templates/savings.html` — 去除视图切换 + currency 过滤器
- `src/templates/baby_fund.html` — 去除视图切换 + currency 过滤器
- `src/templates/quick_templates.html` — currency 过滤器
- `src/templates/recurring.html` — currency 过滤器
- `src/templates/upload.html` — JS toLocaleString
- `src/main.py` — 分页查询
- `src/routes/savings.py` — 固定 family 视图
- `src/routes/baby_fund.py` — 固定 family 视图

### 2026-04-03: 安全扫描 + 修复 ✅

**扫描方式:** Bandit 自动扫描 + 手动代码审查，共发现 14 个问题（4 高/5 中/5 低）

**已修复（10 项）:**
- debug=True 硬编码 → 改为环境变量控制
- /init-db 路由公开暴露 → 已删除
- 登录无暴力破解防护 → session 记录失败次数，5 次锁定 5 分钟
- SECRET_KEY 有默认值 → 添加安全提醒注释
- 异常信息泄露给用户 → 改为通用错误提示
- 邀请码用 random 生成 → 改用 secrets 模块
- 会话无过期时间 → 设置 24 小时过期
- 密码强度要求过低 → 最低 8 位 + 必须含字母和数字
- Decimal 无范围校验 → 金额限制 0 ~ 999 万
- 家庭页面 endpoint 错误 → 修复 regenerate_invite → regenerate_invite_code

**已知问题（4 项，记录为技术债）:**
- CSRF 防护缺失（需安装 flask-wtf，家庭内部使用风险低）
- 文件上传缺 MIME 校验（目前靠扩展名过滤）
- urlopen 汇率 API 无 SSRF 限制（URL 硬编码，当前安全）
- 开发模式绑定 0.0.0.0（生产环境 Gunicorn 已安全）

**安全亮点（原本就做得好的）:**
- 密码 pbkdf2 哈希存储 ✅
- SQLAlchemy ORM 防 SQL 注入 ✅
- Jinja2 自动转义防 XSS ✅
- CSV 注入防护 ✅
- .gitignore 包含敏感文件 ✅

### 2026-03-31: Phase 5 — 体验打磨 + 多币种 + 快捷记账 ✅

**实现内容:**

**快捷记账功能:**
- 新增 TransactionTemplate 模型：常用交易一键填充，首页显示快捷按钮（按使用频率排序，最多 6 个）
- 新增 RecurringTransaction 模型：定期交易自动生成（月/周/自定义周期），首页访问时触发，支持多日补漏
- 新增 2 个蓝图路由 + 2 个管理页面（设置 ▾ → 快捷模板 / 定期交易）

**多币种支持:**
- Account 模型新增 currency 字段（CNY/HKD/USD）
- AccountBalance 模型新增 note 字段（快照备注）
- 投资账户创建时可选币种，列表显示原币余额 + 人民币换算
- 资产总额按实时汇率（exchangerate-api.com，1 小时缓存）换算人民币后求和

**批量录入快照:**
- 全屏模态框表格式布局（860px 宽），所有账户一次性填写
- 5 列表格：账户 | 上月余额 | 本月余额 | 变化 | 备注
- 投资账户支持币种选择 + 实时人民币换算显示
- 变化量输入时即时计算

**页面布局统一:**
- 账户管理：储蓄/投资账户改为表格式（账户名/类型/所属/余额/操作）
- 储蓄计划：计划列表改为表格式（计划名/类型/年份/已储蓄/进度条/操作）
- 储蓄记录：独立模块，表格形式（日期/计划/金额/备注/操作人/录入时间）
- 宝宝基金：每条记录显示操作人 + UTC+8 录入时间
- 账户名按字母排序

**基础设施:**
- Nginx 静态文件缓存改为 no-cache（解决 CSS 更新后浏览器不刷新）
- GitHub 镜像加速（ghfast.top），解决服务器 git pull 超时
- Drawer 添加 visibility:hidden 防止闪现
- 所有时间显示 UTC+8（timedelta context processor）

**新增文件:**
- `src/routes/template.py` — 快捷模板 CRUD
- `src/routes/recurring.py` — 定期交易 CRUD + 自动执行
- `src/templates/quick_templates.html` — 快捷模板管理页面
- `src/templates/recurring.html` — 定期交易管理页面

**设计文档:** `docs/superpowers/specs/2026-03-28-quick-entry-design.md`
**实施计划:** `docs/superpowers/plans/2026-03-28-quick-entry-plan.md`

### 2026-03-26: Phase 4 — UI 体验优化 ✅

**实现内容:**
- 模板重构：抽取 base.html + auth_base.html 公共模板，12 个子模板改为继承，消除约 450 行重复代码
- 移动端适配：底部 Tab 栏（首页/账户/报表/更多）+ 汉堡侧滑菜单 + 768px/1024px 响应式断点
- Toast 消息：基于 Flask flash（with_categories=true），成功绿色 3 秒自动消失，错误红色手动关闭
- 自定义删除确认弹窗：替代浏览器原生 confirm()，data-confirm-delete 属性统一拦截
- 空状态提示：首页/账户/储蓄/宝宝基金 4 个页面，无数据时显示图标+文案+引导按钮
- 表单 loading：data-loading 属性，提交时按钮禁用+"处理中..."
- Flash 分类：所有路由 flash 添加 success/error 类别

**新增文件:**
- `src/templates/base.html` — 公共模板（导航、Tab、Toast、确认弹窗）
- `src/templates/auth_base.html` — 认证页公共模板
- `src/static/js/app.js` — 公共交互 JS

**导航结构（移动端）:**
```
顶部栏：💰 家庭财务 + ☰ 汉堡按钮
底部 Tab：🏠首页 | 💳账户 | 📊报表 | ⚙️更多
汉堡菜单（侧滑）：所有导航项 + 退出
```

**设计文档:** `docs/superpowers/specs/2026-03-26-ui-optimization-design.md`
**实施计划:** `docs/superpowers/plans/2026-03-26-ui-optimization-plan.md`

### 2026-03-24: Phase 3 — 储蓄计划 + 宝宝基金 + 批量导入 ✅

**实现内容:**
- 新增 4 个数据模型：SavingsPlan、SavingsRecord、BabyFund、ImportRecord
- 新增 3 个 Flask 蓝图：savings_bp、baby_fund_bp、upload_bp
- 新增 3 个页面模板 + 文件解析工具模块
- 导航栏重构为二级下拉菜单

**新增路由:**
- 储蓄计划：列表(GET) + 创建/编辑/删除计划(POST) + 录入/删除记录(POST)
- 宝宝基金：列表(GET) + 添加/编辑/删除(POST)，创建时自动生成收入交易，删除时级联删除
- 批量导入：页面(GET) + 解析文件(POST→JSON) + 确认导入(POST→JSON) + 模板下载(GET)

**文件解析器 (`src/utils/importers.py`):**
- `parse_wechat_csv()` — 微信账单（跳过前 16 行概要，清洗 ¥ 符号）
- `parse_alipay_csv()` — 支付宝账单（自动检测表头行）
- `parse_template_csv()` / `parse_excel()` — 标准模板 CSV/Excel
- `detect_source_type()` — 自动识别文件来源
- `map_category()` — 分类模糊匹配
- `sanitize_cell()` — CSV 注入防护

**导航栏结构（二级下拉）:**
```
首页 | 账户 ▾ | 报表 | 设置 ▾ | [家庭] | 退出
       ├── 账户管理    ├── 分类管理
       ├── 储蓄计划    └── 批量导入
       └── 宝宝基金
```

**测试覆盖:** 19 个测试全部通过
- test_savings.py: 5 tests（模型、路由、进度计算、编辑）
- test_baby_fund.py: 4 tests（创建联动、删除级联、编辑同步、类型校验）
- test_importers.py: 7 tests（4种解析器 + 检测 + 映射 + 安全）
- test_upload.py: 3 tests（解析、确认导入、去重检测）

**设计文档:** `docs/superpowers/specs/2026-03-22-phase3-design.md`
**实施计划:** `docs/superpowers/plans/2026-03-22-phase3-implementation.md`

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

### 2026-03-31: SQLite 新增字段部署问题（反复出现）

**问题:** 模型新增字段后部署到服务器，`create_all()` 不会给已有表添加新列，导致 500 错误
**原因:** SQLite 的 `db.create_all()` 只创建不存在的表，不会 ALTER 已有表
**解决:** 部署时必须手动执行 `ALTER TABLE xxx ADD COLUMN yyy`
**经验:** 每次模型新增字段，部署脚本应包含 ALTER TABLE 语句。已发生 3 次（recurring_transactions 表、transaction_templates 表、accounts.currency + account_balance.note）。未来考虑引入 Flask-Migrate 做数据库迁移管理。

### 2026-03-31: Phase 5 体验打磨经验

**问题 1:** Nginx 缓存导致 CSS/JS 更新后浏览器不刷新
**原因:** deploy.sh 配置了 `expires 7d`，浏览器缓存旧的静态文件长达 7 天
**解决:** 将 Nginx 静态文件配置改为 `expires off; add_header Cache-Control no-cache`
**经验:** 开发阶段不应缓存静态文件。生产环境可用文件名 hash 做缓存破坏

**问题 2:** 批量快照面板 grid 布局在生产环境不生效
**原因:** 内嵌在页面中的 grid 表格被外层 CSS 覆盖，导致 5 列 grid 变成单列堆叠
**解决:** 先改抽屉弹窗，再改全屏模态框。最终用全屏模态框 + inline style grid 解决
**经验:** 复杂布局优先用模态框（独立层级），避免被页面其他 CSS 影响

**问题 3:** 子代理并行修改 main.py 时的 timedelta context processor 冲突
**原因:** 3 个子代理都需要添加 timedelta context processor，可能重复添加
**解决:** 第一个完成的子代理添加了 context processor，后续子代理检测到已存在后跳过
**经验:** 并行子代理共享文件时，需在提示词中说明"检查是否已存在再添加"

### 2026-03-26: Phase 4 UI 优化经验

**问题 1:** 模板重构时 `<div class="container">` 嵌套错误
**原因:** base.html 中已有 `<div class="container">`，但部分子模板没有删除自己的 container 包裹，导致双层嵌套
**解决:** 逐个模板检查，确保子模板只输出 content block 内的内容
**经验:** 大规模模板重构时，先改造 1 个模板验证通过，再批量改造其余模板

**问题 2:** flash 消息 with_categories 不兼容
**原因:** base.html 使用 `get_flashed_messages(with_categories=true)` 返回 (category, message) 元组，但 auth 页面仍用旧的 `get_flashed_messages()` 返回纯字符串
**解决:** auth 页面继承 auth_base.html（无 Toast），保留自己的 flash 渲染方式
**经验:** 公共模板中的 flash 格式变更会影响所有子模板，不继承公共模板的页面需要单独处理

**问题 3:** 移动端 CSS 断点与旧断点冲突
**原因:** 新增 768px 断点时，旧的 640px 断点仍然存在，部分样式互相覆盖
**解决:** 在 style.css 末尾追加新断点，后续清理旧断点
**经验:** 添加响应式断点时，应先明确"替代"还是"共存"策略，避免样式冲突

**问题 4:** 删除确认弹窗需要同时支持 form 和非 form 场景
**原因:** 大部分删除按钮在 `<form>` 内，但 family/info.html 的某些操作用的是 JS confirm()
**解决:** app.js 同时支持 form.submit() 和 data-url 跳转两种方式；纯 JS 的 confirm 保持不变
**经验:** 统一交互组件时，需要先盘点所有现有的实现方式，不能假设所有页面都用同一种模式

### 2026-03-24: Phase 3 实施经验

**问题 1:** upload.html 中 `url_for('account.accounts_page')` endpoint 名写错，应为 `account.account_list`
**原因:** 子 agent 创建模板时用了错误的 endpoint 名，测试只验证了路由返回码而没有渲染模板
**解决:** 修正 endpoint 名。教训：模板中的 url_for 也需要在集成测试中覆盖

**问题 2:** 导航栏 7 个一级项目过多，层级关系不清晰
**原因:** Phase 1-3 逐步添加功能时每个都直接加到一级导航，没有整体规划
**解决:** 重构为二级下拉导航（账户 ▾ / 设置 ▾），一级缩减到 4 项
**经验:** 新增功能时应优先考虑归入已有导航分组，而非增加一级导航项

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

## 服务器部署信息

### 服务器实例

| 项目 | 信息 |
|------|------|
| 云服务商 | 腾讯云 Lighthouse |
| 账号 | candyxiao 个人账号 |
| 地域 | 广州 |
| IP 地址 | 119.91.205.137 |
| 系统 | Ubuntu |
| SSH 用户名 | ubuntu（密钥登录） |
| SSH 密钥 | `~/.ssh/candyworkbench.pem` |
| 应用目录 | `/opt/family-finance` |
| 访问地址 | http://119.91.205.137 |

### 部署架构

```
用户浏览器
    ↓ HTTP (80)
  Nginx (反向代理 + 静态文件缓存)
    ↓ 127.0.0.1:5001
  Gunicorn (WSGI 生产服务器, 2 workers)
    ↓
  Flask App + SQLite (/opt/family-finance/data/family_finance.db)
```

### SSH 登录服务器

```bash
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137
sudo -i  # 切换到 root
```

### 日常更新流程

**本地开发完成后：**
```bash
# 1. 本地推送代码
git add . && git commit -m "feat: xxx" && git push

# 2. SSH 登录服务器后执行一条命令
cd /opt/family-finance && git pull origin main && systemctl restart family-finance
```

### 常用运维命令

| 操作 | 命令 |
|------|------|
| 查看服务状态 | `systemctl status family-finance` |
| 查看实时日志 | `journalctl -u family-finance -f` |
| 重启服务 | `systemctl restart family-finance` |
| 停止服务 | `systemctl stop family-finance` |
| 查看 Nginx 日志 | `tail -f /var/log/nginx/error.log` |
| 查看应用日志 | `tail -f /opt/family-finance/data/error.log` |
| 查看访问日志 | `tail -f /opt/family-finance/data/access.log` |

### 故障排查

```bash
# 服务启动失败
systemctl status family-finance    # 看错误信息
journalctl -u family-finance -n 50 # 看最近 50 行日志

# Nginx 报错
nginx -t                           # 检查配置语法
systemctl restart nginx            # 重启 Nginx

# 数据库问题
ls -la /opt/family-finance/data/   # 确认数据库文件存在
```

### 重新部署（从零开始）

```bash
# SSH 登录服务器后
sudo -i
curl -sSL https://raw.githubusercontent.com/candyxiao9216/family-finance/main/deploy.sh -o /tmp/deploy.sh && bash /tmp/deploy.sh
```

---

**最后更新:** 2026-04-06
**文档版本:** 2.0.0
