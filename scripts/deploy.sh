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
echo "🌐 配置 Nginx..."
cat > /etc/nginx/sites-available/family-finance << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/family-finance/src/static;
        expires 7d;
    }
}
NGINX_EOF

# 启用站点
ln -sf /etc/nginx/sites-available/family-finance /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试并重启 Nginx
nginx -t
systemctl restart nginx

echo "✅ Nginx 已配置"

# 10. 验证
echo ""
echo "========================================="
echo "🎉 部署完成！"
echo "========================================="
echo ""
echo "访问地址: http://$(curl -s ifconfig.me)"
echo ""
echo "常用命令:"
echo "  查看状态:  systemctl status family-finance"
echo "  查看日志:  journalctl -u family-finance -f"
echo "  重启服务:  systemctl restart family-finance"
echo "  更新代码:  cd /opt/family-finance && git pull && systemctl restart family-finance"
echo ""
