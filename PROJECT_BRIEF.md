# 项目简报（Project Brief）

## 0. 一句话目标
- 目标：构建一个智能家庭财务管理工具，帮助追踪收支、管理资产持仓、AI智能分析投资组合

## 1. 不做什么（Non-goals）
- 明确不做：
  - 不支持多银行账户自动同步
  - 不集成第三方支付平台
  - 不处理多币种
- 不在本阶段范围：
  - 贷款管理模块（待 Phase 5）

## 2. 用户与场景
- 核心用户：家庭用户，需要简单记账和收支统计
- 核心场景：
  - 日常记录收入和支出
  - 按分类管理交易（工资、餐饮、交通等）
  - 查看月度收支统计和结余
  - 多用户数据隔离管理
- 成功标准：
  - 界面简洁，用户能快速上手
  - 支持自定义分类
  - 月度统计准确无误

## 3. 约束（硬规则）
- 技术约束：Python 3.8+、Flask、SQLAlchemy、SQLite
- 安全与隐私：密码哈希存储、用户数据隔离
- 性能：SQLite 单机部署，适合家庭使用
- 兼容性：macOS/Linux/Windows、主流浏览器

## 4. 架构快照（保持简短）
- 入口形态：Web 应用（Flask）
- 核心模块：用户认证 → 仪表盘首页 → 月度收支 → 分类管理 → 资产总览 → 储蓄计划 → 智能财务顾问（AI分析+持仓管理） → 数据统计
- 数据流：用户登录 → 首页概览（三模块仪表盘）→ 各子页面详情操作
- 数据库：SQLite 3，包含 users、categories、transactions 等 16 张表

## 5. 当前状态（必须随时更新）
- 当前里程碑：Phase 10 智能财务顾问已完成
- 已可用能力：
  - [x] 用户注册/登录（密码哈希加密）
  - [x] 交易记录（添加、编辑、删除、列表展示）
  - [x] 分类模型支持（系统预设 + 用户自定义）
  - [x] 自定义分类管理界面
  - [x] 月度收支统计
  - [x] 用户数据隔离
  - [x] 家庭共享数据模型 + 管理路由
  - [x] 数据可视化图表（趋势折线图 + 分类饼图 + 首页迷你图）
  - [x] 多账户管理（储蓄/投资，预设 5 种类型 + 自定义）
  - [x] 月度余额快照录入 + 资产趋势图
  - [x] 交易可选关联账户，自动更新余额
  - [x] 储蓄计划管理（月度/年度目标 + 进度追踪 + 手动录入）
  - [x] 宝宝基金记录（自动生成收入交易 + 级联删除 + 编辑联动）
  - [x] CSV/Excel 批量导入（微信/支付宝账单 + 标准模板 + 去重检测）
  - [x] 移动端适配（底部 Tab 栏 + 汉堡侧滑菜单 + 响应式断点）
  - [x] base.html 模板重构（消除 12 个模板的重复代码）
  - [x] Toast 消息提示（成功/错误分类 + 自动消失）
  - [x] 自定义删除确认弹窗
  - [x] 空状态友好提示（4 个页面）
  - [x] 表单提交 loading 防重复
  - [x] 储蓄计划图表（汇总趋势折线图 + 计划迷你图）
  - [x] 快捷模板（常用交易一键填充，按使用频率排序）
  - [x] 定期交易自动生成（月/周/自定义周期，请求触发 + 补漏）
  - [x] 投资账户多币种支持（CNY/HKD/USD + 实时汇率换算）
  - [x] 批量录入快照（全屏模态框表格，所有账户一次性填写）
  - [x] 账户/储蓄/宝宝基金表格式布局（统一排版风格）
  - [x] 储蓄记录独立模块（操作人 + UTC+8 时间）
  - [x] 宝宝基金录入记录（操作人 + UTC+8 时间）
  - [x] 资产总额多币种汇率换算
  - [x] 所有金额千分位逗号格式（Jinja2 currency 过滤器 + JS toLocaleString）
  - [x] 账户列表左右两列精简排版（类型badge + 归属人彩色icon）
  - [x] 首页交易列表分页（每页 10 条）
  - [x] 储蓄计划 / 宝宝基金默认家庭视图（去除个人视图切换）
  - [x] 财务数据隐藏（小眼睛，默认隐藏，所有页面统一）
  - [x] 首页重做为三模块仪表盘（月度收支概览 + 资产总览 + 储蓄计划概览）
  - [x] 月度收支独立页面（/transactions，迁移原首页记账功能）
  - [x] 导航文案更新（资产总览/储蓄计划/管理▾含月度收支）
  - [x] 智能财务顾问模块（5页Tab：总览/股票/基金/理财/储蓄）
  - [x] 股票/基金/理财持仓CRUD管理
  - [x] AI分析引擎（智谱GLM-5-Turbo/GLM-5V-Turbo/GLM-Image全系列）
  - [x] 7个AI分析端点（综合/股票整体+个股/基金整体+个基/理财/储蓄）
  - [x] AI分析右侧抽屉交互 + Markdown渲染 + 缓存+刷新+历史
  - [x] Sina Finance API 实时行情（港股/A股/美股）
  - [x] 资产配置实时聚合分析
  - [x] 基金排序 + 赎回转投操作
  - [x] 财务顾问"我的/家庭"视图切换（与资产总览交互一致）
  - [x] 所有页面页标题 + 金额千分位
  - [x] 持仓批量导入（Excel模板 + App截图AI识别，4种类型）
  - [x] 持仓批量导入（Excel模板 + App截图AI识别，4种类型）
