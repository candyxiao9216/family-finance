---
description: 知识沉淀：从本次交付产物中提炼可复用经验，追加到知识库
argument-hint: [TASK_SLUG]
---

# /distill-knowledge

## 用法
```
/distill-knowledge [TASK_SLUG]
```

## 执行步骤（以知识工程师角色执行）

### 第一步：收集信息
读取所有已生成的交付产物：
- `01-requirement/requirement-report.md`
- `02-design/tech-design.md`（如有）
- `02-design/execution-plan.md`（如有）
- `03-code/change-report.md`
- `03-code/review-report.md`（如有）
- `04-e2e/test-report.md`（如有）

### 第二步：提炼知识（4 项标准过滤）
每条知识点必须满足：
- **可复用**：对未来类似场景有参考价值
- **具体明确**：包含模块名、函数名、技术术语等上下文
- **结论导向**：直接写结论，不记录讨论过程
- **精简**：1-3 句话，直击要点

### 第三步：分类组织
| 类别 | 内容 |
|------|------|
| 业务知识 | 业务规则、数据流向、模块职责 |
| 技术决策 | 选 A 不选 B 的理由、架构取舍 |
| 改造模式 | 可复用的代码模式 |
| 踩坑记录 | 易错点、陷阱、注意事项 |
| 流程改进 | 本次发现的工作流改进点 |

### 第四步：追加到知识库（只追加，不覆盖）
输出路径：`.artifacts/devflow/knowledge/{TASK_SLUG}.md`

格式：
```markdown
## {TASK_SLUG} - {标题} ({日期})

### 技术决策
- ...

### 踩坑记录
- ...
```

**规则**：文件若已存在，追加新章节；不删除、不覆盖已有内容。

更新 workflow-state.json：`current_stage = "TASK-05"`, `status = "completed"`

**完成后提示**：知识沉淀完成。整个开发流程已全部完成。
