# 任务清单（Tasks）

> 规则：这是"任务索引"，不要写长篇设计文档。
> 每个任务最好控制在 30–90 分钟可完成；如果更大，先拆分。

## 字段说明
- 状态：TODO / DOING / BLOCKED / DONE
- 优先级：P0 / P1 / P2
- 规模：S（≤30m）/ M（30–90m）/ L（需要先拆分）

---

## 当前里程碑：Phase 1 - 核心功能完善（2026-02-27）

### TASK-001：修复分类下拉框硬编码问题
- 状态：TODO
- 优先级：P0
- 规模：S
- 目标（一句话）：分类选项从后端动态获取，而非模板硬编码
- 验收标准：
  - [ ] index.html 中分类 select 动态渲染 categories 数据
  - [ ] 支持新增自定义分类后自动显示
  - [ ] 按类型（收入/支出）分组显示
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

### TASK-003：家庭管理路由实现
- 状态：TODO
- 优先级：P0
- 规模：M
- 目标（一句话）：实现家庭创建、加入、成员管理路由
- 验收标准：
  - [ ] 家庭创建路由（第一个用户自动创建）
  - [ ] 家庭加入路由（邀请码验证）
  - [ ] 家庭成员列表路由
  - [ ] 邀请码管理路由
- 涉及文件/目录：
  - `/src/routes/family.py`
  - `/src/templates/family/`
  - `/src/main.py`（路由注册）
- 依赖：TASK-002
- 备注：基于已完成的 Family 数据模型

---

## 待办池（Phase 2 - 扩展功能）

### TASK-003：交易编辑功能
- 状态：TODO
- 优先级：P1
- 规模：M
- 目标（一句话）：支持编辑已有交易记录
- 验收标准：
  - [ ] 交易列表显示编辑按钮
  - [ ] 点击编辑显示编辑表单（预填充现有数据）
  - [ ] 提交更新数据库记录
- 涉及文件/目录：
  - `/src/main.py` 或 `/src/routes/transaction.py`
  - `/src/templates/edit_transaction.html`
- 依赖：TASK-001

### TASK-004：自定义分类管理
- 状态：TODO
- 优先级：P1
- 规模：M
- 目标（一句话）：添加分类管理界面，支持添加/删除用户自定义分类
- 验收标准：
  - [ ] 创建分类管理页面
  - [ ] 显示系统默认分类和用户自定义分类
  - [ ] 支持添加新分类（收入/支出类型）
  - [ ] 支持删除用户自定义分类
- 涉及文件/目录：
  - `/src/main.py` 或 `/src/routes/category.py`
  - `/src/templates/categories.html`
- 依赖：TASK-002

### TASK-005：数据可视化图表
- 状态：TODO
- 优先级：P1
- 规模：M
- 目标（一句话）：使用 Chart.js 添加收支统计图表
- 验收标准：
  - [ ] 月度收支趋势折线图
  - [ ] 分类支出饼图
- 涉及文件/目录：
  - `/src/main.py`
  - `/src/templates/index.html`
- 依赖：无

### TASK-006：账户余额追踪
- 状态：TODO
- 优先级：P2
- 规模：L（需拆分）
- 目标（一句话）：支持多账户管理和余额记录
- 涉及文件/目录：
  - `/src/models.py`
  - `/src/routes/account.py`
  - `/src/templates/accounts.html`
- 依赖：TASK-005

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
