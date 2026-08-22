# CLAUDE.md — 家庭财务管理系统

> **定位**: 开发者 + Claude 速查卡。完整功能实现历史见 [docs/DEVELOPMENT_LOG.md](./docs/DEVELOPMENT_LOG.md)

---

## 技术栈 & 红线

**技术栈**: Python 3.8+ / Flask 3.0 / SQLAlchemy / SQLite / Chart.js / 智谱 GLM / Sina Finance API

**红线（违反立即停下）:**

- ❌ **绝对禁止在 main 上 commit 任何改动 — 无例外，包括"一行小改动"、"只是文档"、"只是脚本"。必须先 `./scripts/start.sh`，哪怕改动再小。Claude 每次执行 git commit 前必须检查 `git branch --show-current`，如果是 main 则停下来开分支。**
- ❌ **线上线下数据完全隔离 — 禁止用线上数据覆盖本地 `data/family_finance.db`，禁止未经用户授权修改线上数据。`backup.sh` 只存档到 `backups/`，绝不 cp 到 `data/`。**
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
│   ├── models.py        # 数据模型（24 张表）
│   ├── database.py      # 数据库初始化 + Jinja2 过滤器
│   ├── routes/          # Flask 蓝图（14 个）
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
- **排除**: database.py, config.py, main.py, services/ai_advisor.py, services/market_data.py, routes/advisor.py
- **当前状态**: 185 测试，覆盖率 81%

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

### 5. 生产环境使用公开默认 SECRET_KEY
- **问题**: 生产 `.env` 的 `SECRET_KEY` 等于代码里写死的默认值 `dev-secret-key-change-in-production`，而该值在公开 GitHub 仓库可见。任何人都能伪造 session cookie 冒充任意成员登录
- **根因**: `config.py` 用 `os.environ.get('SECRET_KEY', '默认值')` 静默兜底，缺失时不报错；注释里的"安全提醒"无强制力
- **方案**: 已轮换生产 key（随机 64 字符）；`create_app()` 增加启动安全闸——key 缺失或为默认值时 `raise RuntimeError` 拒绝启动
- **防范**: 配置不安全就拒绝启动而非降级。新增的需"只生产强制"的校验，注意放在 `create_app()` 而非 config import 层（避免 conftest 导入即触发）

