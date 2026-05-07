#!/usr/bin/env bash
# backup.sh — 从线上服务器备份数据库到本地
# 用法:
#   ./backup.sh           # 手动备份一次
#   ./backup.sh --rotate  # 备份并清理超过 30 天的旧备份

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER_IP="119.91.205.137"
SSH_KEY="$HOME/.ssh/candyworkbench.pem"
REMOTE_DB="/opt/family-finance/data/family_finance.db"
LOCAL_BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)/backups"
ROTATE_DAYS=30

# 创建备份目录
mkdir -p "$LOCAL_BACKUP_DIR"

# 生成备份文件名（带时间戳）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="family_finance_${TIMESTAMP}.db"
BACKUP_PATH="${LOCAL_BACKUP_DIR}/${BACKUP_FILE}"

echo -e "${YELLOW}⟳ 备份线上数据库...${NC}"
echo "  来源: ubuntu@${SERVER_IP}:${REMOTE_DB}"
echo "  目标: ${BACKUP_PATH}"
echo ""

# SCP 下载数据库
if ! scp -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
    "ubuntu@${SERVER_IP}:${REMOTE_DB}" "$BACKUP_PATH" 2>/dev/null; then
    # 可能需要 sudo 读取
    ssh -i "$SSH_KEY" -o ConnectTimeout=10 "ubuntu@${SERVER_IP}" \
        "sudo cp ${REMOTE_DB} /tmp/backup_db.tmp && sudo chmod 644 /tmp/backup_db.tmp"
    scp -i "$SSH_KEY" "ubuntu@${SERVER_IP}:/tmp/backup_db.tmp" "$BACKUP_PATH"
    ssh -i "$SSH_KEY" "ubuntu@${SERVER_IP}" "sudo rm -f /tmp/backup_db.tmp"
fi

# 验证备份文件
if [ ! -f "$BACKUP_PATH" ]; then
    echo -e "${RED}✗ 备份失败！文件未创建。${NC}"
    exit 1
fi

FILE_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo -e "${GREEN}✓ 备份成功！${NC}"
echo "  文件: ${BACKUP_FILE}"
echo "  大小: ${FILE_SIZE}"

# 验证数据库完整性
TABLE_COUNT=$(sqlite3 "$BACKUP_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "  表数: ${TABLE_COUNT} 张"
    USER_COUNT=$(sqlite3 "$BACKUP_PATH" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "?")
    TXN_COUNT=$(sqlite3 "$BACKUP_PATH" "SELECT COUNT(*) FROM transactions;" 2>/dev/null || echo "?")
    echo "  用户: ${USER_COUNT} 个"
    echo "  交易: ${TXN_COUNT} 条"
else
    echo -e "${YELLOW}  ⚠ 无法验证数据库完整性${NC}"
fi

# 清理旧备份
if [ "${1:-}" = "--rotate" ]; then
    echo ""
    echo -e "${YELLOW}⟳ 清理 ${ROTATE_DAYS} 天前的旧备份...${NC}"
    DELETED=0
    while IFS= read -r old_file; do
        if [ -n "$old_file" ]; then
            rm -f "$old_file"
            DELETED=$((DELETED + 1))
        fi
    done < <(find "$LOCAL_BACKUP_DIR" -name "family_finance_*.db" -mtime +${ROTATE_DAYS} 2>/dev/null)
    echo "  已清理 ${DELETED} 个旧备份"
fi

# 显示当前备份列表
echo ""
echo "当前备份（最近 5 个）："
ls -lht "$LOCAL_BACKUP_DIR"/family_finance_*.db 2>/dev/null | head -5 | while read -r line; do
    echo "  $line"
done

TOTAL_BACKUPS=$(ls "$LOCAL_BACKUP_DIR"/family_finance_*.db 2>/dev/null | wc -l | tr -d ' ')
echo "  共 ${TOTAL_BACKUPS} 个备份"
