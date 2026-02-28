# TASK-005: 数据可视化图表 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 使用 Chart.js 为首页添加缩略图表，并新建独立报表页展示详细图表（月度收支趋势折线图 + 收入/支出分类饼图）。

**Architecture:** 新建 `src/routes/reports.py` 蓝图提供图表数据 JSON API；首页嵌入两个迷你图表（统计栏下方）；独立报表页 `/reports` 展示完整图表，支持 1/3/6/12 月按钮组切换（默认 6 月）。图表数据跟随「我的/家庭」视图切换。

**Tech Stack:** Chart.js (CDN)、Flask Blueprint、SQLAlchemy 聚合查询

---

## Task 1: 创建报表数据 API 蓝图

**Files:**
- Create: `src/routes/reports.py`
- Modify: `src/main.py:1-19`（导入并注册蓝图）

**Step 1: 创建 `src/routes/reports.py`**

```python
"""
报表数据路由模块
提供图表所需的 JSON 数据 API 和报表页面
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for
from sqlalchemy import func, extract
from models import db, Transaction, Category, User

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_user_filter(user_id, current_view):
    """根据视图类型返回用户过滤条件"""
    user = User.query.get(user_id)
    family = user.family if user else None

    if current_view == 'family' and family:
        family_member_ids = [m.id for m in family.members]
        return Transaction.user_id.in_(family_member_ids), family
    else:
        return (Transaction.user_id == user_id), None


@reports_bp.route('/')
def reports_page():
    """报表页面"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    if not (current_view == 'family' and family):
        current_view = 'personal'

    return render_template('reports.html',
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@reports_bp.route('/api/trend')
def api_trend():
    """月度收支趋势数据 API
    参数: months=1|3|6|12, view=personal|family
    返回: { labels: ["2026-01", ...], income: [100, ...], expense: [200, ...] }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6
    current_view = request.args.get('view', 'personal')
    user_filter, _ = _get_user_filter(user_id, current_view)

    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    # 按月聚合收入/支出
    rows = db.session.query(
        extract('year', Transaction.transaction_date).label('y'),
        extract('month', Transaction.transaction_date).label('m'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        user_filter,
        Transaction.transaction_date >= start_date
    ).group_by('y', 'm', Transaction.type).all()

    # 构建月份列表
    labels = []
    income_map = {}
    expense_map = {}
    cursor = start_date
    while cursor <= today:
        key = f"{cursor.year}-{cursor.month:02d}"
        labels.append(key)
        income_map[key] = 0
        expense_map[key] = 0
        cursor = (cursor + relativedelta(months=1))

    for row in rows:
        key = f"{int(row.y)}-{int(row.m):02d}"
        if key in income_map:
            if row.type == 'income':
                income_map[key] = float(row.total)
            else:
                expense_map[key] = float(row.total)

    return jsonify({
        'labels': labels,
        'income': [income_map[k] for k in labels],
        'expense': [expense_map[k] for k in labels]
    })


@reports_bp.route('/api/category')
def api_category():
    """分类占比数据 API
    参数: type=income|expense, months=1|3|6|12, view=personal|family
    返回: { labels: ["餐饮", ...], values: [500, ...] }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401

    cat_type = request.args.get('type', 'expense')
    if cat_type not in ('income', 'expense'):
        cat_type = 'expense'
    months = request.args.get('months', 6, type=int)
    if months not in (1, 3, 6, 12):
        months = 6
    current_view = request.args.get('view', 'personal')
    user_filter, _ = _get_user_filter(user_id, current_view)

    today = date.today()
    start_date = (today.replace(day=1) - relativedelta(months=months - 1))

    rows = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        user_filter,
        Transaction.type == cat_type,
        Transaction.transaction_date >= start_date
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()

    # 未分类的交易
    uncategorized = db.session.query(
        func.sum(Transaction.amount).label('total')
    ).filter(
        user_filter,
        Transaction.type == cat_type,
        Transaction.category_id == None,
        Transaction.transaction_date >= start_date
    ).scalar()

    labels = [r.name for r in rows]
    values = [float(r.total) for r in rows]

    if uncategorized:
        labels.append('未分类')
        values.append(float(uncategorized))

    return jsonify({'labels': labels, 'values': values})
```

