## 功能实现记录

### 2026-04-07: Phase 10 — 智能财务顾问模块 ✅

**实现内容:**

**财务顾问5页Tab导航:**
- 新增 advisor 蓝图（`/advisor/`），包含总览/股票/基金/理财/储蓄 5 个Tab页
- 每个页面独立管理对应持仓和 AI 分析

**持仓管理（3种资产类型CRUD）:**
- StockHolding: 股票持仓（代码/名称/市场/股数/成本/币种）
- FundHolding: 基金持仓（代码/名称/类型/份额/金额/净值/收益/收益率/状态）
- WealthHolding: 理财产品（产品名/管理机构/买入金额/当前金额/收益/年化/日期/类型）
- 所有持仓支持添加/编辑/删除

**AI 分析引擎（智谱GLM全系列模型）:**
- 文本分析: GLM-5-Turbo（默认模型，快速响应，避免 GLM-5 推理超时）
- 多模态理解: GLM-5V-Turbo（图片OCR，为截图导入准备）
- 图像生成: GLM-Image
- 7个AI分析端点：综合分析/股票整体/个股/基金整体/个基/理财/储蓄
- OpenAI兼容格式调用（智谱/MiniMax等均可适配）

**AI 模型兼容与调优:**
- GLM-5 推理模型兼容（content 为空时 fallback 到 reasoning_content）
- 默认模型从 GLM-5 改为 GLM-5-Turbo（推理快速版，避免超时）
- max_tokens 调大到 16384（防止长分析输出截断）
- timeout 增到 180s

**AI 分析交互（右侧抽屉）:**
- 全局 AI 抽屉组件（`window.aiDrawer`），替代底部面板
- 抽屉内容：标题+正文+时间戳+缓存标记+刷新按钮+历史入口
- marked.js Markdown 渲染
- 支持强制刷新（`?refresh=1` 跳过缓存）

**AI 建议持久化:**
- AiAdviceCache: 短期缓存（1小时TTL，key覆盖）
- AiAdviceHistory: 永久历史记录（类型/文本/模型/时间）
- 独立历史页面（`/advisor/history`）：类型筛选+展开全文+Markdown渲染

**实时行情:**
- Sina Finance API（hq.sinajs.cn）获取港股/A股/美股实时报价
- MarketDataCache 数据库缓存（5分钟TTL）
- 批量获取 + 重复股票代码去重处理

**资产配置分析:**
- 从 Account（储蓄）+ FundHolding（基金）+ StockHolding×实时价（股票）+ WealthHolding（理财）实时聚合
- 仪表盘饼图展示配置比例

**基金增强功能:**
- 可排序表头（金额/收益/收益率，默认金额降序）
- 赎回转投操作（状态标记 holding→redeemed + 转投记录）
- 已赎回基金灰色显示

**页面标题 + 千分位格式:**
- 所有页面 render_template 添加 `page_title=` 参数
- 所有金额使用 `|currency` 过滤器千分位格式化

**新增/修改文件:**
- `src/services/__init__.py` — 服务层初始化
- `src/services/ai_advisor.py` — **新建**，AI 分析引擎（智谱GLM全系列）
- `src/services/market_data.py` — **新建**，行情数据服务（Sina API）
- `src/routes/advisor.py` — **新建**，财务顾问蓝图（758行）
- `src/templates/advisor/dashboard.html` — **新建**，顾问总览
- `src/templates/advisor/stocks.html` — **新建**，股票分析
- `src/templates/advisor/funds.html` — **新建**，基金分析
- `src/templates/advisor/wealth.html` — **新建**，理财分析
- `src/templates/advisor/savings.html` — **新建**，储蓄建议
- `src/templates/advisor/history.html` — **新建**，AI分析历史
- `src/models.py` — +StockHolding/FundHolding/WealthHolding/AiAdviceCache/AiAdviceHistory/MarketDataCache（6个新模型）
- `src/database.py` — +signed_currency 过滤器 + _safe_add_column
- `src/static/js/app.js` — +window.aiDrawer 全局AI抽屉
- `src/static/css/style.css` — +advisor/drawer/history 样式（约900行）
- `src/templates/base.html` — +AI抽屉HTML + 页面标题栏
- `src/config.py` — +dotenv 加载
- `requirements.txt` — +requests
- `.env.example` — **新建**，AI API配置模板
- 所有路由文件 — +page_title 参数

**我的/家庭视图切换:**
- 所有顾问页面支持"我的/家庭"视图切换（与资产总览一致）
- URL 参数 `?view=personal|family` 控制数据筛选
- Tab 导航切换时保持 view 参数不丢失
- AI 分析 API 也随视图切换，分析对应视图的数据
- 有家庭用户显示切换按钮，无家庭用户只看自己数据
- 新增 `_get_user_ids_by_view()` 替代硬编码的 `_get_family_user_ids()`
- 家庭视图下股票/基金/理财列表名字旁显示归属人圆形 icon（蓝=小帅 紫=小美），复用 acct-owner-icon 样式；个人视图不显示

**持仓批量导入:**
- 独立导入页面（`/advisor/import`），三步流程：选择→预览→确认
- Excel/CSV 模板导入（4种类型：股票/基金/理财/储蓄，含可下载模板）
- App 截图 AI 识别（GLM-5V-Turbo 多模态模型提取持仓数据）
- 账户名自动映射（模糊匹配+手动选择） + 重复检测（stock_code/fund_code/product_name + account_id）
- 储蓄类型为更新余额
- 总览页新增"批量导入"入口卡片

**新增/修改文件（持仓批量导入）:**
- `src/templates/advisor/import.html` — **新建**，三步导入页面（选择→预览→确认）
- `src/static/holding_stock_template.csv` — **新建**，股票导入模板
- `src/static/holding_fund_template.csv` — **新建**，基金导入模板
- `src/static/holding_wealth_template.csv` — **新建**，理财导入模板
- `src/static/holding_savings_template.csv` — **新建**，储蓄导入模板
- `src/routes/advisor.py` — +import 页面路由 + parse-excel/parse-image/confirm API
- `src/templates/advisor/dashboard.html` — +批量导入入口卡片
- `requirements.txt` — +pandas>=2.0.0

**数据库变更:**
- 新增 6 张表：stock_holdings, fund_holdings, wealth_holdings, market_data_cache, ai_advice_cache, ai_advice_history
- fund_holdings 新增 status 列（holding/redeemed）

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

