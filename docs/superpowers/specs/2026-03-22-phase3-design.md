# Phase 3 设计文档：储蓄计划 + 宝宝基金 + 批量导入

**日期：** 2026-03-22
**状态：** 审查通过（v2）
**范围：** 三个功能同步设计、按独立蓝图实施

---

## 1. 概述

Phase 3 为家庭财务管理系统新增三个功能模块：

| 模块 | 目标 |
|------|------|
| **储蓄计划** | 创建月度/年度储蓄目标，手动录入储蓄记录，自动计算进度 |
| **宝宝基金** | 记录宝宝收到的红包/礼金，入账时自动生成收入交易 |
| **批量导入** | 支持微信/支付宝账单和标准模板 CSV/Excel 导入，交互式去重 |

**不在范围内：**
- 银行流水自动同步
- 贷款管理模块
- 移动端适配（留到 Phase 4）

---

## 2. 数据模型

### 2.1 新增表：`savings_plans`（储蓄计划）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| name | VARCHAR(100) | NOT NULL | 计划名称 |
| type | VARCHAR(10) | NOT NULL | `'monthly'` 或 `'annual'` |
| target_amount | DECIMAL(10,2) | NOT NULL | 目标金额 |
| year | INTEGER | NOT NULL | 年份 |
| month | INTEGER | NULLABLE | 月份（仅月度计划） |
| created_by | INTEGER | FK → users.id | 创建人 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**业务规则：**
- 月度计划：`month` 必填（1-12），进度 = 该月所有 savings_records 的 amount 之和 / target_amount
- 年度计划：`month` 为空（后端强制置 NULL），进度 = 该年所有 savings_records 的 amount 之和 / target_amount
- 验证规则：`month` 仅接受 1-12，年度计划时后端忽略前端传入的 month 值

**家庭视图逻辑：**
- 个人视图：只显示 `created_by = 当前用户` 的计划
- 家庭视图：显示所有家庭成员创建的计划（`SavingsPlan.created_by.in_(family_member_ids)`）
- 家庭视图下，进度聚合所有家庭成员在该计划下的储蓄记录

### 2.2 新增表：`savings_records`（储蓄记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| plan_id | INTEGER | FK → savings_plans.id, NOT NULL | 关联计划 |
| user_id | INTEGER | FK → users.id, NOT NULL | 录入人 |
| amount | DECIMAL(10,2) | NOT NULL | 储蓄金额 |
| account_id | INTEGER | FK → accounts.id, NULLABLE | 存入账户 |
| record_date | DATE | NOT NULL | 储蓄日期 |
| description | TEXT | NULLABLE | 备注 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

### 2.3 新增表：`baby_funds`（宝宝基金）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| giver_name | VARCHAR(50) | NOT NULL | 给钱的人 |
| amount | DECIMAL(10,2) | NOT NULL | 金额 |
| account_id | INTEGER | FK → accounts.id, NULLABLE | 存入账户 |
| event_date | DATE | NOT NULL | 日期 |
| event_type | VARCHAR(20) | NULLABLE | 事件类型，限定值：`满月`/`生日`/`红包`/`其他` |
| notes | TEXT | NULLABLE | 备注 |
| transaction_id | INTEGER | FK → transactions.id, NULLABLE | 关联自动生成的交易 |
| created_by | INTEGER | FK → users.id | 创建人 |
| created_at | DATETIME | DEFAULT now | 创建时间 |

**业务规则：**
- 创建宝宝基金记录时，自动创建一笔收入类型的 Transaction（description 包含给钱人和事件类型）
- `transaction_id` 存储关联交易的 ID
- 删除宝宝基金时：先删除关联交易的 `TransactionModification` 记录（如有），再删除 `Transaction`，最后删除 `BabyFund`
- `event_type` 校验：模型层定义 `VALID_EVENT_TYPES = ['满月', '生日', '红包', '其他']`，路由层做校验

**家庭视图逻辑：**
- 宝宝基金默认展示当前用户家庭的所有记录（`BabyFund.created_by.in_(family_member_ids)`）
- 支持个人/家庭视图切换

### 2.4 新增表：`import_records`（导入记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| user_id | INTEGER | FK → users.id, NOT NULL | 导入人 |
| file_name | VARCHAR(200) | NOT NULL | 文件名 |
| import_time | DATETIME | DEFAULT now | 导入时间 |
| total_rows | INTEGER | NULLABLE | 文件总行数 |
| imported_count | INTEGER | NULLABLE | 成功导入数 |
| skipped_count | INTEGER | NULLABLE | 跳过数 |
| duplicate_count | INTEGER | NULLABLE | 重复数 |
| source_type | VARCHAR(20) | NULLABLE | `'wechat'`/`'alipay'`/`'template'` |
| status | VARCHAR(20) | DEFAULT 'completed' | `'completed'`/`'partial'`/`'failed'` |

### 2.5 现有表不做修改

