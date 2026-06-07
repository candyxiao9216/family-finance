# 项目简报（Project Brief）

> Claude 上下文恢复用。完整操作指南见 [CLAUDE.md](./CLAUDE.md)。

## 目标
构建自部署、隐私优先的家庭财务管理工具：记账 · 资产追踪 · AI 投资分析 · 家庭协作。

## 非目标
- 不做银行账户自动同步
- 不做第三方支付集成
- 不做用户间权限隔离（家庭内共享）

## 技术约束
Python 3.8+ / Flask / SQLAlchemy / SQLite / Chart.js / 智谱 GLM / Gunicorn + Nginx

## 当前状态
- **版本**: v2.1.5
- **里程碑一已完成**: 家庭资产数据数字化（记账+资产+储蓄+AI顾问+持仓+行情）
- **harness 已建立**: start → release → deploy 全自动化
- **测试**: 139+ 用例，覆盖率 81%

## 已知技术债
- CSRF 防护缺失（家庭内部使用，风险低）
- 文件上传缺 MIME 校验
- 无数据库迁移工具（ALTER TABLE 手动执行）

## 下一步
1. 贷款管理模块
2. 数据导出（CSV/PDF 报表）
3. 暗色模式
4. 更多 AI 场景（税务优化、退休规划）

## 运行
```bash
# 本地
pip install -r requirements.txt && python3 src/main.py
# 访问 http://localhost:5001

# 部署
./push-deploy.sh

# 发版
./start.sh feature/xxx → 开发 → ./release.sh patch → ./push-deploy.sh
```

## 关键路径
- `src/main.py` — 入口 + 仪表盘
- `src/routes/advisor.py` — 最大文件（590行，AI 顾问）
- `src/models.py` — 16 张表
- `src/static/css/style.css` — 全局样式（注意 advisor 区域选择器作用域）
- `CLAUDE.md` — 操作速查卡