- 已知问题 / 技术债：
  - CSRF 防护缺失（需安装 flask-wtf 改动所有表单，家庭内部使用风险低，后续版本处理）
  - 文件上传缺 MIME 校验（目前仅靠扩展名过滤，后续加 magic bytes 校验）
  - urlopen 汇率 API 无 SSRF 限制（URL 硬编码，当前安全，后续改用 requests 库）
  - 开发模式绑定 0.0.0.0（仅影响本地开发，生产环境 Gunicorn 绑定 127.0.0.1 已安全）

## 6. 下一步 5 件事（只保留 5 条）
1. 贷款管理模块
3. 数据导出功能（CSV/PDF 报表导出）
4. 暗色模式
5. 更多 AI 分析场景（税务优化、退休规划）

## 7. 运行方式（可复制粘贴的命令）
- 本地开发：
  - `pip install -r requirements.txt`
  - `python3 src/main.py`
  - 访问 http://localhost:5001
- 线上地址：
  - http://119.91.205.137
- 服务器更新：
  - `ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137`
  - `sudo -i`
  - `cd /opt/family-finance && git pull origin main && systemctl restart family-finance`

## 8. 关键路径（只列重要的）
- `/src/main.py` - 应用入口，仪表盘首页路由 + 交易增删改路由
- `/src/routes/transaction.py` - 月度收支页路由（记账表单+交易列表+分页）
- `/src/models.py` - 数据模型（User, Category, Transaction, SavingsPlan, BabyFund 等 12 个模型）
- `/src/database.py` - 数据库配置和初始化
- `/src/routes/auth.py` - 认证路由（登录/注册）
- `/src/routes/account.py` - 资产总览路由
- `/src/routes/savings.py` - 储蓄计划路由
- `/src/templates/base.html` - 公共模板（导航、Tab栏、Toast、确认弹窗）
- `/src/templates/index.html` - 首页三模块仪表盘
- `/src/templates/transactions.html` - 月度收支页面
- `/src/static/js/app.js` - 公共交互 JS（菜单、Toast、loading、确认弹窗、小眼睛隐藏）
- `/src/static/css/style.css` - 全局样式（含移动端响应式）
- `/data/family_finance.db` - SQLite 数据库文件
- `/src/routes/advisor.py` - 财务顾问蓝图（持仓CRUD + AI分析 + 历史记录）
- `/src/services/ai_advisor.py` - AI分析引擎（智谱GLM全系列模型）
- `/src/services/market_data.py` - 行情数据服务（Sina Finance API）
- `/src/templates/advisor/` - 财务顾问6个页面模板

## 9. 备注（保持简短）
- 预设分类：工资、奖金（收入）；餐饮、交通（支出）
- 端口：5001（避免与 macOS AirPlay Receiver 冲突）
- 密码存储：使用 pbkdf2:sha256 哈希方法
- 会话管理：基于 Flask session
- 服务器：腾讯云 Lighthouse 广州（119.91.205.137），candyxiao 个人账号
- GitHub 仓库：https://github.com/candyxiao9216/family-finance（private）
