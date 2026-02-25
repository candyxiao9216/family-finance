# 家庭财务管理系统 MVP 第一阶段设计文档

**创建日期:** 2026-02-26
**版本:** 1.0.0
**状态:** 已确认

---

## 1. 概述

### 1.1 目标
实现最小可用产品（MVP），验证核心交易录入功能，为后续迭代奠定基础。

### 1.2 范围
- 收入/支出交易录入
- 交易记录列表展示
- 删除交易功能
- 基础统计展示（月度收/支/结余）

### 1.3 不包含
- 用户登录认证
- 自定义分类管理
- CSV/Excel 导入
- 银行流水同步
- 高级数据可视化

---

## 2. 技术架构

| 组件 | 技术选择 |
|------|---------|
| 后端框架 | Flask 3.x |
| 数据库 ORM | SQLAlchemy 2.x |
| 数据库 | SQLite (single file) |
| 前端样式 | 自定义 CSS (无框架) |
| 字体 | Noto Serif SC + Outfit (Google Fonts) |

---

## 3. 数据库设计

### 3.1 表结构

#### categories - 交易分类表
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,                  -- 'income' 或 'expense'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**预设分类：**
| id | name | type |
|----|------|------|
| 1 | 工资 | income |
| 2 | 奖金 | income |
| 3 | 餐饮 | expense |
| 4 | 交通 | expense |

#### transactions - 交易记录表
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount DECIMAL(10,2) NOT NULL,
    type TEXT NOT NULL,                  -- 'income' 或 'expense'
    category_id INTEGER REFERENCES categories(id),
    description TEXT,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 目录结构

```
0225-FamilyFinance/
├── requirements.txt                    # Python 依赖
├── src/
│   ├── main.py                         # Flask 入口
│   ├── config.py                       # 数据库配置
│   ├── database.py                     # 数据库初始化
│   ├── models.py                       # SQLAlchemy 模型
│   ├── static/
│   │   └── css/
│   │       └── style.css               # 前端样式
│   └── templates/
│       └── index.html                  # 主页面模板
└── data/
    └── family_finance.db               # SQLite 数据库
```

---

## 5. API 路由设计

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页 - 交易列表 |
| `/add` | POST | 添加交易 |
| `/delete/<id>` | POST | 删除交易 |
| `/init-db` | GET | 初始化数据库（预设分类） |

---

## 6. 前端设计

### 6.1 视觉风格
- **风格**: 柔软现代 (Soft Minimal with Warmth)
- **背景**: 温暖奶油白 (#F9F7F4)
- **收入色**: 琥珀金 (#D4A574)
- **支出色**: 靛蓝 (#7C8BA1)
- **强调色**: 珊瑚橙 (#E8998D)
- **字体**: Noto Serif SC (标题) + Outfit (正文)

### 6.2 页面布局
```
┌─────────────────────────────────────┐
│  家庭财务          2026年2月26日... │
├─────────────────────────────────────┤
│  [本月收入][本月支出][结余]          │
├─────────────────────────────────────┤
│  添加交易                            │
│  ┌─────────────────────────────┐    │
│  │ [收入][支出]                │    │
│  │ 金额 [__] 分类 [下拉]        │    │
│  │ 日期 [日期框] 备注 [__]     │    │
│  │        [添加记录按钮]        │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  近期交易                            │
│  ┌─────────────────────────────┐    │
│  │ 图 | 描述 - 分类 - 日期 | 金额│    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### 6.3 动效
- 列表载入：错滑进入（staggered）
- 卡片悬停：轻微上浮 + 阴影加深
- 删除按钮：悬停时显示

---

## 7. 数据模型

### Transaction 模型
```python
class Transaction(Base):
    __tablename__ = 'transactions'

    id: int
    amount: Decimal          # 交易金额
    type: str                # 'income' 或 'expense'
    category_id: int         # 分类ID
    category: Category       # 关联分类对象
    description: str         # 描述
    transaction_date: date   # 交易日期
    created_at: datetime     # 创建时间
```

### Category 模型
```python
class Category(Base):
    __tablename__ = 'categories'

    id: int
    name: str                # 分类名称
    type: str                # 'income' 或 'expense'
    created_at: datetime
```

---

## 8. 核心逻辑

### 8.1 添加交易
1. 验证表单数据（金额必填、日期必填）
2. 创建 Transaction 对象
3. 提交到数据库
4. 重定向到首页

### 8.2 删除交易
1. 根据ID查询交易
2. 删除记录
3. 重定向到首页

### 8.3 获取交易列表
1. 按日期降序查询所有交易
2. 关联分类信息
3. 渲染模板

### 8.4 初始化数据库
1. 创建所有表
2. 插入4个预设分类
3. 跳过已存在记录（幂等）

---

## 9. 依赖清单

```
flask==3.0.0
flask-sqlalchemy==3.1.1
python-dotenv==1.0.0
```

---

## 10. 验收标准

- [ ] 可以打开首页 `/`，看到页面正常加载
- [ ] 可以添加收入/支出交易，记录保存成功
- [ ] 交易列表显示所有记录，按日期倒序
- [ ] 可以删除交易记录
- [ ] 统计栏显示本月收入/支出/结余
- [ ] 页面样式符合设计稿
- [ ] 移动端响应式正常

---

## 11. 后续迭代方向

### 第二阶段
- 用户登录认证
- 自定义分类管理

### 第三阶段
- CSV/Excel 批量导入
- 账户余额追踪
- 储蓄计划管理

### 第四阶段
- 月度趋势图表
- 图表数据可视化

---

**文档状态:** 已确认，等待实施
