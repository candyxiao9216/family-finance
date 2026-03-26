# UI 体验优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化家庭财务系统的移动端体验和交互细节，包括混合导航、模板重构、Toast/loading/确认弹窗等组件。

**Architecture:** 抽取 base.html 公共模板消除 12 个模板的重复代码；新建 app.js 处理菜单切换、Toast、loading、删除确认等公共交互；在 style.css 中添加 768px/1024px 断点和移动端组件样式。

**Tech Stack:** Flask/Jinja2 模板继承、原生 CSS（媒体查询）、原生 JavaScript（无框架）

**设计文档:** `docs/superpowers/specs/2026-03-26-ui-optimization-design.md`

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `src/templates/base.html` | 公共模板：head、桌面导航、移动端导航、底部Tab、公共JS引用 |
| 新建 | `src/templates/auth_base.html` | 认证页公共模板：仅 head + 基础样式，无导航 |
| 新建 | `src/static/js/app.js` | 公共 JS：汉堡菜单、Toast、loading、删除确认弹窗 |
| 修改 | `src/static/css/style.css` | 添加：底部Tab栏、汉堡菜单、Toast、确认弹窗、空状态、768px/1024px 断点 |
| 修改 | `src/templates/index.html` | 改为继承 base.html，删除重复的 head/nav |
| 修改 | `src/templates/accounts.html` | 同上 |
| 修改 | `src/templates/reports.html` | 同上 |
| 修改 | `src/templates/categories.html` | 同上 |
| 修改 | `src/templates/savings.html` | 同上 |
| 修改 | `src/templates/baby_fund.html` | 同上 |
| 修改 | `src/templates/upload.html` | 同上 |
| 修改 | `src/templates/edit_transaction.html` | 同上 |
| 修改 | `src/templates/family/info.html` | 同上 |
| 修改 | `src/templates/family/members.html` | 同上 |
| 修改 | `src/templates/auth/login.html` | 改为继承 auth_base.html |
| 修改 | `src/templates/auth/register.html` | 同上 |

---

### Task 1: 创建 base.html 公共模板 + app.js 骨架

**Files:**
- Create: `src/templates/base.html`
- Create: `src/static/js/app.js`

**上下文：** 当前每个模板都重复了约 40 行的 head + nav 代码（第 1-47 行）。需要抽取为公共模板。现有导航结构见 `src/templates/index.html:1-47`。所有模板都通过 `{{ username }}`、`{{ family }}`、`{{ current_view }}` 这几个模板变量渲染导航区域。

- [ ] **Step 1: 创建 base.html**

创建 `src/templates/base.html`，包含完整的 HTML 骨架：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}家庭财务{% endblock %} - 家庭财务管理</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
    {% block extra_head %}{% endblock %}
