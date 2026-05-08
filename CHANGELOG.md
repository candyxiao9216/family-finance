# 变更日志

所有版本变更记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/)。

---

## v2.0.11 (2026-05-08)

### 修复
- 账户类型命名统一为"平台+产品类型"格式

---

## v2.0.10 (2026-05-08)

### 新增
- start.sh 重写 — 参考 devHireAI 智能分支创建

### 修复
- README 版本历史保留标题行（修复 tail -n +2 截断）

---

## v2.0.9 (2026-05-08)

### 新增
- release.sh 用户视角 Release Notes + README 版本历史自动更新

---

## v2.0.8 (2026-05-08)

### 文档
- docs: README 版本历史更新至 v2.0.7（用户视角精选）

### 其他
- chore: .gitignore 添加 .DS_Store
- refactor: 项目目录分层整理

---

## v2.0.7 (2026-05-08)

### 文档
- docs: 移除 CLAUDE.md 中的部署信息（IP/SSH 不应公开）
- docs: CLAUDE.md 指令映射增加发版确认流程
- docs: PROJECT_BRIEF.md 精简为 51 行 + release.sh 自动更新 README 版本号

---

## v2.0.6 (2026-05-08)

### 文档
- docs: CLAUDE.md 重写为 147 行操作速查卡

---

## v2.0.5 (2026-05-08)

### 文档
- docs: README 重写（痛点对比+界面截图+功能精简+版本历史链接 CHANGELOG）

### 修复
- fix(css): stats-bar 固定4列改为 auto-fit 自适应列数

### 测试
- test: 新增 stats-bar 列数和 auto-fit CSS 回归测试

---

## v2.0.4 (2026-05-08)

### 修复
- fix(css): 修复 advisor CSS 全局选择器覆盖导致多页面布局挤在左边

---

## v2.0.3 (2026-05-08)

### 修复
- fix(css): chart-container 宽度被 advisor 样式覆盖

---

## v2.0.2 (2026-05-08)

### 其他
- test: 覆盖率达标 81% + 阈值设回 80%
- test: 补充核心路由测试 + 清理冗余测试文件

---

## v2.0.1 (2026-05-08)

### 新功能
- feat(harness): 自动化发版管道脚本

### 修复
- fix(harness): .gitignore 过滤测试文件 + release.sh 精确 add 文档
- fix(harness): release.sh CHANGELOG 多行插入改用临时文件方式

---

## v2.0.0 (2026-04-08)

### 里程碑一：家庭资产数据数字化

#### 新功能
- feat(advisor): 智能财务顾问模块（5页Tab：总览/股票/基金/理财/储蓄）
- feat(advisor): 股票/基金/理财持仓 CRUD 管理
- feat(advisor): AI 分析引擎（智谱 GLM-5-Turbo/GLM-5V-Turbo/GLM-Image）
- feat(advisor): 7 个 AI 分析端点（综合/股票/基金/理财/储蓄）
- feat(advisor): 实时行情（Sina Finance API：港股/A股/美股）
- feat(advisor): 基金排序 + 赎回转投操作
- feat(advisor): 持仓批量导入（Excel 模板 + App 截图 AI 识别）
- feat(advisor): "我的/家庭"视图切换
- feat(dashboard): 首页重做为三模块仪表盘
- feat(transaction): 月度收支独立页面
- feat(checklist): 月度待办 Checklist + 聚焦气泡引导
- feat(account): 资产账户三分类重构（储蓄/基金/股票）
- feat(quick): 快捷模板 + 定期交易自动生成
- feat(multi-currency): 投资账户多币种支持（CNY/HKD/USD）
- feat(savings): 储蓄计划管理 + 宝宝基金记录
- feat(import): CSV/Excel 批量导入（微信/支付宝/标准模板）
- feat(ui): 移动端适配 + Toast + 确认弹窗 + 空状态

#### 修复
- fix(ai): GLM-5 推理模型兼容 + 超时优化
- fix(import): Excel 列名别名映射
- fix(security): 安全扫描修复（暴力破解防护、密码强度、金额校验等）

#### 基础设施
- 腾讯云 Lighthouse 部署（Gunicorn + Nginx）
- 用户认证 + 家庭共享数据模型
- 数据可视化（Chart.js 趋势图/饼图/资产曲线）