**Step 2: 修改 `src/main.py` 注册蓝图**

在 `src/main.py` 中：
- 第 11 行后添加: `from routes.reports import reports_bp`
- 第 19 行后添加: `app.register_blueprint(reports_bp)`

**Step 3: 安装 python-dateutil 依赖**

Run: `pip install python-dateutil`

将 `python-dateutil` 添加到 `requirements.txt`（如存在）。

**Step 4: 验证 API 路由注册**

Run: `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin/src && python3 -c "from main import app; rules = [r.rule for r in app.url_map.iter_rules() if 'reports' in r.rule]; print(rules)"`

Expected: 包含 `/reports/`, `/reports/api/trend`, `/reports/api/category`

**Step 5: Commit**

```bash
git add src/routes/reports.py src/main.py
git commit -m "feat: 添加报表数据 API 蓝图（趋势 + 分类）"
```

---

## Task 2: 创建独立报表页面

**Files:**
- Create: `src/templates/reports.html`

**Step 1: 创建 `src/templates/reports.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>财务报表 - 家庭财务</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <header class="header">
            <div class="header-main">
                <h1>财务报表</h1>
                <p>收支趋势与分类分析</p>
            </div>
            <div class="user-info">
                <span class="username">{{ username }}</span>
                <div class="user-actions">
                    <a href="{{ url_for('index') }}" class="nav-link">首页</a>
                    <a href="{{ url_for('auth.logout') }}" class="logout-btn">退出</a>
                </div>
            </div>
        </header>

        <!-- 视图切换 -->
        {% if family %}
        <div class="view-switcher">
            <a href="/reports?view=personal" class="view-btn {{ 'active' if current_view == 'personal' }}">我的</a>
            <a href="/reports?view=family" class="view-btn {{ 'active' if current_view == 'family' }}">家庭</a>
        </div>
        {% endif %}

        <!-- 时间范围切换 -->
        <div class="view-switcher" id="range-switcher">
            <button class="view-btn" data-months="1">1月</button>
            <button class="view-btn" data-months="3">3月</button>
            <button class="view-btn active" data-months="6">6月</button>
            <button class="view-btn" data-months="12">12月</button>
        </div>

        <!-- 趋势折线图 -->
        <div class="card chart-section">
            <div class="card-header">
                <h2 class="card-title">收支趋势</h2>
            </div>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
        </div>

        <!-- 分类饼图 -->
        <div class="chart-row">
            <div class="card chart-section chart-half">
                <div class="card-header">
                    <h2 class="card-title">支出构成</h2>
                </div>
                <div class="chart-container chart-container-pie">
                    <canvas id="expensePieChart"></canvas>
                </div>
            </div>
            <div class="card chart-section chart-half">
                <div class="card-header">
                    <h2 class="card-title">收入构成</h2>
                </div>
                <div class="chart-container chart-container-pie">
                    <canvas id="incomePieChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <script>
        const currentView = '{{ current_view }}';
        let currentMonths = 6;
        let trendChart, expensePieChart, incomePieChart;

        // 配色方案（与 CSS 变量一致）
        const COLORS = {
            income: '#D4A574',
            incomeBg: 'rgba(212, 165, 116, 0.15)',
            expense: '#7C8BA1',
            expenseBg: 'rgba(124, 139, 161, 0.15)',
            pieColors: [
                '#D4A574', '#7C8BA1', '#E8998D', '#8DB596', '#B8A9C9',
                '#F0C987', '#89B4C7', '#C9978F', '#A4C2A8', '#D4B5D0'
            ]
        };

        // Chart.js 全局配置
        Chart.defaults.font.family = "'Outfit', 'Noto Serif SC', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#6B6B6B';

        async function fetchJSON(url) {
            const resp = await fetch(url);
            return resp.json();
        }

        async function loadTrendChart() {
            const data = await fetchJSON(`/reports/api/trend?months=${currentMonths}&view=${currentView}`);
            const ctx = document.getElementById('trendChart').getContext('2d');

            if (trendChart) trendChart.destroy();

            trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: '收入',
                            data: data.income,
                            borderColor: COLORS.income,
                            backgroundColor: COLORS.incomeBg,
                            fill: true,
                            tension: 0.3,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        },
                        {
                            label: '支出',
                            data: data.expense,
                            borderColor: COLORS.expense,
                            backgroundColor: COLORS.expenseBg,
                            fill: true,
                            tension: 0.3,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ¥${ctx.parsed.y.toLocaleString('zh-CN', {minimumFractionDigits: 2})}`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: v => '¥' + v.toLocaleString()
                            }
                        }
                    }
                }
            });
        }

        async function loadPieChart(canvasId, catType, chartRef) {
            const data = await fetchJSON(`/reports/api/category?type=${catType}&months=${currentMonths}&view=${currentView}`);
            const ctx = document.getElementById(canvasId).getContext('2d');

            if (chartRef) chartRef.destroy();

            const chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.values,
                        backgroundColor: COLORS.pieColors.slice(0, data.labels.length),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { padding: 12 } },
                        tooltip: {
                            callbacks: {
                                label: ctx => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                    return `${ctx.label}: ¥${ctx.parsed.toLocaleString('zh-CN', {minimumFractionDigits: 2})} (${pct}%)`;
                                }
                            }
                        }
                    }
                }
            });
            return chart;
        }

        async function loadAllCharts() {
            await loadTrendChart();
            expensePieChart = await loadPieChart('expensePieChart', 'expense', expensePieChart);
            incomePieChart = await loadPieChart('incomePieChart', 'income', incomePieChart);
        }

        // 时间范围按钮点击
        document.querySelectorAll('#range-switcher .view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#range-switcher .view-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMonths = parseInt(btn.dataset.months);
                loadAllCharts();
            });
        });

        // 初始加载
        loadAllCharts();
    </script>