</head>
<body>
    <div class="container">
        <!-- 桌面端头部导航（≥768px 显示） -->
        <header class="header desktop-nav">
            <div class="header-main">
                <h1>家庭财务</h1>
                <p id="current-date"></p>
            </div>
            <div class="user-info">
                <span class="username">{{ username }}</span>
                <div class="user-actions">
                    <a href="{{ url_for('index') }}" class="nav-link">首页</a>
                    <div class="nav-dropdown">
                        <a href="#" class="nav-link nav-dropdown-trigger">账户 ▾</a>
                        <div class="nav-dropdown-menu">
                            <a href="{{ url_for('account.account_list') }}" class="nav-dropdown-item">账户管理</a>
                            <a href="{{ url_for('savings.savings_list') }}" class="nav-dropdown-item">储蓄计划</a>
                            <a href="{{ url_for('baby_fund.baby_fund_list') }}" class="nav-dropdown-item">宝宝基金</a>
                        </div>
                    </div>
                    <a href="{{ url_for('reports.reports_page', view=current_view) }}" class="nav-link">报表</a>
                    <div class="nav-dropdown">
                        <a href="#" class="nav-link nav-dropdown-trigger">设置 ▾</a>
                        <div class="nav-dropdown-menu">
                            <a href="{{ url_for('category.category_list') }}" class="nav-dropdown-item">分类管理</a>
                            <a href="{{ url_for('upload.upload_page') }}" class="nav-dropdown-item">批量导入</a>
                        </div>
                    </div>
                    {% if family %}
                    <a href="{{ url_for('family.family_info') }}" class="nav-link">家庭</a>
                    {% endif %}
                    <a href="{{ url_for('auth.logout') }}" class="logout-btn">退出</a>
                </div>
            </div>
        </header>

        <!-- 移动端顶部栏（<768px 显示） -->
        <header class="header mobile-header">
            <div class="mobile-header-left">
                <span class="mobile-logo">💰</span>
                <h1>{% block mobile_title %}家庭财务{% endblock %}</h1>
            </div>
            <button class="hamburger-btn" id="hamburger-btn" aria-label="打开菜单">
                <span></span><span></span><span></span>
            </button>
        </header>

        <!-- 汉堡侧滑菜单 -->
        <div class="side-menu-overlay" id="side-menu-overlay"></div>
        <nav class="side-menu" id="side-menu">
            <div class="side-menu-header">
                <span class="username">{{ username }}</span>
                <button class="side-menu-close" id="side-menu-close">✕</button>
            </div>
            <div class="side-menu-items">
                <a href="{{ url_for('index') }}" class="side-menu-item">🏠 首页</a>
                <a href="{{ url_for('account.account_list') }}" class="side-menu-item">💳 账户管理</a>
                <a href="{{ url_for('savings.savings_list') }}" class="side-menu-item">🎯 储蓄计划</a>
                <a href="{{ url_for('baby_fund.baby_fund_list') }}" class="side-menu-item">👶 宝宝基金</a>
                <a href="{{ url_for('reports.reports_page', view=current_view) }}" class="side-menu-item">📊 报表</a>
                <div class="side-menu-divider"></div>
                <a href="{{ url_for('category.category_list') }}" class="side-menu-item">📂 分类管理</a>
                <a href="{{ url_for('upload.upload_page') }}" class="side-menu-item">📥 批量导入</a>
                {% if family %}
                <div class="side-menu-divider"></div>
                <a href="{{ url_for('family.family_info') }}" class="side-menu-item">👨‍👩‍👧 家庭</a>
                {% endif %}
            </div>
            <div class="side-menu-footer">
                <a href="{{ url_for('auth.logout') }}" class="side-menu-item side-menu-logout">🚪 退出登录</a>
            </div>
        </nav>

        <!-- Toast 消息容器 -->
        <div class="toast-container" id="toast-container">
            {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
            {% for category, message in messages %}
            <div class="toast toast-{{ category }}" data-auto-dismiss="{{ 'true' if category == 'success' else 'false' }}">
                <span class="toast-message">{{ message }}</span>
                <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
            </div>
            {% endfor %}
            {% endif %}
            {% endwith %}
        </div>

        <!-- 确认弹窗 -->
        <div class="confirm-modal" id="confirm-modal">
            <div class="confirm-modal-overlay"></div>
            <div class="confirm-modal-content">
                <p class="confirm-modal-message" id="confirm-modal-message">确定要删除吗？</p>
                <div class="confirm-modal-actions">
                    <button class="btn-cancel" id="confirm-cancel">取消</button>
                    <button class="btn-confirm-delete" id="confirm-ok">确认删除</button>
                </div>
            </div>
        </div>

        <!-- 页面主内容 -->
        <main class="main-content">
            {% block content %}{% endblock %}
        </main>

        <!-- 移动端底部 Tab 栏（<768px 显示） -->
        <nav class="bottom-tab-bar">
            <a href="{{ url_for('index') }}" class="tab-item {{ 'active' if request.path == '/' }}">
                <span class="tab-icon">🏠</span>
                <span class="tab-label">首页</span>
            </a>
            <a href="{{ url_for('account.account_list') }}" class="tab-item {{ 'active' if request.path.startswith('/accounts') }}">
                <span class="tab-icon">💳</span>
                <span class="tab-label">账户</span>
            </a>
            <a href="{{ url_for('reports.reports_page', view=current_view) }}" class="tab-item {{ 'active' if request.path.startswith('/reports') }}">
                <span class="tab-icon">📊</span>
                <span class="tab-label">报表</span>
            </a>
            <button class="tab-item tab-more {{ 'active' if request.path.startswith('/savings') or request.path.startswith('/baby-fund') or request.path.startswith('/categories') or request.path.startswith('/upload') }}" id="tab-more">
                <span class="tab-icon">⚙️</span>
                <span class="tab-label">更多</span>
            </button>
        </nav>
    </div>

    <script src="/static/js/app.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: 创建 app.js 骨架**

创建 `src/static/js/app.js`：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // === 汉堡菜单 ===
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const sideMenu = document.getElementById('side-menu');
    const sideMenuOverlay = document.getElementById('side-menu-overlay');
    const sideMenuClose = document.getElementById('side-menu-close');
    const tabMore = document.getElementById('tab-more');

    function openMenu() {
        sideMenu.classList.add('open');
        sideMenuOverlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeMenu() {
        sideMenu.classList.remove('open');
        sideMenuOverlay.classList.remove('open');
        document.body.style.overflow = '';
    }

    if (hamburgerBtn) hamburgerBtn.addEventListener('click', openMenu);
    if (sideMenuClose) sideMenuClose.addEventListener('click', closeMenu);
    if (sideMenuOverlay) sideMenuOverlay.addEventListener('click', closeMenu);
    if (tabMore) tabMore.addEventListener('click', openMenu);

    // 点击菜单项后关闭
    document.querySelectorAll('.side-menu-item').forEach(function(item) {
        item.addEventListener('click', closeMenu);
    });

    // === Toast 自动消失 ===
    document.querySelectorAll('.toast[data-auto-dismiss="true"]').forEach(function(toast) {
        setTimeout(function() {
            toast.style.animation = 'slideOutUp 0.3s ease forwards';
            setTimeout(function() { toast.remove(); }, 300);
        }, 3000);
    });

    // === 删除确认弹窗 ===
    const confirmModal = document.getElementById('confirm-modal');
    const confirmMessage = document.getElementById('confirm-modal-message');
    const confirmCancel = document.getElementById('confirm-cancel');
    const confirmOk = document.getElementById('confirm-ok');
    let pendingDeleteForm = null;
    let pendingDeleteUrl = null;

    // 拦截所有带 data-confirm-delete 的按钮点击
    // 接入方式：form-based（所有删除按钮都在 <form> 内，确认后 form.submit()）
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-confirm-delete]');
        if (!btn) return;
        e.preventDefault();
        // 优先用 form，备选用 data-url 直接跳转
        const form = btn.closest('form');
        const url = btn.getAttribute('data-url');
        if (!form && !url) return;
        pendingDeleteForm = form;
        pendingDeleteUrl = url;
        const msg = btn.getAttribute('data-confirm-message') || '确定要删除这条记录吗？';
        confirmMessage.textContent = msg;
        confirmModal.classList.add('open');
    });

    if (confirmCancel) {
        confirmCancel.addEventListener('click', function() {
            confirmModal.classList.remove('open');
            pendingDeleteForm = null;
        });
    }

    if (confirmOk) {
        confirmOk.addEventListener('click', function() {
            if (pendingDeleteForm) pendingDeleteForm.submit();
            else if (pendingDeleteUrl) window.location.href = pendingDeleteUrl;
            confirmModal.classList.remove('open');
        });
    }

    // 点击遮罩关闭
    if (confirmModal) {
        confirmModal.querySelector('.confirm-modal-overlay').addEventListener('click', function() {
            confirmModal.classList.remove('open');
            pendingDeleteForm = null;
        });
    }

    // === 表单 loading ===
    document.querySelectorAll('form[data-loading]').forEach(function(form) {
        form.addEventListener('submit', function() {
            const btn = form.querySelector('button[type="submit"]');
            if (btn && !btn.disabled) {
                btn.disabled = true;
                btn.dataset.originalText = btn.textContent;
                btn.textContent = '处理中...';
                btn.classList.add('loading');
            }
        });
    });

    // === 日期显示 ===
    const dateEl = document.getElementById('current-date');
    if (dateEl) {
        const now = new Date();
        const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
        dateEl.textContent = now.toLocaleDateString('zh-CN', options);
    }
});
```

- [ ] **Step 3: 创建 auth_base.html**

创建 `src/templates/auth_base.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}登录{% endblock %} - 家庭财务管理</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: 验证模板文件创建成功**

