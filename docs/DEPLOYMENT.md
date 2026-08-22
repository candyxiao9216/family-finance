# 部署拓扑与运维手册

> 记录生产服务器的真实拓扑。**服务器与其他项目共用，改 nginx 前必读本文。**

---

## 服务器信息

| 项 | 值 |
|---|---|
| IP | `119.91.205.137`（腾讯云） |
| 登录 | `ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137` |
| 应用目录 | `/opt/family-finance` |
| 数据库 | `/opt/family-finance/data/family_finance.db` |

---

## ⚠️ 关键：本机共用 nginx，有 3 个站点

服务器上不只有本项目。**改 nginx 时只能碰 `family-finance` 配置，其余一律不动。**

| nginx 站点 | 监听 | server_name（Host） | 后端 | 归属 |
|---|---|---|---|---|
| `ip-workbench` | 80（**默认站点**）/ 443 | `119.91.205.137` | `127.0.0.1:3000` | 其他项目 |
| `workbench` | 80 / 443 | `work.candyxiao.cn` | `127.0.0.1:3000` | 其他项目 |
| `family-finance` | **443 SSL**（80 跳转 HTTPS） | `finance.candyxiao.cn` | `127.0.0.1:5001` | **本项目** |
| `family-finance` | **8080** | `_`（任意 Host，含裸 IP） | `127.0.0.1:5001` | **本项目** |

配置文件位置：
- `/etc/nginx/sites-available/family-finance` ← 本项目，可改
- `/etc/nginx/sites-available/candy-workbench-ip` ← 其他项目，**别动**
- `/etc/nginx/sites-available/candy-workbench` ← 其他项目，**别动**

### 为什么 IP 直连要用 8080 而不是 80

nginx 虚拟主机按 **Host 头**匹配，不是按端口。80 端口的默认站点已被 `ip-workbench` 占用（它把裸 IP 绑成了自己的 `server_name`），所以裸 IP:80 永远到不了本项目。

**不要试图把 family-finance 改成 `listen 80` + `server_name _` 来抢默认站点** —— 那会打乱其他两个站点的路由。`tests/test_deploy_config.py` 会阻止这种改动。

### 为什么不走 `http://IP/finance` 子路径

试过，代价很高：需要给 Flask 加 `ProxyFix` / `APPLICATION_ROOT`，还要改掉模板和 JS 里 **32 处硬编码绝对路径**（`href="/static/..."`、`fetch('/upload/parse')`、`action="/add"` 等）。漏一处就是"页面能开但 CSS 丢失 / 请求 404"。

8080 方案下应用仍挂在根路径，139 处 `url_for` 与所有硬编码路径天然正确，**src/ 零改动**。详见 CLAUDE.md 经验教训 #6。

---

## 访问地址

| 用途 | 地址 |
|---|---|
| 域名（主入口，HTTPS） | https://finance.candyxiao.cn |
| IP 直连（备用，仅健康检查） | http://119.91.205.137:8080 |
| 内部（服务器上自测） | http://127.0.0.1:8080 |

---

## 防火墙：两道，都要放行

8080 端口需要**同时**在两个地方放行，缺一个都访问不了：

**① 服务器 ufw**
```bash
sudo ufw allow 8080/tcp
sudo ufw status          # 确认出现 8080/tcp ALLOW
```

**② 腾讯云安全组**（必须在云控制台点，命令行改不了）

控制台 → 找到 `119.91.205.137` → 防火墙/安全组 → 添加入站规则：

| 协议 | 端口 | 来源 | 策略 |
|---|---|---|---|
| TCP | 8080 | 0.0.0.0/0 | 允许 |

---

## 服务组成

```
浏览器
  │
  ├─ :8080 ──┐
  ├─ :80 (finance.candyxiao.cn) ──┤
  │                                └─→ nginx ─→ gunicorn 127.0.0.1:5001 ─→ Flask
  └─ :80 (裸 IP / work.candyxiao.cn) ─→ nginx ─→ :3000（其他项目）
```

| 组件 | 配置文件 | 管理命令 |
|---|---|---|
| gunicorn | `/opt/family-finance/gunicorn.conf.py` | `systemctl {status,restart} family-finance` |
| systemd | `/etc/systemd/system/family-finance.service` | `systemctl daemon-reload` |
| nginx | `/etc/nginx/sites-available/family-finance` | `nginx -t && systemctl reload nginx` |

**nginx 一律用 `reload` 不用 `restart`** —— restart 会中断其他两个站点的连接。

---

## 改 nginx 配置的标准流程