</body>
</html>
```

**Step 2: 验证页面可访问**

启动应用，访问 `/reports`，确认页面加载且图表渲染（即使没数据也不报错）。

**Step 3: Commit**

```bash
git add src/templates/reports.html
git commit -m "feat: 创建独立报表页面（趋势折线图 + 分类饼图）"
```

---

## Task 3: 首页添加缩略图表和导航入口

**Files:**
- Modify: `src/templates/index.html:23`（添加"报表"导航链接）
- Modify: `src/templates/index.html:60-61`（统计栏后插入迷你图表区域）
- Modify: `src/templates/index.html` 的 `<head>`（添加 Chart.js CDN）

**Step 1: 修改 `src/templates/index.html`**

1. 在 `<head>` 的 `</head>` 前添加 Chart.js CDN：
```html
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
```

2. 在 `user-actions` 中「分类」链接之后添加「报表」链接：
```html
<a href="{{ url_for('reports.reports_page', view=current_view) }}" class="nav-link">报表</a>
```

3. 在 `</div><!-- 统计栏 -->` 之后、`<!-- 添加交易表单 -->` 之前插入迷你图表卡片：
```html
        <!-- 迷你图表 -->
        <div class="card chart-section">
            <div class="card-header">
                <h2 class="card-title">收支趋势</h2>
                <a href="{{ url_for('reports.reports_page', view=current_view) }}" class="chart-detail-link">查看详情</a>
            </div>
            <div class="chart-container chart-container-mini">
                <canvas id="miniTrendChart"></canvas>
            </div>
        </div>