Run: `ls -la src/templates/base.html src/templates/auth_base.html src/static/js/app.js`
Expected: 3 个文件存在

- [ ] **Step 5: Commit**

```bash
git add src/templates/base.html src/templates/auth_base.html src/static/js/app.js
git commit -m "feat: 创建 base.html 公共模板和 app.js 交互骨架"
```

---

### Task 2: 添加移动端 CSS 样式

**Files:**
- Modify: `src/static/css/style.css`

**上下文：** 当前 style.css 约 1766 行，已有 CSS 变量系统和 640px 断点。需要添加：底部 Tab 栏、汉堡侧滑菜单、Toast 消息、确认弹窗、空状态样式，以及新的 768px/1024px 断点（替代 640px）。

- [ ] **Step 1: 在 style.css 末尾追加移动端组件样式**

在文件末尾添加以下 CSS（约 350 行）：

```css
/* ==========================================
   Phase 4: 移动端适配 + 交互组件
   ========================================== */

/* --- 移动端顶部栏 --- */
.mobile-header {
    display: none;
}

.mobile-header-left {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.mobile-header-left .mobile-logo {
    font-size: 24px;
}

.mobile-header-left h1 {
    font-size: 20px;
    font-family: 'Noto Serif SC', serif;
}

.hamburger-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 44px;
    min-height: 44px;
    align-items: center;
    justify-content: center;
}

.hamburger-btn span {
    display: block;
    width: 22px;
    height: 2px;
    background: var(--color-text-primary);
    border-radius: 2px;
    transition: var(--transition-fast);
}

/* --- 汉堡侧滑菜单 --- */
.side-menu-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 998;
    opacity: 0;
    transition: opacity var(--transition-normal);
}

.side-menu-overlay.open {
    display: block;
    opacity: 1;
}

.side-menu {
    position: fixed;
    top: 0;
    right: -280px;
    width: 280px;
    height: 100%;
    background: var(--color-bg-card);
    z-index: 999;
    transition: right var(--transition-normal);
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
}

.side-menu.open {
    right: 0;
}

.side-menu-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-lg);
    border-bottom: 1px solid var(--color-border);
}

.side-menu-header .username {
    font-weight: 600;
    font-size: 16px;
}

.side-menu-close {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: var(--color-text-secondary);
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.side-menu-items {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-sm) 0;
}

.side-menu-item {
    display: block;
    padding: 14px var(--space-lg);
    color: var(--color-text-primary);
    text-decoration: none;
    font-size: 15px;
    transition: background var(--transition-fast);
    min-height: 44px;
    display: flex;
    align-items: center;
}

.side-menu-item:hover,
.side-menu-item:active {
    background: var(--color-border-light);
}

.side-menu-divider {
    height: 1px;
    background: var(--color-border);
    margin: var(--space-sm) var(--space-lg);
}

.side-menu-footer {
    border-top: 1px solid var(--color-border);
    padding: var(--space-sm) 0;
}

.side-menu-logout {
    color: var(--color-accent) !important;
}

/* --- 底部 Tab 栏 --- */
.bottom-tab-bar {
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: var(--color-bg-card);
    border-top: 1px solid var(--color-border);
    justify-content: space-around;
    align-items: center;
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom, 0);
}

.tab-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: var(--color-text-muted);
    font-size: 11px;
    padding: 4px 12px;
    min-width: 60px;
    min-height: 44px;
    background: none;
    border: none;
    cursor: pointer;
    transition: color var(--transition-fast);
}

.tab-item.active {
    color: var(--color-income);
}

.tab-icon {
    font-size: 20px;
    margin-bottom: 2px;
}

.tab-label {
    font-size: 11px;
}

/* --- Toast 消息 --- */
.toast-container {
    position: fixed;
    top: var(--space-lg);
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    width: 90%;
    max-width: 400px;
}

.toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    color: white;
    font-size: 14px;
    animation: slideInDown 0.3s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.toast-success {
    background: #4CAF50;
}

.toast-error {
    background: #f44336;
}

.toast-info, .toast-message-default {
    background: var(--color-income);
}

.toast-close {
    background: none;
    border: none;
    color: white;
    font-size: 16px;
    cursor: pointer;
    padding: 4px;
    margin-left: 12px;
    opacity: 0.8;
}

.toast-close:hover {
    opacity: 1;
}

@keyframes slideInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideOutUp {
    from { opacity: 1; transform: translateY(0); }
    to { opacity: 0; transform: translateY(-20px); }
}

/* --- 确认弹窗 --- */
.confirm-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1001;
    align-items: center;
    justify-content: center;
}

.confirm-modal.open {
    display: flex;
}

.confirm-modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
}

.confirm-modal-content {
    position: relative;
    background: var(--color-bg-card);
    border-radius: var(--radius-md);
    padding: var(--space-xl);
    max-width: 360px;
    width: 90%;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
    text-align: center;
}

.confirm-modal-message {
    font-size: 16px;
    color: var(--color-text-primary);
    margin-bottom: var(--space-xl);
    line-height: 1.5;
}

.confirm-modal-actions {
    display: flex;
    gap: var(--space-md);
    justify-content: center;
}

.confirm-modal-actions .btn-cancel {
    padding: 10px 24px;
    border: 1px solid var(--color-border);
    background: var(--color-bg-card);
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 14px;
    min-height: 44px;
}

.confirm-modal-actions .btn-confirm-delete {
    padding: 10px 24px;
    background: #f44336;
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 14px;
    min-height: 44px;
}

/* --- 空状态 --- */
.empty-state {
    text-align: center;
    padding: var(--space-2xl) var(--space-lg);
    color: var(--color-text-muted);
}

.empty-state-icon {
    font-size: 48px;
    margin-bottom: var(--space-md);
}

.empty-state-text {
    font-size: 15px;
    margin-bottom: var(--space-lg);
}

.empty-state-btn {
    display: inline-block;
    padding: 10px 24px;
    background: var(--color-income);
    color: white;
    border-radius: var(--radius-sm);
    text-decoration: none;
    font-size: 14px;
    min-height: 44px;
}

/* --- 表单 loading 状态 --- */
button.loading {
    opacity: 0.7;
    cursor: not-allowed;
}

/* ==========================================
   响应式断点（替代原有 640px）
   ========================================== */

/* 手机端：<768px */
@media (max-width: 767px) {
    .desktop-nav {
        display: none !important;
    }

    .mobile-header {
        display: flex !important;
        justify-content: space-between;
        align-items: center;
    }

    .bottom-tab-bar {
        display: flex;
    }

    .main-content {
        padding-bottom: 70px;
    }

    /* 统计栏单列 */
    .stats-bar {
        flex-direction: column;
        gap: var(--space-sm);
    }

    /* 网格单列 */
    .account-grid,
    .savings-grid {
        grid-template-columns: 1fr;
    }

    /* 交易项紧凑 */
    .transaction-meta .transaction-source,
    .transaction-meta .transaction-creator {
        display: none;
    }

    .transaction-desc {
        max-width: 150px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* 抽屉全宽 */
    .drawer-panel {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* 表单输入框触摸友好 */
    input, select, textarea {
        min-height: 48px;
        font-size: 16px; /* 防止 iOS 自动缩放 */
    }

    /* 交易操作按钮加大点击区域 */
    .transaction-actions button,
    .transaction-actions a {
        min-width: 44px;
        min-height: 44px;
        padding: 8px;
    }
}

/* 平板：768px - 1024px */
@media (min-width: 768px) and (max-width: 1023px) {
    .account-grid,
    .savings-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* 桌面端（≥768px）隐藏移动端元素 */
@media (min-width: 768px) {
    .mobile-header {
        display: none !important;
    }

    .bottom-tab-bar {
        display: none !important;
    }

    .side-menu,
    .side-menu-overlay {
        display: none !important;
    }
}
```

