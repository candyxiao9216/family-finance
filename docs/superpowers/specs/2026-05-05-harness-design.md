# Harness 设计文档 — FamilyFin 自动化开发管道

> 日期: 2026-05-05
> 状态: 设计阶段

---

## 1. 目标

为 FamilyFin 建立完整的自动化开发→验证→发版→部署管道，确保：

- main 分支永远是可部署的稳定版本
- 每次发版有质量门保障（测试 + 覆盖率 + 冒烟验证）
- 文档与代码保持同步（自动提醒 + 自动更新）
- 部署零手工操作（一键脚本）

---

## 2. 架构总览

```
start.sh          创建功能分支
    ↓
开发 & commit      在功能分支上工作
    ↓
release.sh        验证 → squash merge → tag → 自动文档 → push
    ↓
deploy.sh         一键部署到腾讯云
    ↓
cleanup.sh        清理已合并分支
```

---

## 3. 分支策略

### 规则
- **禁止**直接在 main 上 commit
- 所有开发在功能分支上进行
- 合并方式：squash merge（N 个 commit → 1 个）
- main 的 git log 保持线性、每个 commit 对应一次发版

### 分支命名
- `feature/xxx` — 功能开发（如 `feature/loan-module`）
- `fix/xxx` — Bug 修复（如 `fix/chart-width`）
- `hotfix/xxx` — 线上紧急修复

---

## 4. 脚本详细设计

### 4.1 start.sh — 分支创建

**用法：**
```bash
./start.sh feature/xxx    # 创建并切换到功能分支
./start.sh fix/xxx        # 创建修复分支
```

**逻辑：**
1. 检查当前是否在 main（如果不在，提示先切回 main）
2. 检查工作区干净（无未提交改动）
3. `git fetch origin && git pull origin main`（同步最新 main）
4. `git checkout -b <branch_name>`（创建本地分支）
5. `git push -u origin <branch_name>`（推送远程 + 设置上游）
6. 打印成功信息

**错误处理：**
- 分支名为空 → 提示用法
- 已在非 main 分支 → 提示先切回 main
- 有未提交改动 → 拒绝，提示 stash 或 commit

---

### 4.2 deploy.sh — 一键部署

**用法：**
```bash
./deploy.sh              # 部署 main 分支到生产
```

**逻辑：**
1. 检查当前在 main 分支
2. 检查本地与远程 main 同步（无未推送的 commit）
3. SSH 到服务器执行：
   ```bash
   ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137 \
     "sudo bash -c 'cd /opt/family-finance && git pull origin main && systemctl restart family-finance'"
   ```
4. 等待 5 秒
5. curl 验证线上服务返回 200/302
6. 打印部署成功 + 版本信息

**错误处理：**
- 不在 main → 拒绝（"请先 release 合并到 main"）
- SSH 失败 → 报错退出
- curl 验证失败 → 警告（服务可能启动中，建议手动检查）

---

### 4.3 release.sh — 发版管道（核心）

**用法：**
```bash
./release.sh patch        # 自动模式（Claude Code 使用）
./release.sh minor        # 自动模式，minor 版本
./release.sh              # 交互模式（手动选择版本号）
```

**完整流程（10 步）：**

#### 阶段一：检查

**① 状态检查**
- 当前不在 main 分支（必须从功能分支发版）
- 无未提交改动
- 功能分支已推送到远程

**② 测试验证**
```bash
cd src && python -m pytest ../tests/ --cov=. --cov-report=term-missing
```
- 全部用例通过 → 继续
- 任何用例失败 → 阻断，打印失败详情
- 全量覆盖率 < 80% → 阻断，打印当前覆盖率和未覆盖文件

**③ 本地冒烟验证**
```bash
# 启动 Flask（后台）
python src/main.py &
PID=$!
sleep 3
# 验证首页可访问
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001)
kill $PID
# 302（重定向登录）或 200 都算通过
```
- 返回 200 或 302 → 通过
- 其他 → 阻断（"本地启动失败，请检查"）

**④ 文档变更提醒**

扫描本次分支相对 main 的改动文件，按规则提醒：

| 改动范围 | 提醒更新 |
|---------|---------|
| `src/routes/` | CLAUDE.md "API 路由设计" 章节 |
| `src/models.py` | CLAUDE.md "数据库设计" 章节 |
| `src/templates/` | CLAUDE.md "系统架构/目录结构" 章节 |
| `src/config.py` 或 `.env*` | CLAUDE.md "开发环境" + 服务器部署信息 |
| `src/services/` | CLAUDE.md 对应服务描述 |
| `requirements.txt` | README.md 依赖说明 |
| `src/static/` | 无需特别提醒 |

输出格式：
```
⚠️  文档变更提醒：
  - 检测到 routes/ 改动 → 请确认 CLAUDE.md API 路由表已更新
  - 检测到 models.py 改动 → 请确认数据库设计章节已更新
  是否已确认文档已同步？[Y/n]
```
- 交互模式：等待用户确认
- 自动模式：打印提醒但不阻断（信任 CLAUDE.md 硬规则已执行）

**⑤ 改动摘要**
```bash
git log main..HEAD --oneline
```
展示本次所有 commit，供 Release Notes 使用。

#### 阶段二：准备

**⑥ 版本号**
- 读取当前版本（从 `PROJECT_BRIEF.md` 或专用 `VERSION` 文件）
- patch: 2.0.0 → 2.0.1
- minor: 2.0.0 → 2.1.0
- major: 2.0.0 → 3.0.0
- 交互模式：展示选项让用户选择
- 自动模式：从命令行参数读取

**⑦ Release Notes 生成**

按 commit message 前缀分类：
```markdown
## v2.0.1 (2026-05-05)

### 新功能
- xxx

### 修复
- xxx

### 文档
- xxx

### 其他
- xxx
```

