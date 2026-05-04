# Harness 实施计划 — FamilyFin 自动化开发管道

> 日期: 2026-05-05
> 对应设计: docs/superpowers/specs/2026-05-05-harness-design.md

---

## 实施顺序

按依赖关系排列，前面的步骤是后面的前置条件。

---

## Step 1：创建基础文件（VERSION + CHANGELOG）

**预计时间：5 分钟**

### 任务
1. 创建 `VERSION` 文件，内容为 `2.0.0`
2. 创建 `CHANGELOG.md`，回填 v2.0.0 里程碑条目（从现有 git log 生成）

### 验收标准
- [x] `cat VERSION` 输出 `2.0.0`
- [x] `CHANGELOG.md` 包含 v2.0.0 条目，格式符合设计文档第 7 节

### 涉及文件
- `VERSION`（新建）
- `CHANGELOG.md`（新建）

---

## Step 2：start.sh — 分支创建脚本

**预计时间：15 分钟**

### 任务
1. 编写 `start.sh`
2. 处理所有错误场景（无参数、不在 main、有未提交改动）
3. `chmod +x`

### 验收标准
- [ ] `./start.sh` 无参数时打印用法提示
- [ ] 在 main 分支执行 `./start.sh feature/test` 能创建并切换分支
- [ ] 在非 main 分支执行时拒绝并提示
- [ ] 有未提交改动时拒绝并提示

### 涉及文件
- `start.sh`（新建）

---

## Step 3：deploy.sh — 一键部署脚本

**预计时间：15 分钟**

### 任务
1. 编写 `deploy.sh`
2. SSH 到服务器执行 git pull + restart
3. curl 验证线上服务可访问

### 验收标准
- [ ] 不在 main 时拒绝执行
- [ ] 成功部署后 curl 返回 200/302
- [ ] SSH 失败时报错退出
- [ ] 打印部署成功信息 + 当前版本号

### 涉及文件
- `deploy.sh`（新建）

### 依赖
- Step 1（需要 VERSION 文件）

---

## Step 4：release.sh — 发版管道

**预计时间：60 分钟**（最复杂的脚本）

### 任务
1. 编写 release.sh 框架（10 步流程）
2. 实现检查阶段：状态检查 + pytest + 覆盖率 + 冒烟验证 + 文档提醒
3. 实现准备阶段：版本号递增 + Release Notes 生成
4. 实现执行阶段：squash merge + 文档自动更新 + tag + push
5. 实现收尾：打印完成信息
6. 支持交互模式和自动模式（参数传入版本类型）

### 验收标准
- [ ] `./release.sh` 无参数进入交互模式
- [ ] `./release.sh patch` 自动模式执行
- [ ] pytest 失败时阻断
- [ ] 覆盖率 < 80% 时阻断并打印数值
- [ ] 本地 Flask 启动失败时阻断
- [ ] 文档变更提醒正确触发（改 routes/ 提醒 API 文档）
- [ ] squash merge 后 main 只多一个 commit
- [ ] CHANGELOG.md 自动追加新版本条目
- [ ] VERSION / PROJECT_BRIEF.md / CLAUDE.md 版本号自动更新
- [ ] tag 正确创建并推送

### 涉及文件
- `release.sh`（新建）

### 依赖
- Step 1（VERSION + CHANGELOG）
- Step 2（验证分支策略正确）

---

## Step 5：cleanup.sh — 分支清理脚本

**预计时间：10 分钟**

### 任务
1. 编写 `cleanup.sh`
2. 清理本地 + 远程已合并分支

### 验收标准
- [ ] 已合并分支被正确列出并删除
- [ ] main 分支不会被删除
- [ ] 远程分支同步清理
- [ ] 无已合并分支时打印"无需清理"

### 涉及文件
- `cleanup.sh`（新建）

---

## Step 6：pytest 配置 + 覆盖率基础设施

**预计时间：15 分钟**

