---
description: 代码审查：检查变更代码的质量、安全性，生成 review-report.md
argument-hint: [TASK_SLUG]
---

# /review-code

## 用法
```
/review-code [TASK_SLUG]
```

## 前置条件
- `.artifacts/devflow/{TASK_SLUG}/03-code/change-report.md` 存在

## 执行步骤（以代码审查员角色执行）

### 第零步：前置硬校验（必须全部通过才进入审查）
1. **边界校验**：change-report.md 中的实际修改文件 ⊆ execution-plan.md 所有 PT 的 files_whitelist 合集
2. **验收完成度**：change-report.md 的验收结果表中所有条目均为 PASS
3. **产物完整性**：change-report.md 存在且非空

任一未通过 → 直接判定 FAILED，说明具体失败原因，不进行后续代码审查。

### 第一步：收集变更信息
读取：change-report.md、tech-design.md、execution-plan.md

### 第二步：逐文件代码审查
审查维度：
- **代码规范**：命名、格式、注释、函数长度
- **安全性**：SQL 注入、XSS、硬编码密钥、输入校验、权限检查
- **性能**：N+1 查询、缺失索引、大数据量处理、内存泄漏
- **架构一致性**：是否符合设计、是否引入不合理依赖
- **错误处理**：异常捕获、降级策略、日志规范

### 第三步：生成 review-report.md

```markdown
## 审查结论
- 结果：PASSED / FAILED
- 审查文件数：N
- 问题汇总：P0: X，P1: Y，P2: Z

## P0 必须修复
### [CR-001] 问题标题
- 文件：path/to/file.py:行号
- 类别：安全性 / 数据安全
- 描述：...
- 建议修复：...

## P1 必须修复
...

## P2 建议（可选）
...
```

**判定规则**：无 P0 且无 P1 → PASSED；有任意 P0 或 P1 → FAILED

保存到：`.artifacts/devflow/{TASK_SLUG}/03-code/review-report.md`
更新 workflow-state.json：`current_stage = "CODE-REVIEW"`, `review_result = "passed/failed"`

**完成后提示**：
- PASSED → 可执行 `/run-tests`
- FAILED → 请根据 P0/P1 修复代码后重新执行 `/review-code`