#### 阶段三：执行

**⑧ Squash Merge**
```bash
git checkout main
git pull origin main
git merge --squash <branch>
git commit -m "release(YYYY-MM-DD): v<version> — <summary>"
```

**⑨ 自动文档更新**

合并到 main 后，自动更新以下内容：

| 文件 | 更新内容 |
|------|---------|
| `CHANGELOG.md` | 追加新版本的 Release Notes |
| `PROJECT_BRIEF.md` | "当前里程碑" 行的版本号 |
| `CLAUDE.md` | "状态: ... (vX.X.X)" 行的版本号 |
| `VERSION` | 纯版本号文件（新建，供脚本读取） |

更新后自动 commit：
```bash
git add -A
git commit -m "docs: 自动更新版本号和 CHANGELOG 至 v<version>"
```

**⑩ Tag + Push**
```bash
git tag v<version>
git push origin main --tags
```

#### 阶段四：收尾

打印完成信息：
```
✅ 发版完成！
  版本: v2.0.1
  分支: feature/xxx → main (squash merged)
  Tag:  v2.0.1
  
  下一步:
  1. ./deploy.sh     — 部署到生产
  2. ./cleanup.sh    — 清理旧分支
```

自动切回功能分支（方便继续开发或清理）。

---

### 4.4 cleanup.sh — 分支清理

**用法：**
```bash
./cleanup.sh            # 清理已合并分支
```

**逻辑：**
1. 切换到 main
2. `git fetch --prune`（同步远程删除状态）
3. 列出已合并到 main 的本地分支（排除 main 自身）
4. 逐一删除本地分支：`git branch -d <branch>`
5. 逐一删除远程分支：`git push origin --delete <branch>`
6. 打印清理结果

---

## 5. 文件结构

新增文件：
```
项目根目录/
├── start.sh              # 分支创建
├── deploy.sh             # 一键部署
├── release.sh            # 发版管道
├── cleanup.sh            # 分支清理
├── VERSION               # 当前版本号（纯文本，如 "2.0.0"）
└── CHANGELOG.md          # 版本变更日志
```

---

## 6. VERSION 文件

新建 `VERSION` 文件，内容为纯版本号：
```
2.0.0
```

所有脚本从这里读取当前版本号。发版时由 release.sh 自动更新。

---

## 7. CHANGELOG.md 格式

```markdown
# 变更日志

## v2.0.1 (2026-05-05)

### 新功能
- feat(harness): 自动化发版管道

### 修复
- fix(css): 图表容器宽度被覆盖

---

## v2.0.0 (2026-04-08)

### 里程碑一：家庭资产数据数字化
- feat(advisor): 智能财务顾问模块
- feat(advisor): 持仓批量导入
- ...
```

---

## 8. 覆盖率策略

### 当前状态
- 现有 19 个测试用例
- 覆盖范围：储蓄计划、宝宝基金、CSV导入
- 未覆盖：routes/（大部分）、main.py、services/、database.py

### 达标路径
第一次成功发版前，需要补充测试到全量 ≥ 80%。建议分批补充：

1. **优先级 1**：models.py（数据模型，纯逻辑，最容易测）
2. **优先级 2**：routes/ 核心路由（auth、account、transaction）
3. **优先级 3**：services/（AI、行情，可 mock 外部 API）
4. **优先级 4**：main.py 仪表盘路由

### 覆盖率豁免
以下文件可排除在覆盖率计算之外（配置在 `pytest.ini` 或 `pyproject.toml`）：
- `src/database.py`（初始化逻辑，难以单测）
- `src/config.py`（纯配置读取）

---

## 9. 开发工作流示例

### 日常开发（修复 CSS 问题）

```bash
# 1. 创建分支
./start.sh fix/chart-width

# 2. 改代码 + 提交
vim src/static/css/style.css
git add . && git commit -m "fix(css): chart-container 宽度被 advisor 样式覆盖"

# 3. 发版
./release.sh patch

# 4. 部署
./deploy.sh

# 5. 清理
./cleanup.sh
```

### 功能开发（贷款模块）

```bash
# 1. 创建分支
./start.sh feature/loan-module

# 2. 多次提交
git commit -m "feat(loan): 数据模型设计"
git commit -m "feat(loan): CRUD 路由"
git commit -m "test(loan): 单元测试"
git commit -m "docs: 更新 CLAUDE.md 数据库设计"

# 3. 发版（所有 commit squash 成一个）
./release.sh minor

# 4. 部署
./deploy.sh

# 5. 清理
./cleanup.sh
```

---

## 10. 与现有工具的关系

| 现有 | 改动 |
|------|------|
| 手动 SSH 部署 | 被 `deploy.sh` 替代 |
| 直接在 main 提交 | 改为功能分支 + squash merge |
| CLAUDE.md 手动更新版本 | release.sh 自动更新 |
| 无 CHANGELOG | release.sh 自动生成 |
| 测试偶尔跑 | release.sh 强制跑 + 覆盖率门 |

---

## 11. 风险和注意事项

1. **第一次发版需要先补测试** — 全量覆盖率要达 80%，现有测试不够。建议先做一个 `feature/add-tests` 分支把覆盖率补上来，然后用 release.sh 做第一次正式发版。

2. **SQLite ALTER TABLE** — 之前反复出现的部署问题。deploy.sh 不解决这个问题（仍需手动 ALTER TABLE）。后续可以考虑集成 Flask-Migrate，但不在本次范围。

3. **Nginx 静态文件缓存** — 已经设为 no-cache，deploy.sh 只需 restart service 不需要额外处理。

4. **脚本权限** — 所有 .sh 文件需要 `chmod +x`。

---

**文档版本:** 1.0.0
**作者:** candyxiao + Claude