- [ ] **Step 2: 本地启动确认样式加载无错误**

Run: `python3 src/main.py &` 然后 `curl -s http://localhost:5001/static/css/style.css | tail -5`
Expected: 能看到新加的 CSS 末尾内容

- [ ] **Step 3: Commit**

```bash
git add src/static/css/style.css
git commit -m "feat: 添加移动端导航、Toast、确认弹窗、空状态等 CSS 样式"
```

---

### Task 3: 改造 index.html 继承 base.html

**Files:**
- Modify: `src/templates/index.html`

**上下文：** index.html 当前 350 行，第 1-47 行是 head+nav（将由 base.html 提供），第 48-350 行是页面内容和 JS。需要删除 head/nav，改为 `{% extends "base.html" %}`，页面内容放入 `{% block content %}`，Chart.js 引用放入 `{% block extra_head %}`，页面 JS 放入 `{% block scripts %}`。

- [ ] **Step 1: 改造 index.html**

将 index.html 改为继承 base.html 的结构：
- 删除第 1-13 行（DOCTYPE 到 `</head>`），替换为 extends + block title + block extra_head
- 删除第 14 行 `<body>` 和第 15 行 `<div class="container">`
- 删除第 16-47 行（header 导航）
- 将第 48 行到 `</script>` 之前的 HTML 内容包裹在 `{% block content %}...{% endblock %}`
- 将 `<script>` 内容包裹在 `{% block scripts %}...{% endblock %}`
- 删除末尾的 `</div></body></html>`
- 将现有的 flash messages 代码删除（base.html 已统一处理）

