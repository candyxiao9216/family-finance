# 家庭财务管理系统

一个智能家庭财务管理工具，帮助追踪收支、管理资产持仓、AI 智能分析投资组合。

## 功能特性

### 核心记账
- 收入/支出记录（手动录入 + 快捷模板 + 定期交易自动生成）
- 自定义分类管理
- CSV/Excel 批量导入（微信/支付宝账单 + 标准模板）
- 月度收支统计和分页

### 资产管理
- 多账户管理（储蓄/基金理财/股票三分类）
- 多币种支持（CNY/HKD/USD + 实时汇率换算）
- 月度余额快照 + 批量录入
- 资产趋势图

### 智能财务顾问 🤖
- **持仓管理**: 股票/基金/理财产品 CRUD
- **AI 分析**: 智谱GLM全系列（GLM-5文本 + GLM-5V-Turbo多模态 + GLM-Image图像）
- **7个分析端点**: 综合分析/股票整体+个股/基金整体+个基/理财/储蓄
- **实时行情**: Sina Finance API（港股/A股/美股）
- **资产配置**: 实时聚合分析 + 饼图展示
- **分析历史**: 永久保存 + 类型筛选 + Markdown全文展开
- **视图切换**: "我的/家庭"视图切换（与资产总览交互一致）
- **视图切换**: "我的/家庭"视图切换（与资产总览交互一致）

### 储蓄与宝宝基金
- 储蓄计划追踪（月度/年度目标 + 进度条）
- 宝宝基金记录（自动生成收入交易 + 级联操作）

### 体验细节
- 首页三模块仪表盘（收支+资产+储蓄概览）
- 移动端适配（底部Tab + 汉堡菜单 + 响应式）
- 财务数据隐藏（小眼睛，默认隐藏）
- 月度待办 Checklist + 聚焦气泡引导
- 所有金额千分位格式化

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Python Flask |
| 数据库 | SQLite |
| 前端样式 | 原生 CSS（变量 + 媒体查询） |
| 数据可视化 | Chart.js |
| AI 模型 | 智谱GLM（GLM-5 / GLM-5V-Turbo / GLM-Image） |
| 行情数据 | Sina Finance API |
| 部署 | Gunicorn + Nginx |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 AI_API_KEY（智谱开放平台密钥）
```

### 3. 运行应用

```bash
python src/main.py
```

访问 http://localhost:5001

## 项目结构

```
src/
├── main.py                # Flask 应用入口 + 仪表盘首页
├── models.py              # 16 个数据模型
├── database.py            # 数据库配置和初始化
├── config.py              # 配置管理
├── routes/                # Flask 蓝图（12个）
│   ├── advisor.py         # 智能财务顾问（持仓CRUD + AI分析 + 历史）
│   ├── transaction.py     # 月度收支
│   ├── account.py         # 资产总览
│   ├── savings.py         # 储蓄计划
│   └── ...                # auth/category/baby_fund/upload/family/template/recurring/monthly_todo
├── services/              # 业务服务层
│   ├── ai_advisor.py      # AI 分析引擎（智谱GLM全系列）
│   └── market_data.py     # 行情数据（Sina API + 缓存）
├── utils/
│   └── importers.py       # CSV/Excel 解析
├── static/
│   ├── css/style.css      # 全局样式
│   └── js/app.js          # 公共交互（菜单/Toast/AI抽屉/小眼睛）
└── templates/             # Jinja2 模板
    ├── base.html          # 公共模板
    ├── advisor/           # 财务顾问6个页面
    └── ...                # 其他页面模板
```

## 部署

已部署到腾讯云 Lighthouse，使用 Gunicorn + Nginx：

```bash
# 服务器更新
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137
sudo -i
cd /opt/family-finance && git pull origin main && systemctl restart family-finance
```

## 许可

MIT License
