# 任务清单（Tasks）

> 规则：这是"任务索引"，不要写长篇设计文档。
> 每个任务最好控制在 30–90 分钟可完成；如果更大，先拆分。

## 字段说明
- 状态：TODO / DOING / BLOCKED / DONE
- 优先级：P0 / P1 / P2
- 规模：S（≤30m）/ M（30–90m）/ L（需要先拆分）

---

## 当前里程碑：Phase 1 - 核心功能完善（2026-02-27）

### TASK-001：修复分类下拉框硬编码问题 ✅
- 状态：DONE
- 优先级：P0
- 规模：S
- 目标（一句话）：分类选项从后端动态获取，而非模板硬编码
- 验收标准：
  - [x] index.html 中分类 select 动态渲染 categories 数据
  - [x] 支持新增自定义分类后自动显示
  - [x] 按类型（收入/支出）分组显示
- 涉及文件/目录：
  - `/src/main.py`（确认已传递 categories 给模板）
  - `/src/templates/index.html`
- 依赖：无
- 备注：
  - main.py:66-68 已传递 categories，只是模板没用到
  - 当前模板中是硬编码的 ID（1,2,3,4）

### TASK-002：家庭共享数据模型实现 ✅
- 状态：DONE
- 优先级：P0
- 规模：M
- 目标（一句话）：实现 Family 数据模型和 User-Family 关联
- 验收标准：
  - [x] Family 模型创建（id、name、invite_code、created_at）
  - [x] User 模型添加 family_id 外键
  - [x] 建立一对多关系映射
  - [x] to_dict() 方法包含家庭信息
  - [x] 向后兼容性保证
- 涉及文件/目录：
  - `/src/models.py`
  - `/tests/test_models.py`
- 依赖：无
- 备注：已完成，通过代码审查

### TASK-003：家庭管理路由实现 ✅
- 状态：DONE
- 优先级：P0
- 规模：M
- 目标（一句话）：实现家庭创建、加入、成员管理路由
- 验收标准：
  - [x] 家庭创建路由（第一个用户自动创建）
  - [x] 家庭加入路由（邀请码验证）
  - [x] 家庭成员列表路由
  - [x] 邀请码管理路由
- 涉及文件/目录：
  - `/src/routes/family.py`
  - `/src/routes/auth.py`（注册流程集成家庭创建/加入）
  - `/src/templates/family/info.html`
  - `/src/templates/family/members.html`
  - `/src/main.py`（蓝图注册）
- 依赖：TASK-002
- 备注：已完成，包含家庭信息页、成员列表页、邀请码重新生成、API 接口

---

## 待办池（Phase 2 - 扩展功能）

### TASK-003：交易编辑功能 ✅
- 状态：DONE
- 优先级：P1
- 规模：M
- 目标（一句话）：支持编辑已有交易记录，含修改日志追踪
- 验收标准：
  - [x] 交易列表显示编辑按钮
  - [x] 点击编辑显示编辑表单（预填充现有数据）
  - [x] 提交更新数据库记录
  - [x] TransactionModification 模型记录逐字段修改历史
  - [x] 家庭成员可互相编辑/删除交易
  - [x] 首页显示「已修改」徽标
- 涉及文件/目录：
  - `/src/main.py`（edit_transaction 路由，GET+POST）
  - `/src/models.py`（TransactionModification 模型、Transaction 追踪字段）
  - `/src/templates/edit_transaction.html`（编辑表单页）
  - `/src/templates/index.html`（编辑按钮、修改徽标）
  - `/src/static/css/style.css`（btn-edit、t-modified 样式）
- 依赖：TASK-001
- 备注：已完成，含家庭权限检查和修改历史展示

### TASK-004：自定义分类管理 ✅
- 状态：DONE
- 优先级：P1
- 规模：M
- 目标（一句话）：添加分类管理界面，支持添加/删除用户自定义分类
- 验收标准：
  - [x] 创建分类管理页面
  - [x] 显示系统默认分类和用户自定义分类
  - [x] 支持添加新分类（收入/支出类型）
  - [x] 支持删除用户自定义分类