`transactions` 表不新增字段。去重逻辑优先使用微信/支付宝账单中的交易单号，回退到 `transaction_date + amount + description` 组合比对。详见第 5.4 节。

---

## 3. API 路由设计

### 3.1 储蓄计划蓝图 `savings_bp`（prefix: `/savings`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/savings` | GET | 储蓄计划列表页（含进度计算） |
| `/savings/plan/add` | POST | 创建储蓄计划 |
| `/savings/plan/<id>/delete` | POST | 删除储蓄计划（级联删除关联记录） |
| `/savings/plan/<id>/edit` | POST | 编辑储蓄计划（修改名称、目标金额等） |
| `/savings/record/add` | POST | 录入储蓄记录 |
| `/savings/record/<id>/delete` | POST | 删除储蓄记录 |

### 3.2 宝宝基金蓝图 `baby_fund_bp`（prefix: `/baby-fund`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/baby-fund` | GET | 宝宝基金列表页 |
| `/baby-fund/add` | POST | 添加宝宝基金（同时创建交易） |
| `/baby-fund/<id>/edit` | POST | 编辑宝宝基金记录 |
| `/baby-fund/<id>/delete` | POST | 删除宝宝基金（同时删除交易） |

### 3.3 批量导入蓝图 `upload_bp`（prefix: `/upload`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/upload` | GET | 导入页面（含导入历史） |
| `/upload/parse` | POST | 解析上传文件，返回预览数据（JSON） |
| `/upload/confirm` | POST | 确认导入，处理重复项 |
| `/upload/template` | GET | 下载标准导入模板 CSV |

---

## 4. 页面设计

### 4.1 储蓄计划页（卡片式布局）

**结构：**
1. **顶部统计栏：** 年度目标总额、已储蓄总额、完成率
2. **计划卡片列表：** 每个计划独立卡片，包含：
   - 计划名 + 目标金额
   - 进度条（已储蓄/目标）
   - 百分比数字
3. **操作按钮：** 「+ 创建储蓄计划」「+ 录入储蓄」（抽屉浮层表单，与账户管理页风格一致）
4. **视图切换：** 支持个人/家庭视图

**表单字段：**
- 创建计划：名称、类型（月度/年度）、目标金额、年份、月份
- 录入储蓄：选择计划、金额、日期、备注

### 4.2 宝宝基金页

**结构：**
1. **顶部统计栏：** 基金总额、记录数
2. **记录列表：** 每笔记录显示给钱人、事件类型图标、金额、日期
3. **操作按钮：** 「+ 记录宝宝基金」（抽屉浮层表单）

**表单字段：**
- 给钱人、金额、存入账户（下拉选择）、日期、事件类型（满月/生日/红包/其他）、备注

### 4.3 批量导入页（三步流程）

**步骤 1 — 上传：**
- 拖拽上传区域
- 文件类型选择按钮（微信账单 / 支付宝账单 / 标准模板）
- 下载标准模板链接

**步骤 2 — 预览确认：**
- 解析结果表格预览（前 20 条）
- 统计信息：总行数、有效行数、重复行数
- 重复项高亮显示 + 单条操作（跳过/覆盖/保留两条）
- 批量操作：全部跳过 / 全部覆盖

**步骤 3 — 导入结果：**
- 成功/失败统计
- 导入详情列表

**底部：** 导入历史记录列表

---

## 5. 文件解析逻辑

### 5.1 微信账单格式

微信导出的 CSV 特点：
- 前 16 行为账单概要信息，需跳过
- 数据列：交易时间、交易类型、交易对方、商品、收/支、金额(元)、支付方式、当前状态、交易单号、商户单号、备注
- 金额带 `¥` 符号，需清洗
- 收/支列：`收入`、`支出`、`/`（不计收支）

### 5.2 支付宝账单格式

支付宝导出的 CSV 特点：
- 前几行为账单信息头，需跳过（检测到列名行开始解析）
- 数据列：交易时间、交易分类、交易对方、对方账号、商品说明、收/支、金额、收/付款方式、交易状态、交易订单号、商家订单号、备注
- 金额为纯数字
- 收/支列：`收入`、`支出`

### 5.3 标准模板格式

用户按模板整理的 CSV/Excel：
- 列：日期、类型（收入/支出）、金额、分类、描述
- 无需特殊清洗

### 5.4 去重逻辑

**优先使用交易单号去重（微信/支付宝账单）：**
- 微信账单：使用"交易单号"字段
- 支付宝账单：使用"交易订单号"字段
- 解析时将订单号存入 Transaction 的 `description` 字段末尾（格式：`原描述 [单号:xxx]`）
- 去重时先提取订单号匹配

**回退方案（标准模板或无单号时）：**
- 基于 `transaction_date + amount + description` 组合
- `description` 为 NULL 时视为空字符串参与比对
- 完全相同的合法交易会被标记为"疑似重复"，由用户手动确认