### 任务
1. 创建 `pyproject.toml`（或 `pytest.ini`）配置 pytest + coverage
2. 配置覆盖率排除文件（database.py、config.py）
3. 安装 pytest-cov 到 requirements.txt
4. 验证 `pytest --cov` 能正常运行并输出覆盖率报告

### 验收标准
- [ ] `pip install -r requirements.txt` 包含 pytest-cov
- [ ] `pytest tests/ --cov=src --cov-report=term-missing` 能执行
- [ ] database.py 和 config.py 被排除在覆盖率计算之外
- [ ] 输出当前实际覆盖率数值（用于评估后续需补多少测试）

### 涉及文件
- `pyproject.toml`（新建或修改）
- `requirements.txt`（添加 pytest-cov）

---

## Step 7：补充测试用例（达到 80% 覆盖率）

**预计时间：2-4 小时**（独立分支完成）

### 任务
按优先级补充：
1. `src/models.py` — 数据模型单元测试
2. `src/routes/auth.py` — 认证路由测试
3. `src/routes/account.py` — 账户路由测试
4. `src/routes/transaction.py` — 月度收支路由测试
5. `src/main.py` — 首页仪表盘路由测试
6. `src/services/` — AI 和行情服务测试（mock 外部 API）

### 验收标准
- [ ] `pytest --cov` 全量覆盖率 ≥ 80%
- [ ] 所有测试通过
- [ ] mock 外部依赖（智谱 API、Sina API、汇率 API）

### 涉及文件
- `tests/` 目录下新增多个测试文件

### 备注
这一步工作量最大。可以作为独立的 `feature/add-tests` 分支完成，也是 harness 建成后的**第一次正式发版**。

---

## Step 8：首次正式发版（验证完整流程）

**预计时间：15 分钟**

### 任务
1. 在 `feature/harness-setup` 分支完成以上所有改动
2. 使用 `./release.sh patch` 执行第一次发版
3. 验证所有环节正常工作
4. 使用 `./deploy.sh` 部署到生产
5. 使用 `./cleanup.sh` 清理分支

### 验收标准
- [ ] release.sh 10 步全部顺利通过
- [ ] main 分支多了一个 squash commit
- [ ] CHANGELOG.md 有新条目
- [ ] VERSION 更新为 2.0.1
- [ ] tag v2.0.1 存在
- [ ] 线上服务正常
- [ ] 旧分支已清理

---

## Step 9：更新项目文档

**预计时间：15 分钟**

### 任务
1. CLAUDE.md — 添加 harness 脚本说明到"系统架构/目录结构" + 新增"开发工作流"章节
2. PROJECT_BRIEF.md — "运行方式"章节添加脚本用法
3. README.md — 添加开发流程说明

### 验收标准
- [ ] CLAUDE.md 包含 4 个脚本的用法说明
- [ ] PROJECT_BRIEF.md 运行方式包含 `./start.sh`、`./release.sh`、`./deploy.sh`
- [ ] 新人看文档就知道怎么用 harness

### 涉及文件
- `CLAUDE.md`
- `PROJECT_BRIEF.md`
- `README.md`

---

## 实施策略

### 执行顺序
```
Step 1-6：在 feature/harness-setup 分支一次性完成
    ↓
Step 7：在 feature/add-tests 分支补测试（可独立，也可合入 harness-setup）
    ↓
Step 8：用 release.sh 首次发版（验证 harness 自身）
    ↓
Step 9：更新文档
```

### 注意事项
- Step 7 是最耗时的。如果想快速跑通流程，可以先把覆盖率门槛临时调低（如 50%），验证 harness 脚本本身没问题后，再补测试到 80%。
- 首次发版前，项目还在 main 上。需要先 commit 现有改动（设计文档），然后从那个点开始用 start.sh 创建分支。

---

**文档版本:** 1.0.0
**作者:** candyxiao + Claude
