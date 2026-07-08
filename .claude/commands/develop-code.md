---
description: 代码开发：按执行计划实现代码，生成 change-report.md
argument-hint: [TASK_SLUG]
---

# /develop-code

## 用法
```
/develop-code [TASK_SLUG]
```

## 前置条件
- `.artifacts/devflow/{TASK_SLUG}/02-design/execution-plan.md` 存在

## 执行步骤（以开发者角色执行）

### 第一步：读取计划
- 读取 execution-plan.md，理解各 PT 的 files_whitelist、伪代码、验收标准
- 验证各 PT 的 files_whitelist 互不重叠（若有重叠，报错停止）

### 第二步：逐 PT 实现代码
对每个 PT：
1. 只修改该 PT files_whitelist 内的文件（**严禁越界**）
2. 按伪代码实现
3. 逐条验证 acceptance 标准，记录 PASS/FAIL

### 第三步：自检
- 运行测试：`python3 -m pytest tests/ -q`（Python）
- 扫描安全问题：SQL 注入、硬编码密钥、XSS 等

### 第四步：生成 change-report.md
内容包括：
- 各 PT 实现摘要（PT 编号、标题、修改文件数）
- 修改文件清单（含行数变化）
- 验收验证结果表：

| PT | 验收项 | 结果 | 说明 |
|----|--------|------|------|
| PT-01 | xxx | PASS | ... |

- 自检结果（测试通过情况、安全扫描）
- 已知问题或延后事项

保存到：`.artifacts/devflow/{TASK_SLUG}/03-code/change-report.md`

更新 workflow-state.json：`current_stage = "TASK-03"`, `status = "completed"`

**完成后提示**：代码开发完成，可执行 `/review-code` 进入代码审查。
