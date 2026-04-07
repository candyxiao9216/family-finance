# 开发指南（Development Guide）

> 每次重新开始开发时，按此文件操作。

---

## 一、启动开发环境

```bash
# 进入项目目录
cd /Users/candyxiao/ClaudeCode/0225-FamilyFin

# 启动应用（端口 5001）
python3 src/main.py
```

打开浏览器访问：http://localhost:5001

---

## 二、运行测试

```bash
# 运行核心测试（推荐，每次改完代码先跑这个）
python3 -m pytest tests/test_savings.py tests/test_baby_fund.py tests/test_importers.py tests/test_upload.py -v

# 运行单个测试文件
python3 -m pytest tests/test_savings.py -v

# 运行全部测试
python3 -m pytest tests/ -v
```

---

## 三、提交代码

```bash
git add <改动的文件>
git commit -m "feat: 简短描述"
git push origin main
```

---

## 四、部署到服务器

本地提交并推送后，执行一条命令即可更新线上：

```bash
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137 \
  "sudo bash -c 'cd /opt/family-finance && git pull origin main && systemctl restart family-finance'"
```

线上地址：http://119.91.205.137

---

## 五、服务器运维

```bash
# SSH 登录
ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137

# 以下命令在服务器上执行（需要 sudo）
sudo systemctl status family-finance     # 查看状态
sudo systemctl restart family-finance    # 重启服务
sudo journalctl -u family-finance -f     # 实时日志
sudo tail -f /opt/family-finance/data/error.log  # 应用错误日志
```

---

## 六、项目关键文件

| 文件 | 说明 |
|------|------|
| `src/main.py` | 应用入口 + 主路由 |
| `src/models.py` | 所有数据模型（16 个） |
| `src/database.py` | 数据库配置和初始化 |
| `src/routes/` | 路由蓝图（auth、savings、baby_fund、upload 等） |
| `src/templates/` | HTML 模板 |
| `src/static/css/style.css` | 全局样式 |
| `src/utils/importers.py` | CSV/Excel 解析工具 |
| `src/routes/advisor.py` | 财务顾问蓝图（持仓CRUD + AI分析） |
| `src/services/ai_advisor.py` | AI分析引擎（智谱GLM全系列） |
| `src/services/market_data.py` | 行情数据服务（Sina API） |
| `src/templates/advisor/` | 财务顾问页面模板（6个） |
| `.env` / `.env.example` | AI API密钥配置 |
| `PROJECT_BRIEF.md` | 项目状态总览（每次完成任务后更新） |

---

## 七、用 Claude Code 继续开发

启动新会话后，直接说：

> "帮我看一下 PROJECT_BRIEF.md，继续开发下一步功能"

Claude Code 会自动读取项目状态，知道做到哪了、下一步做什么。