```

4. 在 `<script>` 区域末尾（`updateCategories('expense');` 之后）添加迷你图表初始化代码：
```javascript
        // 迷你趋势图（近 6 个月）
        (async function() {
            const resp = await fetch('/reports/api/trend?months=6&view={{ current_view }}');
            const data = await resp.json();
            const ctx = document.getElementById('miniTrendChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: '收入',
                            data: data.income,
                            borderColor: '#D4A574',
                            backgroundColor: 'rgba(212, 165, 116, 0.15)',
                            fill: true, tension: 0.3, pointRadius: 3
                        },
                        {
                            label: '支出',
                            data: data.expense,
                            borderColor: '#7C8BA1',
                            backgroundColor: 'rgba(124, 139, 161, 0.15)',
                            fill: true, tension: 0.3, pointRadius: 3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
                        tooltip: {
                            callbacks: {
                                label: ctx => ctx.dataset.label + ': ¥' + ctx.parsed.y.toLocaleString('zh-CN', {minimumFractionDigits: 2})
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString(), font: { size: 10 } } },
                        x: { ticks: { font: { size: 10 } } }
                    }
                }
            });
        })();
```

**Step 2: 验证首页图表**

启动应用，访问首页，确认：
- 导航栏出现"报表"链接
- 统计栏下方出现迷你趋势图
- 点击"查看详情"跳转到 `/reports`

**Step 3: Commit**

```bash
git add src/templates/index.html
git commit -m "feat: 首页添加迷你趋势图和报表导航入口"
```

---

## Task 4: 添加图表相关 CSS 样式

**Files:**
- Modify: `src/static/css/style.css`（文件末尾追加）

**Step 1: 在 `style.css` 末尾添加图表样式**

```css
/* ===== 图表相关样式 ===== */

.chart-section {
    margin-bottom: var(--space-lg);
}

.chart-container {
    position: relative;
    height: 300px;
    padding: var(--space-md);
}

.chart-container-mini {
    height: 200px;
}

.chart-container-pie {
    height: 280px;
}

.chart-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
}

.chart-half {
    margin-bottom: 0;
}

.chart-detail-link {
    font-size: 12px;
    color: var(--color-accent);
    text-decoration: none;
    font-weight: 500;
}

.chart-detail-link:hover {
    color: var(--color-accent-hover);
    text-decoration: underline;
}

/* 响应式：移动端饼图堆叠 */
@media (max-width: 640px) {
    .chart-row {
        grid-template-columns: 1fr;
    }
}
```

**Step 2: 验证样式生效**

访问 `/reports` 页面，确认：
- 折线图高度 300px
- 两个饼图并排显示（移动端堆叠）
- 首页迷你图表高度 200px

**Step 3: Commit**

```bash
git add src/static/css/style.css
git commit -m "feat: 添加图表相关 CSS 样式"
```

---

## Task 5: 端到端验证 & 更新任务状态

**Step 1: 完整功能验证**

启动应用 `cd /Users/candyxiao/ClaudeCode/0225-FamilyFin/src && python3 main.py`

验证清单：
- [ ] 首页统计栏下方显示迷你趋势图
- [ ] 首页导航栏有"报表"链接
- [ ] 点击"查看详情"或"报表"进入 `/reports`
- [ ] 报表页 1/3/6/12 月按钮组切换正常，默认选中 6 月
- [ ] 趋势折线图展示收入和支出两条线
- [ ] 支出构成饼图正确显示
- [ ] 收入构成饼图正确显示
- [ ] 有家庭时，「我的/家庭」视图切换后图表数据更新
- [ ] 无数据时图表不报错，显示空图

**Step 2: 更新 TASKS.md**

将 TASK-005 状态改为 DONE，勾选验收标准。

**Step 3: 最终 Commit**

```bash
git add TASKS.md
git commit -m "docs: 更新 TASK-005 状态为 DONE"
```