关键变化：
```jinja2
{% extends "base.html" %}

{% block title %}首页{% endblock %}

{% block extra_head %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
{% endblock %}

{% block content %}
    <!-- 视图切换 -->
    {% if family %}
    ...（保持原有内容不变）
    {% endif %}

    <!-- 统计栏 -->
    ...（保持原有内容不变）

    <!-- 后续所有内容保持不变 -->
{% endblock %}

{% block scripts %}
<script>
    // 原有的 JS 代码（删除日期显示代码，已由 app.js 处理）
</script>
{% endblock %}
```

- [ ] **Step 2: 启动应用，访问首页确认正常显示**

Run: `python3 src/main.py`
访问 http://localhost:5001，确认：桌面端导航显示正常，页面内容无变化

- [ ] **Step 3: Commit**

```bash
git add src/templates/index.html
git commit -m "refactor: index.html 改为继承 base.html"
```

---

### Task 4: 改造其余 9 个页面模板

**Files:**
- Modify: `src/templates/accounts.html`
- Modify: `src/templates/reports.html`
- Modify: `src/templates/categories.html`
- Modify: `src/templates/savings.html`
- Modify: `src/templates/baby_fund.html`
- Modify: `src/templates/upload.html`
- Modify: `src/templates/edit_transaction.html`
- Modify: `src/templates/family/info.html`
- Modify: `src/templates/family/members.html`