**去重流程：**
1. 解析文件后，对每条记录生成去重键
2. 查询数据库中当前用户近 6 个月的交易（避免全表扫描），生成去重键集合
3. 比对找出重复项
4. 前端展示重复项，用户交互式选择：跳过 / 覆盖 / 保留两条

---

## 5.5 导入状态管理

**parse 和 confirm 之间的数据流：**
- `/upload/parse` 解析文件后，将全量解析结果作为 JSON 返回给前端
- 前端在内存中持有解析数据，展示预览表格
- 用户在前端完成重复项决策后，`/upload/confirm` 提交最终确认的记录列表（JSON body）
- 后端接收记录列表，逐条写入数据库

**文件大小和安全限制：**
- 最大文件大小：10MB
- 仅接受 `.csv` 和 `.xlsx` 后缀
- CSV 内容安全清洗：去除以 `=`, `+`, `-`, `@` 开头的单元格内容（防止 CSV 注入）
- Flask 配置：`MAX_CONTENT_LENGTH = 10 * 1024 * 1024`

---

## 5.6 分类映射逻辑

**导入时如何确定交易分类：**
1. **标准模板：** 用户在模板中填写分类名，按名称精确匹配系统 `categories` 表
2. **微信/支付宝账单：** 原始账单的"交易分类"字段做模糊匹配：
   - 包含"餐饮/美食"→ 匹配系统"餐饮"分类
   - 包含"交通/出行"→ 匹配系统"交通"分类
   - 无法匹配时设为 `NULL`（未分类）
3. **预览页允许用户手动调整：** 每条记录旁显示分类下拉框，用户可修改

---

## 6. 导航整合

在首页 header 的 `user-actions` 区域新增三个导航链接：

```
首页 | 分类 | 报表 | 账户 | 储蓄 | 宝宝 | 导入 | 家庭 | 退出
```

各子页面的 header 也同步更新导航链接。

---

## 7. 新增文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/routes/savings.py` | 路由 | 储蓄计划蓝图 |
| `src/routes/baby_fund.py` | 路由 | 宝宝基金蓝图 |
| `src/routes/upload.py` | 路由 | 批量导入蓝图 |
| `src/utils/importers.py` | 工具 | 微信/支付宝/模板文件解析器 |
| `src/templates/savings.html` | 模板 | 储蓄计划页面 |
| `src/templates/baby_fund.html` | 模板 | 宝宝基金页面 |
| `src/templates/upload.html` | 模板 | 批量导入页面 |
| `src/static/import_template.csv` | 静态 | 标准导入模板文件 |
| `tests/test_savings.py` | 测试 | 储蓄计划单元测试 |
| `tests/test_baby_fund.py` | 测试 | 宝宝基金单元测试 |
| `tests/test_upload.py` | 测试 | 批量导入单元测试 |
| `tests/test_importers.py` | 测试 | 文件解析器单元测试 |

**修改文件：**

| 文件 | 修改内容 |
|------|---------|
| `src/models.py` | 新增 SavingsPlan、SavingsRecord、BabyFund、ImportRecord 模型 |
| `src/database.py` | 新增表的创建逻辑 |
| `src/main.py` | 注册三个新蓝图 |
| `src/templates/index.html` | header 添加导航链接 |
| `src/templates/accounts.html` | header 添加导航链接 |
| `src/templates/reports.html` | header 添加导航链接 |
| `src/templates/categories.html` | header 添加导航链接 |
| `src/static/css/style.css` | 新增储蓄/宝宝基金/导入页面样式 |
| `requirements.txt` | 添加 openpyxl（Excel 支持） |

---

## 8. 验收标准

### 储蓄计划
- [ ] 可创建月度/年度储蓄计划
- [ ] 可录入储蓄记录，关联到指定计划
- [ ] 进度条正确显示（已储蓄/目标）
- [ ] 支持个人/家庭视图切换
- [ ] 可删除计划（级联删除记录）

### 宝宝基金
- [ ] 可添加宝宝基金记录
- [ ] 入账时自动生成一笔收入交易
- [ ] 删除时同步删除关联交易
- [ ] 统计栏显示正确的总额和记录数

### 批量导入
- [ ] 可上传微信账单 CSV 并正确解析
- [ ] 可上传支付宝账单 CSV 并正确解析
- [ ] 可上传标准模板 CSV/Excel 并正确解析
- [ ] 预览页正确显示解析结果
- [ ] 重复项检测正确，支持交互式处理
- [ ] 导入记录表正确记录每次导入的统计信息
- [ ] 可下载标准导入模板

---

## 9. 模型规范

所有新增模型必须遵循现有代码风格：
- 实现 `__repr__()` 方法
- 实现 `to_dict()` 方法
- 定义必要的 relationship 和 backref
- `BabyFund` 模型定义常量：`VALID_EVENT_TYPES = ['满月', '生日', '红包', '其他']`
