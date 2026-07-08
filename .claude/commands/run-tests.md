---
description: 测试：为本次变更生成并运行 E2E 测试用例，生成 test-report.md
argument-hint: [TASK_SLUG]
---

# /run-tests

## 用法
```
/run-tests [TASK_SLUG]
```

## 前置条件
- CODE-REVIEW 已通过（review-report.md 结论为 PASSED）

## 执行步骤（以测试工程师角色执行）

### 第一步：定位测试目录
按优先级查找：`tests/` → `test/` → `tests/e2e/` → `tests/integration/`，未找到则创建 `tests/`。

### 第二步：生成测试用例
读取 change-report.md，对每个修改模块/函数编写覆盖以下场景的测试：
- 正常路径（happy path）
- 异常分支（错误输入、边界值）
- 边界条件（最大值、最小值、空值）

使用项目现有测试框架（pytest），不引入新框架。

### 第三步：运行测试
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -n 50
```

### 第四步：生成产物
- `test-report.md`：测试摘要、执行结果、通过率
- `added-cases.md`：本次新增的测试用例列表

保存到：`.artifacts/devflow/{TASK_SLUG}/04-e2e/`
更新 workflow-state.json：`current_stage = "TASK-04"`, `status = "completed"`

**完成后提示**：测试完成，可执行 `/distill-knowledge` 进行知识沉淀。
