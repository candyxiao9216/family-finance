---
description: 需求分析：通过 brainstorming 对话澄清需求，生成 requirement-report.md
argument-hint: 需求描述
---

# /analyze-requirement

## 用法
```
/analyze-requirement {需求描述}
```

## 执行步骤

### 第一步：初始化产物目录
1. 根据需求描述生成 TASK_SLUG（中文转拼音首字母或英文，下划线连接，≤40字符）
2. 创建目录：`.artifacts/devflow/{TASK_SLUG}/01-requirement/`
3. 初始化 `.artifacts/devflow/{TASK_SLUG}/workflow-state.json`（记录 task_slug、创建时间、当前阶段）

### 第二步：AI 自主需求分析（不与用户交互）
- 阅读项目结构和相关代码（最多 15 次文件读取）
- 识别需求涉及的模块、接口、数据库表、上下游依赖
- 梳理技术约束和兼容性要求

### 第三步：需求澄清对话
使用 `brainstorming` skill 与用户逐步澄清需求：
- 一次只问一个问题
- 优先用选择题
- 澄清完成后生成收敛结论

### 第四步：保存产物
将以下内容写入 `.artifacts/devflow/{TASK_SLUG}/01-requirement/requirement-report.md`：
- 需求背景与目标
- AI 需求分析结果（涉及模块、约束、依赖）
- 澄清 Q&A 记录
- 收敛结论（最终确认的需求范围）
- 明确排除项（不做什么）

更新 workflow-state.json：`current_stage = "TASK-01"`, `status = "completed"`

**完成后提示**：需求分析完成，可执行 `/design-solution` 进入方案设计。