**上下文：** 每个模板的改造方式与 Task 3 相同：删除 head/nav，改为 extends base.html。每个模板的差异点：
- `reports.html` 需要 `{% block extra_head %}` 引入 Chart.js
- 所有模板中已有的 `get_flashed_messages` 代码需要删除（base.html 已统一处理）
- 所有模板中的 `onclick="return confirm(...)"` 需要改为 `data-confirm-delete data-confirm-message="..."`

- [ ] **Step 1: 逐个改造 9 个模板**

对每个模板执行相同的改造：
1. 替换 head+nav 为 `{% extends "base.html" %}` + blocks
2. 页面内容包裹在 `{% block content %}`
3. 页面 JS 包裹在 `{% block scripts %}`
4. 删除 flash messages 渲染代码
5. 将删除按钮的 `onclick="return confirm('...')"` 改为 `data-confirm-delete data-confirm-message="..."`

删除按钮改造示例（以 categories.html 为例）：
```html
<!-- 改造前 -->
<button type="submit" class="btn-delete-cat" onclick="return confirm('确定删除分类「{{ c.name }}」？')">删除</button>

<!-- 改造后 -->
<button type="submit" class="btn-delete-cat" data-confirm-delete data-confirm-message="确定删除分类「{{ c.name }}」？关联的交易将变为未分类。">删除</button>
```

