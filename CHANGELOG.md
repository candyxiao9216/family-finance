# 变更日志

所有版本变更记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/)。

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
