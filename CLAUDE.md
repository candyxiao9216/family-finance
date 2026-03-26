# CLAUDE.md - 家庭财务管理系统

## 项目概述

**项目名称:** 0225-FamilyFinance
**项目类型:** 个人财务管理 Web 应用
**状态:** Phase 4 已完成 (v1.4.0)
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
├── models.py              # 所有数据模型（12 个）
├── database.py            # 数据库连接和初始化
├── routes/                # 路由层（Flask 蓝图）
│   ├── auth.py            # 认证路由
│   ├── account.py         # 账户路由
│   ├── category.py        # 分类路由
│   ├── savings.py         # 储蓄路由
│   ├── baby_fund.py       # 宝宝基金路由
│   ├── upload.py          # 文件上传路由
│   └── family.py          # 家庭路由
├── utils/                 # 工具函数
│   └── importers.py       # CSV/Excel 解析
├── static/
│   ├── css/style.css      # 全局样式（含移动端响应式）
│   └── js/app.js          # 公共交互 JS
└── templates/             # HTML 模板（Jinja2 继承）
    ├── base.html          # 公共模板（导航、Tab、Toast、确认弹窗）
    ├── auth_base.html     # 认证页公共模板
    ├── index.html         # 首页
    ├── accounts.html      # 账户管理
    ├── reports.html       # 数据报表
    ├── categories.html    # 分类管理
    ├── savings.html       # 储蓄计划
    ├── baby_fund.html     # 宝宝基金
    ├── upload.html        # 批量导入
    ├── edit_transaction.html
    ├── auth/              # 登录/注册
    └── family/            # 家庭信息/成员
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
- ✅ 移动端适配（底部 Tab + 汉堡菜单）
- ✅ 交互优化（Toast、确认弹窗、空状态、loading）

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

**最后更新:** 2026-03-26
**文档版本:** 1.4.0