- 涉及文件/目录：
  - `/src/routes/category.py`（新建，category_bp 蓝图）
  - `/src/templates/categories.html`（新建）
  - `/src/main.py`（注册蓝图）
  - `/src/templates/index.html`（添加导航入口）
  - `/src/static/css/style.css`（分类页面样式）
- 依赖：TASK-002
- 备注：已完成，系统分类受保护不可删除，删除自定义分类时关联交易变为未分类

### TASK-005：数据可视化图表 ✅
- 状态：DONE
- 优先级：P1
- 规模：M
- 目标（一句话）：使用 Chart.js 添加收支统计图表
- 验收标准：
  - [x] 月度收支趋势折线图
  - [x] 分类支出饼图
- 涉及文件/目录：
  - `/src/routes/reports.py`（报表 API 蓝图：趋势 + 分类数据接口）
  - `/src/templates/reports.html`（独立报表页：折线图 + 双饼图）
  - `/src/templates/index.html`（首页迷你趋势图 + 报表导航入口）
  - `/src/static/css/style.css`（图表样式 + 响应式布局）
  - `/src/main.py`（蓝图注册）
- 依赖：无
- 备注：已完成，支持个人/家庭视图切换、1/3/6/12 月时间范围选择

### TASK-006：账户余额追踪 ✅
- 状态：DONE
- 优先级：P2
- 规模：L
- 目标（一句话）：支持多账户管理和余额记录
- 验收标准：
  - [x] 账户数据模型（AccountType, Account, AccountBalance）
  - [x] 预设 5 种账户类型（银行/微众/中金/富途/中银国际）
  - [x] 账户管理页面（创建/删除/月度快照录入）
  - [x] 交易可选关联账户，自动更新余额
  - [x] 资产趋势图（储蓄/投资/总资产三条曲线）
- 涉及文件/目录：
  - `/src/models.py`（AccountType, Account, AccountBalance 模型）
  - `/src/database.py`（预设账户类型初始化）
  - `/src/routes/account.py`（账户管理蓝图）
  - `/src/templates/accounts.html`（账户管理页面）
  - `/src/templates/index.html`（导航链接 + 交易表单账户下拉框）
  - `/src/templates/edit_transaction.html`（编辑表单账户下拉框）
  - `/src/routes/reports.py`（asset-trend API）
  - `/src/templates/reports.html`（资产趋势图）
  - `/src/main.py`（蓝图注册 + 交易余额逻辑）
  - `/src/static/css/style.css`（账户页面样式）
- 依赖：TASK-005
- 备注：已完成，支持个人/家庭视图切换，编辑/删除交易时自动反向修正账户余额

---

## Phase 3 - 储蓄计划 + 宝宝基金 + 批量导入（2026-03-24）

### TASK-007：储蓄计划管理 ✅
- 状态：DONE
- 优先级：P1
- 规模：M
- 目标：创建月度/年度储蓄计划，手动录入储蓄记录，自动计算进度
- 涉及文件：
  - `/src/models.py`（SavingsPlan, SavingsRecord 模型）
  - `/src/routes/savings.py`（储蓄蓝图）
  - `/src/templates/savings.html`（卡片式布局 + 进度条）
  - `/tests/test_savings.py`（5 个测试）

### TASK-008：宝宝基金记录 ✅
- 状态：DONE
- 优先级：P1
- 规模：M
- 目标：记录宝宝红包/礼金，自动生成收入交易，编辑/删除联动
- 涉及文件：
  - `/src/models.py`（BabyFund 模型）
  - `/src/routes/baby_fund.py`（宝宝基金蓝图）
  - `/src/templates/baby_fund.html`
  - `/tests/test_baby_fund.py`（4 个测试）

### TASK-009：CSV/Excel 批量导入 ✅
- 状态：DONE
- 优先级：P1
- 规模：L
- 目标：支持微信/支付宝账单和标准模板导入，含去重检测和交互确认
- 涉及文件：
  - `/src/models.py`（ImportRecord 模型）
  - `/src/utils/importers.py`（7 个解析函数）
  - `/src/routes/upload.py`（上传蓝图）
  - `/src/templates/upload.html`（三步流程）
  - `/tests/test_importers.py`（7 个测试）
  - `/tests/test_upload.py`（3 个测试）

