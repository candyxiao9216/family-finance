# UI 体验优化设计文档

## 目标

优化家庭财务管理系统的 UI 体验，涵盖移动端适配、模板重构和交互细节三个方面，使应用在手机和桌面上都好用。

## 不做的事

- 暗色模式
- 打印样式
- 高对比度模式
- CSS 框架迁移（保持原生 CSS）

---

## 一、移动端适配

### 1.1 混合导航（底部 Tab + 顶部汉堡）

**桌面端（≥768px）：** 保持现有顶部二级下拉导航，不变。

**移动端（<768px）：** 隐藏顶部导航链接，改为：

- **顶部栏：** Logo + 页面标题 + 汉堡菜单按钮（☰）
- **底部 Tab 栏：** 固定在底部，4 个高频入口
  - 🏠 首页 → `/`
  - 💳 账户 → `/accounts`
  - 📊 报表 → `/reports`
  - ⚙️ 更多 → 展开汉堡菜单
- **汉堡菜单：** 点击 ☰ 或「更多」时，侧滑弹出全屏菜单
  - 一级项：首页、账户管理、储蓄计划、宝宝基金、报表、分类管理、批量导入
  - 底部：家庭信息、退出登录
  - 点击遮罩层或 ✕ 关闭

**实现方式：**
- 汉堡菜单用 JS 控制 `.open` 类切换显示/隐藏
- 底部 Tab 用 `position: fixed; bottom: 0` 固定，高度 60px
- `<main>` 元素在移动端添加 `padding-bottom: 70px` 避免内容被 Tab 栏遮挡
- **Tab 高亮逻辑：** 在 Jinja2 中基于 `request.path` 注入 `active` class
  - 首页：`request.path == '/'`
  - 账户：`request.path.startswith('/accounts')`
  - 报表：`request.path.startswith('/reports')`
  - 更多：当前页面属于储蓄计划、宝宝基金、分类管理、批量导入时高亮

### 1.2 断点补齐

废弃原有 640px 断点，统一使用新的断点体系：

| 断点 | 用途 |
|------|------|
| <768px | 手机：单列布局、底部 Tab、汉堡菜单 |
| 768px-1024px | 平板：2 列网格、顶部导航 |
| ≥1024px | 桌面：保持现有布局 |

### 1.3 触摸友好

- 所有可点击元素最小尺寸 44px × 44px
- 交易项的编辑/删除按钮在移动端加大点击区域
- 表单输入框高度 ≥ 48px

### 1.4 表格响应式

交易列表在 <768px 时：
- 隐藏「来源」「创建人」列
- 金额和操作按钮保持可见
- 描述文字自动截断（ellipsis）

其他列表页面（宝宝基金、储蓄记录等）暂不单独处理表格响应式，保持默认单列堆叠即可。

---

## 二、模板重构

### 2.1 base.html 公共模板

抽取公共部分到 `templates/base.html`：

```
base.html 结构：
├── <head>（meta、CSS、字体）
│   ├── {% block title %}家庭财务{% endblock %}
│   └── {% block extra_head %}（各页面额外依赖，如 Chart.js）{% endblock %}
├── 桌面端顶部导航
├── 移动端顶部栏（Logo + 汉堡按钮）
├── 移动端汉堡侧滑菜单
├── <main>{% block content %}（各页面内容）{% endblock %}</main>
├── 移动端底部 Tab 栏
├── 公共 JS（菜单切换、Toast、loading、确认弹窗）
└── {% block scripts %}（各页面私有 JS）{% endblock %}
```

### 2.2 子模板改造

所有 12 个模板改为继承 base.html：

```jinja2
{% extends "base.html" %}
{% block content %}
  <!-- 页面特有内容 -->
{% endblock %}
```

需要改造的模板（继承 `base.html`）：
- index.html、accounts.html、reports.html、categories.html
- savings.html、baby_fund.html、upload.html、edit_transaction.html
- family/info.html、family/members.html

需要改造的模板（继承 `auth_base.html`）：
- auth/login.html、auth/register.html

### 2.3 认证页面处理

登录/注册页面不需要导航栏和底部 Tab，使用独立的 `auth_base.html`：
- 只包含 <head> 和基础样式
- 不包含导航和 Tab

---

## 三、交互细节

### 3.1 空状态提示

当列表为空时，显示友好的空状态插图和文案：

| 页面 | 空状态文案 | 引导按钮 |
|------|----------|---------|
| 首页（无交易） | 还没有交易记录，开始记一笔吧 | + 添加交易 |
| 账户（无账户） | 还没有添加账户 | + 添加账户 |
| 储蓄计划（无计划） | 还没有储蓄计划，设一个目标吧 | + 创建计划 |
| 宝宝基金（无记录） | 还没有宝宝基金记录 | + 添加记录 |

样式：居中显示，浅灰色图标 + 文字，带一个主色按钮。

### 3.2 表单提交 loading

- 点击提交按钮后，按钮变为 loading 状态（显示旋转图标 + "处理中..."）
- 防止重复提交（设置 `disabled` 属性）
- 成功时：页面跳转或刷新（按钮无需恢复）
- 失败时（网络错误/服务端错误）：恢复按钮可点击状态，同时触发 Toast 错误提示

### 3.3 删除确认优化

当前删除是浏览器原生 `confirm()` 弹窗。改为自定义确认弹窗：
- 居中模态框，遮罩层
- 显示「确定要删除这条记录吗？」
- 两个按钮：取消（灰色）、确认删除（红色）
- 与应用视觉风格一致

**接入方式：** 所有删除按钮统一使用 `data-confirm-delete` 属性和 `data-url` 属性：
```html
<button class="btn-delete" data-confirm-delete data-url="/transactions/1/delete">删除</button>
```
由 `app.js` 通过事件委托统一拦截，弹出确认弹窗，确认后提交 POST 请求。

### 3.4 Toast 消息提示

**触发方式：** 基于 Flask `flash()` 消息。`base.html` 中渲染 `get_flashed_messages(with_categories=true)`，自动转为 Toast 显示。

操作成功/失败时，在页面顶部显示 Toast 提示条：
- 成功（`success` 类别）：绿色背景，3 秒自动消失
- 失败（`error` 类别）：红色背景，需手动关闭
- 从顶部滑入，自动消失时滑出
- 多条 Toast 依次堆叠显示

---

## 四、文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `templates/base.html` — 公共模板 |
| 新建 | `templates/auth_base.html` — 认证页公共模板 |
| 新建 | `src/static/js/app.js` — 公共 JS（菜单、Toast、loading、确认弹窗） |
| 修改 | `src/static/css/style.css` — 添加移动端样式、断点、组件样式 |
| 修改 | 12 个子模板 — 改为继承 base.html |

---

## 五、测试验证

- 桌面端：Chrome 1280px 宽度，确认导航、布局、交互不变
- 平板端：768px 宽度，确认 2 列布局正常
- 手机端：375px 宽度，确认底部 Tab、汉堡菜单、单列布局正常
- 汉堡菜单：打开 → 点击遮罩层关闭、点击 ✕ 关闭、点击菜单项后关闭
- 底部 Tab：「更多」按钮应触发汉堡菜单打开；当前页面高亮正确
- 触摸：确认按钮 ≥ 44px，表单输入 ≥ 48px
- 交互：空状态、loading、删除确认、Toast 均正常显示
- Toast：成功 3 秒消失、失败需手动关闭、多条 Toast 堆叠正确
