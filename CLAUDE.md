# CLAUDE.md — 家庭财务管理系统

> **定位**: 开发者 + Claude 速查卡。完整功能实现历史见 [docs/DEVELOPMENT_LOG.md](./docs/DEVELOPMENT_LOG.md)

---

## 技术栈 & 红线

**技术栈**: Python 3.8+ / Flask 3.0 / SQLAlchemy / SQLite / Chart.js / 智谱 GLM / Sina Finance API

**红线（违反立即停下）:**

- ❌ 严禁在 main 上直接 commit（必须用 `./scripts/start.sh` 创建分支）
- ❌ 严禁硬编码密钥（用 `.env` + `os.getenv`）
- ❌ 严禁不更新文档就提交（代码改了对应文档必须同步）
- ❌ 严禁不备份就部署（`scripts/push-deploy.sh` 已自动备份，手动部署前必须 `./scripts/backup.sh`）
- ❌ 严禁手动发版（必须用 `./scripts/release.sh`，确保测试+覆盖率+tag+CHANGELOG）

---

## 目录结构

```
项目根目录/
├── scripts/             # Harness 脚本
│   ├── start.sh         #   创建功能分支
│   ├── release.sh       #   10步发版管道
│   ├── push-deploy.sh   #   一键部署（自动备份）
│   ├── backup.sh        #   备份线上数据库
│   ├── cleanup.sh       #   清理已合并分支
│   └── deploy.sh        #   服务器从零初始化（只执行一次）
├── src/
│   ├── main.py          # 应用入口 + 仪表盘首页路由
│   ├── models.py        # 数据模型（16 张表）
│   ├── database.py      # 数据库初始化 + Jinja2 过滤器
│   ├── routes/          # Flask 蓝图（12 个）
│   ├── services/        # AI 分析 + 行情数据
│   ├── static/          # CSS + JS
│   └── templates/       # Jinja2 页面模板
├── tests/               # pytest 测试
├── docs/                # 文档
│   ├── DEVELOPMENT_LOG.md
│   ├── screenshots/
│   └── archive/         # 历史文档（不再维护）
├── data/                # SQLite 数据库（运行时生成）
└── backups/             # 线上备份（不入库）
```

---

## 脚本速查

| 命令 | 作用 | 什么时候用 |
|------|------|-----------|
| `./scripts/start.sh feature/xxx` | 从 main 创建功能分支 | 开始任何新工作前 |
| `./scripts/release.sh patch` | 发版：测试→覆盖率→冒烟→squash merge→tag→CHANGELOG | 功能开发完成后 |
| `./scripts/push-deploy.sh` | 备份数据库→SSH推送→重启→验证 | release 之后部署到生产 |
| `./scripts/backup.sh` | 从线上 SCP 下载数据库到 backups/ | 任何时候想备份 |
| `./scripts/cleanup.sh` | 删除已合并的本地+远程分支 | 发版后清理 |

**完整流程**: `scripts/start.sh` → 开发 & commit → `scripts/release.sh` → `scripts/push-deploy.sh` → `scripts/cleanup.sh`

---

## 测试规范

- **覆盖率**: ≥ 80%（硬性，release.sh 会阻断）
- **测试位置**: `tests/` 目录，文件命名 `test_*.py`
- **运行**: `python3 -m pytest tests/ --cov=src --cov-config=pyproject.toml`
- **排除**: database.py, config.py, main.py, migration*, services/ai_advisor.py, services/market_data.py, routes/advisor.py
- **当前状态**: 139+ 测试，覆盖率 81%

---

## 分支策略

| 类型 | 命名 | 场景 |
|------|------|------|
| 功能 | `feature/xxx` | 新功能开发 |
| 修复 | `fix/xxx` | Bug 修复 |
| 紧急 | `hotfix/xxx` | 线上紧急问题 |

合并方式: squash merge（N 个 commit → 1 个），main 保持线性。

---

## Claude 指令映射

| 用户说 | Claude 执行 |
|--------|------------|
| "开个分支做 xxx" | `./scripts/start.sh feature/xxx` 或 `./scripts/start.sh fix/xxx` |
| "提交" / "commit" | `git add` + `git commit` + `git push`（只提交到功能分支，**不发版**） |
| "发版" | 见下方发版流程 |
| "部署" | `./scripts/push-deploy.sh`（会自动备份） |
| "备份" | `./scripts/backup.sh` |
| "修 bug" | `./scripts/start.sh fix/xxx` → 修改 → commit → 等用户确认发版 |
| "加功能" | `./scripts/start.sh feature/xxx` → 开发 → commit → 等用户确认发版 |

**发版流程（必须用户确认）：**
1. Claude 展示：改动摘要 + 版本号 + Release Notes 预览
2. 用户说"确认" → 执行 `./scripts/release.sh patch|minor|major`
3. 用户未确认 → 不执行，继续开发

**硬规则：commit ≠ release。** 做完改动只 commit + push 到功能分支。只有用户明确说"发版"时才跑 release.sh，且必须先展示发版内容让用户确认。

---

## 经验教训

### 1. SQLite 新增字段部署问题（发生 3 次）
- **问题**: 模型新增字段后 `create_all()` 不会给已有表添加新列，导致 500
- **根因**: SQLite 的 `create_all()` 只建不存在的表，不 ALTER
- **方案**: 部署时手动执行 `ALTER TABLE xxx ADD COLUMN yyy`
- **防范**: 每次模型新增字段，CHANGELOG 里注明需要的 ALTER 语句

### 2. Nginx 缓存导致 CSS 不更新
- **问题**: CSS 改了但浏览器还是旧样式
- **根因**: deploy.sh 配了 `expires 7d`
- **方案**: 改为 `expires off; add_header Cache-Control no-cache`
- **防范**: 开发阶段不缓存静态文件

### 3. Advisor CSS 全局选择器覆盖（发生 3 次）
- **问题**: Phase 10 添加的 CSS 用了 `.form-row`、`.card-header`、`.chart-container` 等全局选择器名，覆盖了通用样式
- **根因**: advisor 局部样式没有限定作用域
- **方案**: 改为 `.advisor-container .card-header`、`.add-holding-form .form-row` 等
- **防范**: 新增 CSS 时，如果选择器名已在通用区域存在，必须加父级限定。已有 `test_page_rendering.py` 回归测试

### 4. 服务器重装导致数据丢失
- **问题**: 不小心重装系统，SQLite 数据库没了
- **根因**: 无远程备份机制
- **方案**: 新增 `backup.sh` + `push-deploy.sh` 部署前自动备份
- **防范**: 备份已集成到部署流程，backups/ 目录在本地保留

---

**版本**: v2.0.5
**最后更新**: 2026-05-08