### 6. 多站点共用 nginx 导致 IP 无法访问（2026-08-08）
- **问题**: 裸 IP `http://119.91.205.137` 打不开家庭财务系统，一直显示另一个项目
- **根因**: 服务器上同时跑着 3 个站点。family-finance 的 nginx 只绑了域名 `finance.candyxiao.cn`，裸 IP 请求命中的是默认站点 `ip-workbench`（转发到 :3000 的另一个应用）。nginx 虚拟主机按 Host 头匹配，跟"端口通不通"无关
- **踩坑过程**: 曾尝试改成 `http://IP/finance` 子路径而卡死。子路径需要同时改两处才能work——① Flask 加 `ProxyFix`/`APPLICATION_ROOT`（项目完全没有）② 改掉模板和 JS 里 **32 处硬编码绝对路径**（`href="/static/..."`、`fetch('/upload/parse')`、`action="/add"` 等）。只改一边的症状是"首页能开但 CSS 丢失 / 链接 404"
- **方案**: 改用 **8080 独立端口**。应用仍挂在根路径 `/`，139 处 `url_for` 和 32 处硬编码路径全部天然正确，**src/ 零改动**
- **防范**:
  - `deploy.sh` 不再使用 `listen 80` + `server_name _`（会抢占默认站点、打乱其他项目路由）；80 端口只绑具体域名，IP 直连走 8080
  - `deploy.sh` 不再 `rm sites-enabled/default`，nginx 用 `reload` 而非 `restart`（避免中断其他站点）
  - `push-deploy.sh` 健康检查改为 `http://IP:8080`——原先打裸 IP 等于在验证别人的项目，是假绿灯
  - `tests/test_deploy_config.py` 守护上述不变量
  - 部署拓扑与端口分配 → 见 [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

### 7. IDOR 越权大面积缺失 + 测试自我安慰（2026-08-20 体检）
- **问题**: 系统体检发现 5 个 blueprint 共 18 个写路由不校验资源归属，转账不校验账户归属，注册接口对公网开放。陌生人自助注册即可遍历 id 删改全站所有家庭的财务数据。同时覆盖率 81% 是"自我安慰"——main.py（566 行）和 advisor.py（1221 行）被 omit，真实覆盖率约 55%，而两个最大的文件恰好各藏一个 IDOR
- **根因**: 只在 `before_request` 做了"是否登录"的全局闸，没在路由内做"资源是否属于你"的对象级授权（IDOR）。转账 add/edit/delete 写 `AccountBalance` 的逻辑各写一遍，导致同一 bug 修两次（v2.1.13/14）还漏第三处。测试用 conftest 自建 app 但漏注册 `before_request`，且 `test_main_routes.py` 抄了 index/add 副本已与真代码漂移，断言与真行为相反却全绿
- **方案**:
  - 新增 `src/utils/auth.py` 的 `is_owner_or_family` 统一权限 helper，21 处写路由补归属校验
  - 转账写 AccountBalance 抽成 `_apply_transfer_balance`/`_remove_transfer_balance` 共用，add/edit/delete 三处统一
  - 注册默认要求邀请码（`ALLOW_SELF_REGISTER_FAMILY` 逃生口）
  - conftest 注册 `require_login`，测试 app 与生产一致
  - API 未登录返回 401 JSON 而非 302 跳登录（前端 fetch 能区分）
- **防范**:
  - 新增写路由（带 id 参数的 POST）**必须**加归属校验，复用 `is_owner_or_family`
  - 新增资源的归属字段若是 `created_by` 而非 `user_id`，helper 传 `field=` 参数
  - 同一逻辑在多处出现时**抽 helper**，别复制粘贴（transfer 写余额是教训）
  - 测试要用真路由（conftest 已注册 `/add`/`/edit`/`/delete`），不要抄副本
  - `tests/test_idor.py` 的两用户越权测试模式可复用：B 操作 A 的资源断言被拒且 A 数据不变

### 8. 覆盖率 omit 的真实代价（2026-08-20 体检）
- **问题**: `pyproject.toml` 把 `main.py`/`advisor.py` 整体 omit，81% 覆盖率数字掩盖了关键路径空洞。移出后 main.py 仅 61%，总覆盖率跌至 79% 跌破门槛
- **根因**: "排除了难测的文件"的决策，代价是两个最严重的越权点恰好落在两个盲区里。`release.sh` 用这个虚高数字做发版卡口，等于放行
- **当前状态**: 暂未移出 omit（移出会卡发版）。待 `test_main_routes.py` 重写覆盖 main.py 后再移除
- **待办（不紧急，单独批次）**:
  - P1-9: 重写 `test_main_routes.py`，删 main_app 影子实现，改用 conftest 真 app
  - P1-10: main.py/advisor.py 移出 omit（advisor 拆分：持仓 CRUD 纳入覆盖，AI 端点留 omit）
  - `release.sh:115` 覆盖率提取失败降级为 100 的 fail-open 改为 fail

### 9. HTTPS + Secure cookie + ProxyFix 三件套（2026-08-22）
- **背景**: 域名 `finance.candyxiao.cn` 备案下来后上 HTTPS（腾讯云 SSL 证书）
- **坑**: 光配 nginx 443 不够。开了 `SESSION_COOKIE_SECURE=True` 后，Flask 默认不信任 nginx 的 `X-Forwarded-Proto` 头，以为自己在 HTTP → Secure cookie 不发出 → **HTTPS 域名也登录不了**（登录后立即被踢回登录页）
- **方案**: 三件套缺一不可
  - nginx: `listen 443 ssl` + `X-Forwarded-Proto $scheme` + 80 跳转 HTTPS
  - 应用: `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE` 配置
  - 应用: `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` 让 Flask 信任反代头
- **权衡**: 开 Secure 后 **8080 HTTP 入口无法登录**（cookie 不在 HTTP 下传），但 8080 仍可用于部署健康检查（curl 验 302）。需要登录走 HTTPS
- **证书续期**: 腾讯云免费 SSL 有效期 1 年，到期前 30 天须续期，否则 HTTPS 失效。续期步骤见 [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)「HTTPS 配置与证书续期」
- **备案合规**: 页脚必须显示备案号（粤ICP备2026120681号-1），否则可能被注销备案。已在 `base.html`/`auth_base.html` 加 `.site-footer`

---

**版本**: v2.1.25
**最后更新**: 2026-08-22
