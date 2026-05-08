#!/usr/bin/env bash
# push-deploy.sh — 本地一键部署到生产环境
# 用法: ./push-deploy.sh
#
# 注意: deploy.sh 是服务器上从零安装的初始化脚本（只执行一次）
#       push-deploy.sh 是日常更新部署脚本（从本地触发）

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER_IP="119.91.205.137"
SSH_KEY="$HOME/.ssh/candyworkbench.pem"
APP_DIR="/opt/family-finance"

# 检查是否在 main 分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}✗ 当前在 '$CURRENT_BRANCH' 分支，只能从 main 部署。${NC}"
    echo "  请先执行 ./release.sh 合并到 main。"
    exit 1
fi

# 检查本地是否与远程同步
git fetch origin --quiet
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
    echo -e "${YELLOW}⚠ 本地 main 与远程不同步，先推送...${NC}"
    git push origin main
fi

# 读取版本号
VERSION=$(cat "$(git rev-parse --show-toplevel)/VERSION" 2>/dev/null || echo "unknown")

# 部署前自动备份数据库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo -e "${YELLOW}⟳ 部署前备份数据库...${NC}"
if "$SCRIPT_DIR/backup.sh" --rotate; then
    echo ""
else
    echo -e "${YELLOW}⚠ 备份失败（可能是首次部署，线上无数据），继续部署...${NC}"
    echo ""
fi

echo -e "${YELLOW}⟳ 部署 v${VERSION} 到 ${SERVER_IP}...${NC}"
echo ""

# SSH 部署
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    "ubuntu@${SERVER_IP}" \
    "sudo bash -c 'cd ${APP_DIR} && git pull origin main && ${APP_DIR}/venv/bin/python -c \"import sys; sys.path.insert(0, \\\"src\\\"); from database import create_app, init_database; app = create_app(); init_database(app)\" && systemctl restart family-finance'"; then
    echo -e "${RED}✗ SSH 部署失败，请检查网络或服务器状态。${NC}"
    exit 1
fi

# 等待服务启动
echo -e "${YELLOW}⟳ 等待服务启动...${NC}"
sleep 5

# 验证线上服务
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://${SERVER_IP}" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo ""
    echo -e "${GREEN}✓ 部署成功！${NC}"
    echo -e "  版本: v${VERSION}"
    echo -e "  地址: http://${SERVER_IP}"
    echo -e "  状态: HTTP ${HTTP_CODE}"
else
    echo ""
    echo -e "${YELLOW}⚠ 部署完成但验证异常（HTTP ${HTTP_CODE}）${NC}"
    echo "  服务可能还在启动中，建议手动检查:"
    echo "  curl -I http://${SERVER_IP}"
    echo "  ssh -i $SSH_KEY ubuntu@${SERVER_IP} 'sudo journalctl -u family-finance -n 20'"
fi