---

## Phase 7 - 首页仪表盘重做（2026-04-05）

### TASK-010：首页重做为三模块仪表盘 ✅
- 状态：DONE
- 优先级：P0
- 规模：M
- 目标：首页从记账页改为概览仪表盘（月度收支+资产总览+储蓄计划）
- 涉及文件：
  - `/src/main.py`（重写 index 路由为仪表盘数据查询）
  - `/src/templates/index.html`（重写为三模块卡片布局）
  - `/src/routes/transaction.py`（**新建**，月度收支蓝图）
  - `/src/templates/transactions.html`（**新建**，迁移原首页记账功能）
  - `/src/templates/base.html`（导航文案更新：资产总览/储蓄计划/管理▾含月度收支）

### TASK-011：小眼睛金额隐藏统一 ✅
- 状态：DONE
- 优先级：P1
- 规模：S
- 目标：首页仪表盘添加小眼睛，所有页面默认隐藏金额，进度条和百分比不隐藏
- 涉及文件：
  - `/src/static/js/app.js`（选择器扩展 + ffReapplyHide 全局函数）
  - `/src/templates/index.html`（amount-hide class + ffReapplyHide 调用）
  - `/src/templates/transactions.html`（ffReapplyHide 调用）

---

## Phase 10 - 智能财务顾问（2026-04-07）

### TASK-012：AI 分析引擎 + 智谱GLM集成 ✅
- 状态：DONE
- 优先级：P0
- 规模：L
- 目标：接入智谱GLM全系列模型（文本GLM-5/多模态GLM-5V-Turbo/图像GLM-Image）
- 涉及文件：
  - `/src/services/ai_advisor.py`（AI引擎，支持文本/视觉/图像三类API）
  - `/src/services/market_data.py`（Sina行情API + 数据库缓存）
  - `.env.example`（API配置模板）

### TASK-013：持仓管理CRUD ✅
- 状态：DONE
- 优先级：P0
- 规模：M
- 目标：股票/基金/理财三类持仓的增删改查
- 涉及文件：
  - `/src/models.py`（StockHolding/FundHolding/WealthHolding + 3个缓存表）
  - `/src/routes/advisor.py`（CRUD路由 + 页面路由）
  - `/src/templates/advisor/`（6个页面模板）

### TASK-014：AI 分析交互 + 历史记录 ✅
- 状态：DONE
- 优先级：P0
- 规模：M
- 目标：右侧抽屉展示AI分析 + 时间戳 + 缓存标记 + 强制刷新 + 永久历史
- 涉及文件：
  - `/src/static/js/app.js`（window.aiDrawer 全局组件）
  - `/src/templates/base.html`（抽屉HTML）
  - `/src/templates/advisor/history.html`（独立历史页）
  - `/src/static/css/style.css`（抽屉+历史样式）

### TASK-015：基金增强（排序+赎回转投） ✅
- 状态：DONE
- 优先级：P1
- 规模：S
- 目标：基金表头排序（金额/收益/收益率）+ 赎回转投操作流程
- 涉及文件：
  - `/src/templates/advisor/funds.html`（排序JS + 转投模态框）
  - `/src/routes/advisor.py`（转投API）

---

## 已完成任务

### TASK-P0-001：交易记录基本功能
- 状态：DONE
- 实现内容：添加交易、删除交易、交易列表展示
- 相关文件：`/src/main.py`, `/src/templates/index.html`

### TASK-P0-002：用户认证基础
- 状态：DONE（待调整）
- 实现内容：注册、登录、退出、密码哈希存储、session 管理
- 相关文件：`/src/models.py`, `/src/routes/auth.py`
- 备注：用户反馈需求有变化，见 TASK-002

### TASK-P0-003：月度统计
- 状态：DONE
- 实现内容：月度收入、支出、结余统计
- 相关文件：`/src/main.py`

### TASK-P0-004：用户数据隔离
- 状态：DONE
- 实现内容：用户只能看到自己的交易数据
- 相关文件：`/src/main.py`
