#!/bin/bash
# ============================================
# 家庭财务管理系统 - 一键部署脚本
# 在服务器上执行：bash deploy.sh
# ============================================

set -e

echo "🚀 开始部署家庭财务管理系统..."

# 1. 安装系统依赖
echo "📦 安装系统依赖..."
apt update -y
apt install -y python3 python3-pip python3-venv nginx git

# 2. 创建应用目录和用户
echo "👤 配置应用目录..."
mkdir -p /opt/family-finance
cd /opt/family-finance

# 3. 从 GitHub 克隆代码
echo "📥 克隆代码..."
if [ -d ".git" ]; then
    echo "已存在 Git 仓库，执行 pull..."
    git pull origin main
else
    git clone https://github.com/candyxiao9216/family-finance.git .
fi

# 4. 创建虚拟环境并安装依赖
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 5. 创建数据目录
mkdir -p data

# 5.5 创建 .env（若不存在）
# 注意：create_app() 会在 SECRET_KEY 缺失或为默认值时拒绝启动，
# 而 .env 在 .gitignore 中不会被 clone 下来，因此必须在初始化数据库前生成。
if [ ! -f /opt/family-finance/.env ]; then
    echo "🔑 生成 .env 与随机 SECRET_KEY..."
    cat > /opt/family-finance/.env << ENV_EOF
SECRET_KEY=$(openssl rand -hex 32)
FLASK_DEBUG=False
ENV_EOF
    chmod 600 /opt/family-finance/.env
    echo "⚠️  ZHIPU_API_KEY 未设置，AI 顾问功能不可用。需要时手动追加到 .env。"
else
    echo "✓ .env 已存在，保留原值（不覆盖 SECRET_KEY，避免已登录用户失效）"
fi

# 6. 初始化数据库
echo "💾 初始化数据库..."
cd src
python3 -c "
import sys
sys.path.insert(0, '.')
from database import create_app, init_database
app = create_app()
init_database(app)
print('数据库初始化完成')
"
cd ..

# 7. 创建 Gunicorn 配置
echo "⚙️ 创建 Gunicorn 配置..."
cat > gunicorn.conf.py << 'GUNICORN_EOF'
import multiprocessing

bind = "127.0.0.1:5001"
workers = 2
worker_class = "sync"
timeout = 120
accesslog = "/opt/family-finance/data/access.log"
errorlog = "/opt/family-finance/data/error.log"
loglevel = "info"
chdir = "/opt/family-finance/src"
GUNICORN_EOF

# 8. 创建 systemd 服务
echo "🔧 配置 systemd 服务..."
cat > /etc/systemd/system/family-finance.service << 'SERVICE_EOF'
[Unit]
Description=Family Finance Management System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/family-finance
Environment="PATH=/opt/family-finance/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/opt/family-finance/venv/bin/gunicorn -c gunicorn.conf.py main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable family-finance
systemctl restart family-finance

echo "✅ Gunicorn 服务已启动"

# 9. 配置 Nginx 反向代理
#
# 端口/域名分配（详见 docs/DEPLOYMENT.md）：
#   本机可能与其他项目共用 nginx。历史事故：本脚本原先写
#   `listen 80` + `server_name _`，会抢占默认站点、打乱其他项目路由。
#   现在改为：8080 端口作 IP 直连入口，80 端口只绑本项目域名。
echo "🌐 配置 Nginx..."

NGINX_CONF=/etc/nginx/sites-available/family-finance
DOMAIN="${DOMAIN:-finance.candyxiao.cn}"

# 保护闸：检测同一 nginx 上的其他站点，避免误覆盖
OTHER_SITES=""
for site in /etc/nginx/sites-enabled/*; do
    [ -e "$site" ] || continue
    name=$(basename "$site")
    [ "$name" = "family-finance" ] && continue
    OTHER_SITES="${OTHER_SITES}     - ${name}"$'\n'
done
if [ -n "$OTHER_SITES" ]; then
    echo "⚠️  检测到同一 nginx 上还有其他站点："
    printf '%s' "$OTHER_SITES"
    echo "   本脚本只写 $NGINX_CONF，不会修改上述站点。"
    echo "   但请确认 8080 端口未被它们占用。"
    read -r -p "   继续配置？(yes/no) " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "已取消 Nginx 配置。Gunicorn 服务仍在 127.0.0.1:5001 运行。"
        exit 1
    fi
fi

# 覆盖前无条件备份（含 certbot 生成的 HTTPS 配置）
if [ -f "$NGINX_CONF" ]; then
    BACKUP_CONF="${NGINX_CONF}.bak.$(date +%s)"
    cp "$NGINX_CONF" "$BACKUP_CONF"
    echo "✓ 原配置已备份到 $BACKUP_CONF"
    if grep -q "listen 443" "$NGINX_CONF"; then
        echo "⚠️  原配置含 HTTPS（可能由 certbot 管理），覆盖后需重新执行 certbot 或手动合并。"
    fi
fi

cat > "$NGINX_CONF" << NGINX_EOF
# IP 直连入口：不依赖域名，避免与同机其他站点争抢 80 端口默认站点
server {
    listen 8080;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /opt/family-finance/src/static;
        # 开发阶段不缓存静态文件（见 CLAUDE.md 经验教训 #2）
        expires off;
        add_header Cache-Control "no-cache";
    }
}

# 域名入口：80 端口只绑本项目域名，不使用 server_name _
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /opt/family-finance/src/static;
        expires off;
        add_header Cache-Control "no-cache";
    }
}
NGINX_EOF

# 启用站点（不删除 sites-enabled/default，避免影响同机其他站点的兜底行为）
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/

# 测试并热加载 Nginx（用 reload 而非 restart，不中断其他站点的连接）
nginx -t
systemctl reload nginx

echo "✅ Nginx 已配置"
echo "   IP 直连: http://<服务器IP>:8080  （需放行 8080：ufw allow 8080/tcp + 云安全组）"
echo "   域名访问: http://${DOMAIN}"

# 10. 验证
echo ""
echo "========================================="
echo "🎉 部署完成！"
echo "========================================="
echo ""
echo "访问地址:"
echo "  IP 直连:  http://$(curl -s ifconfig.me):8080"
echo "  域名:     http://${DOMAIN}"
echo ""
echo "⚠️  首次部署请确认 8080 已放行:"
echo "  服务器防火墙: ufw allow 8080/tcp"
echo "  云安全组:     入站规则 TCP:8080（需在云控制台操作）"
echo ""
echo "常用命令:"
echo "  查看状态:  systemctl status family-finance"
echo "  查看日志:  journalctl -u family-finance -f"
echo "  重启服务:  systemctl restart family-finance"
echo "  更新代码:  cd /opt/family-finance && git pull && systemctl restart family-finance"
echo ""
