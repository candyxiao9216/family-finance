# 家庭共享功能设计文档

**创建日期:** 2026-02-27
**版本:** 1.0.0
**状态:** 已确认

---

## 1. 概述

### 1.1 目标
将现有严格隔离的用户数据模型改造为家庭内完全共享的数据模型，支持家庭成员间数据共享和协作。

### 1.2 核心功能
- 家庭关系管理（家庭创建、成员加入）
- 数据完全共享（家庭成员可查看/修改所有交易）
- 修改日志追踪（详细记录所有修改操作）
- 视图切换（个人视图/家庭视图）

### 1.3 设计原则
- **简单优先**：先实现核心共享功能，后续根据需求扩展
- **信任基础**：家庭场景下信任度较高，不做复杂权限控制
- **可追溯性**：通过修改日志确保操作可追溯

---

## 2. 数据库设计变更

### 2.1 新增 Family 表
```sql
CREATE TABLE families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '我的家庭',
    invite_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 User 表变更
```sql
ALTER TABLE users ADD COLUMN family_id INTEGER REFERENCES families(id);
```

### 2.3 Transaction 表变更
```sql
ALTER TABLE transactions ADD COLUMN last_modified_by INTEGER REFERENCES users(id);
ALTER TABLE transactions ADD COLUMN last_modified_at TIMESTAMP;
ALTER TABLE transactions ADD COLUMN modification_count INTEGER DEFAULT 0;
```

### 2.4 新增修改日志表
```sql
CREATE TABLE transaction_modifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER REFERENCES transactions(id),
    modified_by INTEGER REFERENCES users(id),
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    field_name TEXT NOT NULL,      -- 'amount', 'description', 'category_id'
    old_value TEXT,                -- 修改前的值
    new_value TEXT                 -- 修改后的值
);
```

---

## 3. 核心业务流程

### 3.1 家庭创建流程
```
用户注册 → 检查是否第一个用户 → 创建家庭 → 生成邀请码 → 关联用户到家庭
```

### 3.2 成员加入流程
```
用户注册 → 输入邀请码 → 验证邀请码 → 关联用户到家庭 → 显示欢迎信息
```

### 3.3 交易修改流程
```
用户修改交易 → 验证权限 → 更新交易数据 → 记录修改日志 → 返回成功
```

### 3.4 数据查询流程
```
用户访问首页 → 检查视图参数 → 查询对应数据 → 渲染页面
```

---

## 4. API 路由设计

### 4.1 新增路由
| 路由 | 方法 | 功能 |
|------|------|------|
| `/family/invite` | GET | 获取家庭邀请码 |
| `/family/join` | POST | 加入家庭 |
| `/family/members` | GET | 查看家庭成员 |

### 4.2 修改现有路由
| 路由 | 变更 |
|------|------|
| `/` | 支持 `?view=personal` 和 `?view=family` 参数 |
| `/add` | 交易自动关联到当前用户，但家庭视图可修改他人交易 |
| `/delete/<id>` | 可删除家庭内任何交易 |
| `/edit/<id>` | 可编辑家庭内任何交易 |

---

## 5. 前端界面设计

### 5.1 首页视图切换
```html
<!-- 视图切换按钮 -->
<div class="view-toggle">
    <a href="/?view=personal" class="btn">👤 个人视图</a>
    <a href="/?view=family" class="btn">🏠 家庭视图</a>
</div>
```

### 5.2 交易列表显示修改信息
```html
<!-- 交易项 -->
<div class="transaction-item">
    <span class="amount">¥150.00</span>
    <span class="description">午餐</span>
    <span class="modified-by">由 张三 修改</span>
    <span class="modified-time">2小时前</span>
</div>
```

### 5.3 邀请码显示
```html
<!-- 家庭信息栏 -->
<div class="family-info">
    <h3>我的家庭</h3>
    <p>邀请码：<code>FAMILY-ABCD</code></p>
    <button onclick="copyInviteCode()">复制邀请码</button>
</div>
```

---

## 6. 数据查询逻辑

### 6.1 个人视图查询
```python
# 查询当前用户的交易
transactions = Transaction.query.filter_by(user_id=current_user.id).all()
```

### 6.2 家庭视图查询
```python
# 查询家庭内所有交易
transactions = Transaction.query.join(User).filter(
    User.family_id == current_user.family_id
).all()
```

### 6.3 分类查询（共享）
```python
# 查询家庭内可用的分类
categories = Category.query.filter(
    (Category.user_id == None) |  # 系统预设
    (Category.user_id.in_(family_user_ids))  # 家庭成员自定义
).all()
```

---

## 7. 修改日志实现

### 7.1 修改记录函数
```python
def log_transaction_modification(transaction_id, modified_by, field_name, old_value, new_value):
    modification = TransactionModification(
        transaction_id=transaction_id,
        modified_by=modified_by,
        field_name=field_name,
        old_value=str(old_value),
        new_value=str(new_value)
    )
    db.session.add(modification)
```

### 7.2 交易更新函数
```python
def update_transaction(transaction_id, updates):
    transaction = Transaction.query.get(transaction_id)

    # 记录每个字段的修改
    for field, new_value in updates.items():
        old_value = getattr(transaction, field)
        if old_value != new_value:
            log_transaction_modification(transaction_id, current_user.id, field, old_value, new_value)
            setattr(transaction, field, new_value)

    # 更新修改追踪字段
    transaction.last_modified_by = current_user.id
    transaction.last_modified_at = datetime.utcnow()
    transaction.modification_count += 1

    db.session.commit()
```

---

## 8. 家庭邀请码管理

### 8.1 邀请码生成
```python
def generate_invite_code():
    import random
    import string
    prefix = "FAMILY-"
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return prefix + suffix
```

### 8.2 邀请码验证
```python
def join_family(invite_code):
    family = Family.query.filter_by(invite_code=invite_code).first()
    if not family:
        return False, "邀请码无效"

    current_user.family_id = family.id
    db.session.commit()
    return True, f"成功加入 {family.name}"
```

---

## 9. 迁移策略

### 9.1 数据迁移脚本
```python
def migrate_to_family_model():
    # 1. 创建家庭表
    # 2. 为现有用户创建默认家庭
    # 3. 更新现有交易的 user_id 为家庭内用户
    # 4. 添加修改追踪字段
    # 5. 创建修改日志表
```

### 9.2 向后兼容
- 现有数据自动迁移到新模型
- 未加入家庭的用户继续使用个人模式
- 逐步过渡到家庭共享模式

---

## 10. 验收标准

### 家庭管理
- [ ] 第一个用户注册时自动创建家庭
- [ ] 首页显示家庭邀请码
- [ ] 其他用户可通过邀请码加入家庭
- [ ] 家庭成员列表显示正确

### 数据共享
- [ ] 个人视图只显示自己的交易
- [ ] 家庭视图显示所有家庭成员交易
- [ ] 任何家庭成员可修改任何交易
- [ ] 修改后显示修改者和时间

### 修改日志
- [ ] 每次修改记录详细变更
- [ ] 修改历史可查询
- [ ] 修改计数正确更新

### 视图切换
- [ ] URL 参数正确切换视图
- [ ] 视图状态在页面刷新后保持
- [ ] 统计信息按视图正确计算

---

## 11. 后续扩展方向

### 短期扩展
- 家庭成员角色管理（管理员/普通成员）
- 修改审批流程
- 交易评论功能

### 长期扩展
- 多家庭支持（用户可加入多个家庭）
- 家庭间数据对比
- 高级权限控制

---

**文档状态:** 已确认，等待实施