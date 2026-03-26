# 项目简报（Project Brief）

## 0. 一句话目标
- 目标：构建一个简洁、温暖的家庭财务管理工具，帮助追踪收支、管理分类、统计月度数据

## 1. 不做什么（Non-goals）
- 明确不做：
  - 不支持多银行账户自动同步
  - 不提供复杂的投资分析功能
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
- 核心模块：用户认证 → 交易记录 → 分类管理 → 数据统计
- 数据流：用户登录 → 录入交易 → 关联分类 → 统计展示
- 数据库：SQLite 3，包含 users、categories、transactions 三张表

## 5. 当前状态（必须随时更新）
- 当前里程碑：Phase 4 UI 优化已完成
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
- 已知问题 / 技术债：
  - 无重大已知问题

## 6. 下一步 5 件事（只保留 5 条）
1. 贷款管理模块
2. 储蓄计划页面图表（储蓄趋势折线图）
3. 导入功能优化（支持更多银行账单格式）
4. 数据导出功能（CSV/PDF 报表导出）
5. 暗色模式

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
- `/src/main.py` - 应用入口，主路由
- `/src/models.py` - 数据模型（User, Category, Transaction, SavingsPlan, BabyFund 等 12 个模型）
- `/src/database.py` - 数据库配置和初始化
- `/src/routes/auth.py` - 认证路由（登录/注册）
- `/src/templates/base.html` - 公共模板（导航、Tab栏、Toast、确认弹窗）
- `/src/templates/auth_base.html` - 认证页公共模板
- `/src/static/js/app.js` - 公共交互 JS（菜单、Toast、loading、确认弹窗）
- `/src/static/css/style.css` - 全局样式（含移动端响应式）
- `/data/family_finance.db` - SQLite 数据库文件

## 9. 备注（保持简短）
- 预设分类：工资、奖金（收入）；餐饮、交通（支出）
- 端口：5001（避免与 macOS AirPlay Receiver 冲突）
- 密码存储：使用 pbkdf2:sha256 哈希方法
- 会话管理：基于 Flask session
- 服务器：腾讯云 Lighthouse 广州（119.91.205.137），candyxiao 个人账号
- GitHub 仓库：https://github.com/candyxiao9216/family-finance（private）
