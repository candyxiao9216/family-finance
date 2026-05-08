#!/usr/bin/env bash
# start.sh — 创建开发分支
# 用法：
#   ./scripts/start.sh                  → dev/2026-05-08（今天日期）
#   ./scripts/start.sh feature/xxx      → 功能开发
#   ./scripts/start.sh fix/xxx          → Bug 修复
#   ./scripts/start.sh hotfix/xxx       → 紧急修复

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(git rev-parse --show-toplevel)"

# ── 确定分支名 ──
if [ $# -eq 0 ]; then
    BRANCH_NAME="dev/$(date +%Y-%m-%d)"
else
    BRANCH_NAME="$1"
fi

# ── 安全检查：main 上有未提交改动 ──
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] && [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}✗ main 上有未提交的改动，请先 commit 或 stash:${NC}"
    git status --short
    exit 1
fi

# 如果不在 main，先切回 main
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}⟳ 从 $CURRENT_BRANCH 切回 main...${NC}"
    git checkout main
fi

# ── 拉取 main 最新 ──
echo -e "${YELLOW}⟳ 同步最新 main...${NC}"
git fetch origin main
git pull origin main

# ── 创建或切换分支 ──
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" 2>/dev/null; then
    # 本地分支已存在，直接切换
    echo -e "${YELLOW}⚠ 本地分支 ${BRANCH_NAME} 已存在，直接切换${NC}"
    git checkout "${BRANCH_NAME}"
    git pull origin "${BRANCH_NAME}" --rebase 2>/dev/null || true
elif git ls-remote --heads origin "${BRANCH_NAME}" 2>/dev/null | grep -q "${BRANCH_NAME}"; then
    # 远程分支已存在，拉取到本地
    echo -e "${YELLOW}⚠ 远程分支 ${BRANCH_NAME} 已存在，拉取到本地${NC}"
    git checkout -b "${BRANCH_NAME}" "origin/${BRANCH_NAME}"
else
    # 全新分支
    echo -e "${YELLOW}⟳ 创建分支 '${BRANCH_NAME}'...${NC}"
    git checkout -b "${BRANCH_NAME}"
    git push -u origin "${BRANCH_NAME}"
fi

echo ""
echo -e "${GREEN}✓ 就绪！${NC}"
echo -e "  当前分支: ${YELLOW}${BRANCH_NAME}${NC}"
echo ""
echo "  开始开发吧！完成后使用 ./scripts/release.sh 发版。"