- [ ] **Step 2: 改造 auth/login.html 和 auth/register.html**

这两个改为继承 `auth_base.html`：
```jinja2
{% extends "auth_base.html" %}
{% block title %}登录{% endblock %}
{% block content %}
    <!-- 保持原有登录表单内容不变 -->
{% endblock %}
```

- [ ] **Step 3: 启动应用，逐页访问确认正常**

Run: `python3 src/main.py`
逐个访问以下 URL 确认页面正常渲染：
- http://localhost:5001/ （首页）
- http://localhost:5001/accounts （账户）
- http://localhost:5001/reports （报表）
- http://localhost:5001/categories （分类）
- http://localhost:5001/savings （储蓄）
- http://localhost:5001/baby-fund （宝宝基金）
- http://localhost:5001/upload （导入）
- http://localhost:5001/auth/login （登录）

- [ ] **Step 4: Commit**

```bash
git add src/templates/
git commit -m "refactor: 所有模板改为继承 base.html/auth_base.html，统一删除确认"
```

---

### Task 5: 添加空状态提示

**Files:**
- Modify: `src/templates/index.html`
- Modify: `src/templates/accounts.html`
- Modify: `src/templates/savings.html`
- Modify: `src/templates/baby_fund.html`

**上下文：** 当列表为空时，目前只显示空白区域。需要添加友好的空状态提示。

- [ ] **Step 1: 在各页面列表为空时显示空状态**

在各模板的列表渲染位置添加 `{% else %}` 分支：

**index.html**（交易列表区域）：
```html
{% if transactions %}
    <!-- 现有交易列表 -->
{% else %}
    <div class="empty-state">
        <div class="empty-state-icon">📝</div>
        <p class="empty-state-text">还没有交易记录，开始记一笔吧</p>
        <a href="#" class="empty-state-btn" onclick="document.getElementById('add-form').scrollIntoView()">+ 添加交易</a>
    </div>
{% endif %}
```

**accounts.html**：
```html
{% if accounts %}
    <!-- 现有账户列表 -->
{% else %}
    <div class="empty-state">
        <div class="empty-state-icon">💳</div>
        <p class="empty-state-text">还没有添加账户</p>
        <a href="#" class="empty-state-btn" onclick="document.querySelector('.drawer-toggle').click()">+ 添加账户</a>
    </div>
{% endif %}
```

**savings.html**：
```html
{% if plans %}
    <!-- 现有储蓄计划列表 -->
{% else %}
    <div class="empty-state">
        <div class="empty-state-icon">🎯</div>
        <p class="empty-state-text">还没有储蓄计划，设一个目标吧</p>
        <a href="#" class="empty-state-btn" onclick="document.querySelector('.drawer-toggle').click()">+ 创建计划</a>
    </div>
{% endif %}
```

**baby_fund.html**：
```html
{% if funds %}
    <!-- 现有宝宝基金列表 -->
{% else %}
    <div class="empty-state">
        <div class="empty-state-icon">👶</div>
        <p class="empty-state-text">还没有宝宝基金记录</p>
        <a href="#" class="empty-state-btn" onclick="document.querySelector('.drawer-toggle').click()">+ 添加记录</a>
    </div>
{% endif %}
```

