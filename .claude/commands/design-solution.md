---
description: 技术方案设计：读取需求报告，生成 tech-design.md 和 execution-plan.md
argument-hint: [TASK_SLUG]
---

# /design-solution

## 用法
```
/design-solution [TASK_SLUG]
```

## 前置条件
- `.artifacts/devflow/{TASK_SLUG}/01-requirement/requirement-report.md` 存在

## 执行步骤（以架构师角色执行）

### 第一步：读取输入
- 读取 requirement-report.md
- 阅读项目相关代码（最多 20 次文件读取，优先 codebase 搜索）

### 第二步：生成技术方案（tech-design.md）
使用 `tech-design` skill，产出内容包括：
- 方案背景与目标
- 架构设计（Mermaid 图）
- 核心实现路径
- 关键技术决策（选A不选B的理由）
- 数据库/接口变更（如有）
- 性能与安全考量
- 不在范围内的事项

保存到：`.artifacts/devflow/{TASK_SLUG}/02-design/tech-design.md`

### 第三步：生成执行计划（execution-plan.md）
将技术方案拆解为并行任务（PT-01、PT-02…），每个 PT 包含：
- `id`：PT 编号
- `title`：任务名称
- `files_whitelist`：本任务涉及的文件路径（**各 PT 之间必须互不重叠**）
- `pseudocode`：≥5 行伪代码
- `acceptance`：具体可验证的验收标准（PASS/FAIL 型）

**自检**：确认所有 PT 的 files_whitelist 无重叠，PT 数量 ≤ 6。

保存到：`.artifacts/devflow/{TASK_SLUG}/02-design/execution-plan.md`

### 第四步：更新状态
更新 workflow-state.json：`current_stage = "TASK-02"`, `status = "completed"`

**完成后提示**：方案设计完成，可执行 `/develop-code` 进入代码开发。