```bash
CONF=/etc/nginx/sites-available/family-finance
sudo cp $CONF $CONF.bak.$(date +%s)    # 1. 先备份
sudo vi $CONF                           # 2. 改
sudo nginx -t                           # 3. 语法检查（不通过就别继续）
sudo systemctl reload nginx             # 4. 热加载
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/   # 5. 验证，期望 302
```

回退：`sudo cp $CONF.bak.<时间戳> $CONF && sudo nginx -t && sudo systemctl reload nginx`

---

## HTTPS 配置与证书续期

### 当前证书

- **域名**: `finance.candyxiao.cn`
- **证书来源**: 腾讯云免费 SSL 证书（DV，1 年有效期）
- **证书文件位置（服务器）**: `/etc/nginx/ssl/`
  - `finance.candyxiao.cn_bundle.crt`（证书链，644）
  - `finance.candyxiao.cn.key`（私钥，600，owner root）
- **nginx 配置**: `/etc/nginx/sites-available/family-finance`
  含 `listen 443 ssl` 块 + 80 跳转 HTTPS + 8080 IP 直连块

### 应用层配套（已做）

- `SESSION_COOKIE_SECURE=True`：cookie 只在 HTTPS 下发送
- `SESSION_COOKIE_HTTPONLY=True`、`SESSION_COOKIE_SAMESITE=Lax`
- `ProxyFix`：让 Flask 信任 nginx 的 `X-Forwarded-Proto`，否则
  Flask 以为是 HTTP，Secure cookie 不发出 → HTTPS 域名登录不了
- ⚠️ **8080 HTTP 入口在 Secure cookie 模式下无法登录**，只能用于
  部署健康检查（`push-deploy.sh` curl 验证 302）。需要登录走 HTTPS。

### ⚠️ 证书续期（每年一次，重要！）

腾讯云免费 SSL 证书有效期 **1 年**，到期前必须续期，否则 HTTPS 失效、
浏览器报证书错误、用户进不来。

**续期步骤**（到期前 30 天做）：

1. 登录腾讯云控制台 → SSL 证书 → 对旧证书点「续期」或重新申请免费证书
2. 域名填 `finance.candyxiao.cn`，DNS 验证（DNSPod 在腾讯云下可自动验证）
3. 签发后下载 Nginx 版证书，解压得 `finance.candyxiao.cn_bundle.crt` + `.key`
4. 上传到服务器替换：
   ```bash
   scp -i ~/.ssh/candyworkbench.pem <新.crt> <新.key> ubuntu@119.91.205.137:/tmp/
   ssh -i ~/.ssh/candyworkbench.pem ubuntu@119.91.205.137 \
     'sudo mv /tmp/finance.candyxiao.cn_bundle.crt /tmp/finance.candyxiao.cn.key /etc/nginx/ssl/ && \
      sudo chmod 644 /etc/nginx/ssl/finance.candyxiao.cn_bundle.crt && \
      sudo chmod 600 /etc/nginx/ssl/finance.candyxiao.cn.key && \
      sudo chown root:root /etc/nginx/ssl/finance.candyxiao.cn.* && \
      sudo nginx -t && sudo systemctl reload nginx'
   ```
5. 验证：浏览器开 `https://finance.candyxiao.cn`，看🔒锁无警告

**提醒方式**：腾讯云会向申请时填的邮箱发到期提醒；控制台到期前 30 天有提示。

---

## 日常部署

```bash
./scripts/push-deploy.sh    # 自动备份数据库 → git pull → 重启服务 → 验证 :8080
```

**注意：`push-deploy.sh` 不会重跑 nginx 配置**，它只做 `git pull` + 重启 gunicorn。nginx 改动必须手动在服务器上执行（见上一节）。

`deploy.sh` 是**从零重装**用的（只跑一次），日常不要碰。它会覆盖 nginx 配置，跑之前务必确认已备份。

---

## 环境变量

`.env` 位于 `/opt/family-finance/.env`，**不在 git 中**（`.gitignore`）。

| 变量 | 必需 | 说明 |
|---|---|---|
| `SECRET_KEY` | ✅ | 缺失或为默认值时 `create_app()` 拒绝启动（见经验教训 #5） |
| `FLASK_DEBUG` | - | 生产设 `False` |
| `ZHIPU_API_KEY` | - | AI 顾问功能，缺失则该功能不可用 |

`deploy.sh` 会在 `.env` 不存在时自动生成随机 `SECRET_KEY`；**已存在则不覆盖**（覆盖会让所有已登录用户掉线）。

---

## 备份

```bash
./scripts/backup.sh           # 从线上 SCP 数据库到 backups/
./scripts/backup.sh --rotate  # 同时清理旧备份
```

**红线：`backups/` 里的文件绝不 cp 回 `data/`** —— 线上线下数据完全隔离。

---

**最后更新**: 2026-08-08