- [ ] **Step 2: 验证空状态显示**

注册一个新用户（无数据），访问各页面确认空状态提示正常显示。

- [ ] **Step 3: Commit**

```bash
git add src/templates/index.html src/templates/accounts.html src/templates/savings.html src/templates/baby_fund.html
git commit -m "feat: 添加空状态提示，无数据时显示友好引导"
```

---

### Task 6: 修改 Flask 路由使用分类 flash

**Files:**
- Modify: `src/routes/auth.py`
- Modify: `src/routes/savings.py`
- Modify: `src/routes/baby_fund.py`
- Modify: `src/routes/upload.py`
- Modify: `src/main.py`（首页路由）
- Modify: `src/routes/account.py`
- Modify: `src/routes/category.py`

**上下文：** 当前所有 `flash()` 调用都不带 category 参数，但 base.html 的 Toast 需要 `with_categories=true` 才能区分成功/错误样式。需要给所有 flash 调用加上类别。

- [ ] **Step 1: 更新所有 flash 调用**

将所有 `flash('消息')` 改为 `flash('消息', 'success')` 或 `flash('消息', 'error')`。

规则：
- 操作成功（创建/更新/删除/登录）→ `flash('...', 'success')`
- 操作失败（验证错误/异常）→ `flash('...', 'error')`

示例改造：
```python
# auth.py
flash('用户名和密码不能为空', 'error')
flash('注册成功！', 'success')
flash('用户名或密码错误', 'error')
flash('欢迎回来！', 'success')

# savings.py
flash('请填写所有必填字段', 'error')
flash('计划创建成功', 'success')
flash('记录已删除', 'success')
```

- [ ] **Step 2: 验证 Toast 样式**

启动应用，执行一次登录操作，确认：
- 成功消息显示绿色 Toast，3 秒后自动消失
- 错误消息（输入空密码）显示红色 Toast，需手动关闭

- [ ] **Step 3: Commit**

```bash
git add src/routes/ src/main.py
git commit -m "feat: flash 消息添加分类，支持 Toast 成功/错误样式区分"
```

---

### Task 7: 运行测试 + 浏览器验证 + 清理旧断点

**Files:**
- Modify: `src/static/css/style.css`（清理旧 640px 断点）

- [ ] **Step 1: 运行现有测试**

Run: `python3 -m pytest tests/test_savings.py tests/test_baby_fund.py tests/test_importers.py tests/test_upload.py -v 2>&1 | tail -20`
Expected: 核心测试通过（部分路由测试可能因模板变更需要修复）

- [ ] **Step 2: 清理旧的 640px 断点**

在 style.css 中搜索 `@media (max-width: 640px)` 和 `@media (min-width: 640px)`，将其中的样式规则合并到新的 768px 断点中，然后删除旧断点。

- [ ] **Step 3: 浏览器验证（桌面 + 移动端）**

使用 Playwright 打开 http://localhost:5001：
1. 桌面端（1280px）：确认顶部导航正常，底部 Tab 不显示
2. 移动端（375px）：确认底部 Tab 显示、汉堡菜单可打开/关闭、页面单列布局

- [ ] **Step 4: 更新 PROJECT_BRIEF.md**

更新当前状态：
- 当前里程碑：Phase 4 进行中
- 已可用能力新增：移动端适配（底部 Tab + 汉堡菜单）、base.html 模板重构、Toast/loading/确认弹窗
- 下一步 5 件事更新

- [ ] **Step 5: Commit**

```bash
git add src/static/css/style.css PROJECT_BRIEF.md
git commit -m "feat: 清理旧断点，完成 UI 优化 Phase 4"
```

- [ ] **Step 6: 推送并部署**

```bash
git push origin main
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137 "sudo bash -c 'cd /opt/family-finance && git pull origin main && systemctl restart family-finance'"
```
