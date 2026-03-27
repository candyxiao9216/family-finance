# 快捷记账功能设计文档

## 目标

减少日常记账操作步骤：常用交易一键录入，固定支出自动生成。

## 不做的事

- 不做复杂的 cron 调度器（用请求触发代替）
- 不做提醒通知（邮件/推送）
- 不做模板分享（家庭成员间）

---

## 一、常用交易模板

### 数据模型

新增 `TransactionTemplate` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK(users) | 所属用户 |
| name | VARCHAR(50) | 模板名称（如"午餐"） |
| amount | DECIMAL(10,2) | 金额 |
| type | VARCHAR(10) | income / expense |
| category_id | INTEGER FK(categories) | 分类 |
| description | TEXT | 备注（可选） |
| account_id | INTEGER FK(accounts) | 关联账户（可选） |
| use_count | INTEGER DEFAULT 0 | 使用次数（用于排序） |
| created_at | DATETIME | 创建时间 |

### 交互流程

**创建模板（两种方式）：**
1. 首页「添加交易」表单旁新增「保存为模板」按钮 — 填完表单后点击，弹出输入模板名称
2. 设置 → 新增「快捷模板」管理页面 — 手动创建/编辑/删除模板

**使用模板：**
- 首页「添加交易」区域上方显示常用模板按钮（按使用次数排序，最多显示 6 个）
- 点击模板按钮 → 自动填充金额、类型、分类、描述、账户到表单
- 用户可微调后提交，或直接提交
- 提交后 `use_count += 1`

### 模板管理页面

在导航栏「设置 ▾」下拉菜单中新增「快捷模板」入口，页面包含：
- 模板列表（名称、金额、分类、使用次数）
- 添加/编辑/删除操作

---

## 二、定期交易自动生成

### 数据模型

新增 `RecurringTransaction` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | INTEGER FK(users) | 所属用户 |
| name | VARCHAR(100) | 名称（如"房租"） |
| amount | DECIMAL(10,2) | 金额 |
| type | VARCHAR(10) | income / expense |
| category_id | INTEGER FK(categories) | 分类 |
| description | TEXT | 备注（可选） |
| account_id | INTEGER FK(accounts) | 关联账户（可选） |
| frequency | VARCHAR(20) | 周期：monthly / weekly / custom |
| interval_days | INTEGER | 自定义天数（frequency=custom 时） |
| day_of_month | INTEGER | 每月几号执行（frequency=monthly 时，1-28） |
| day_of_week | INTEGER | 每周几执行（frequency=weekly 时，0-6） |
| next_run_date | DATE | 下次执行日期 |
| is_active | BOOLEAN DEFAULT 1 | 是否启用 |
| created_at | DATETIME | 创建时间 |

### 自动执行机制

**触发方式：** 每次用户访问首页时，检查是否有到期的定期交易。

```python
# 在首页路由中调用
def process_recurring_transactions(user_id):
    today = date.today()
    due_items = RecurringTransaction.query.filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_run_date <= today
    ).all()

    for item in due_items:
        # 创建交易记录
        create_transaction_from_recurring(item)
        # 计算下次执行日期
        item.next_run_date = calculate_next_run(item)

    db.session.commit()
```

**补漏机制：** 如果用户几天没登录，到期的定期交易会在下次登录时全部补上（每个到期日各生成一条）。

### 管理页面

在导航栏「设置 ▾」下拉菜单中新增「定期交易」入口，页面包含：
- 定期交易列表（名称、金额、周期、下次执行日期、状态开关）
- 添加/编辑/删除/暂停/恢复操作

---

## 三、文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `src/models.py` | 新增 TransactionTemplate + RecurringTransaction 模型 |
| 新建 | `src/routes/template.py` | 模板 CRUD 路由 |
| 新建 | `src/routes/recurring.py` | 定期交易 CRUD + 自动执行路由 |
| 新建 | `src/templates/templates.html` | 快捷模板管理页面 |
| 新建 | `src/templates/recurring.html` | 定期交易管理页面 |
| 修改 | `src/templates/index.html` | 添加模板快捷按钮区域 |
| 修改 | `src/templates/base.html` | 导航「设置 ▾」增加两个入口 |
| 修改 | `src/main.py` | 注册新蓝图 + 首页调用定期交易处理 |
| 修改 | `src/database.py` | 初始化新表 |

---

## 四、测试验证

- 模板 CRUD：创建、编辑、删除、使用次数递增
- 模板填充：点击模板后表单字段正确填充
- 定期交易：创建后下次执行日期正确计算
- 自动执行：到期时自动创建交易记录
- 补漏：多天未登录后补上所有遗漏的交易
- 暂停/恢复：暂停后不再自动执行，恢复后继续
