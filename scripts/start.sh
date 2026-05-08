#!/usr/bin/env bash
# start.sh — 创建功能分支
# 用法: ./start.sh feature/xxx | fix/xxx | hotfix/xxx

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 参数检查
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}用法:${NC}"
    echo "  ./start.sh feature/xxx    # 功能开发"
    echo "  ./start.sh fix/xxx        # Bug 修复"
    echo "  ./start.sh hotfix/xxx     # 紧急修复"
    exit 1
fi

BRANCH_NAME="$1"

# 检查分支命名
if [[ ! "$BRANCH_NAME" =~ ^(feature|fix|hotfix)/ ]]; then
    echo -e "${RED}✗ 分支名必须以 feature/ fix/ hotfix/ 开头${NC}"
    exit 1
fi

# 检查是否在 main 分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}✗ 当前在 '$CURRENT_BRANCH' 分支，请先切回 main:${NC}"
    echo "  git checkout main"
    exit 1
fi

# 检查工作区是否干净
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${RED}✗ 工作区有未提交的改动，请先 commit 或 stash:${NC}"
    git status --short
    exit 1
fi

# 同步最新 main
echo -e "${YELLOW}⟳ 同步最新 main...${NC}"
git fetch origin
git pull origin main

# 创建分支
echo -e "${YELLOW}⟳ 创建分支 '$BRANCH_NAME'...${NC}"
git checkout -b "$BRANCH_NAME"
git push -u origin "$BRANCH_NAME"

echo ""
echo -e "${GREEN}✓ 分支创建成功！${NC}"
echo -e "  当前分支: ${YELLOW}$BRANCH_NAME${NC}"
echo -e "  远程跟踪: origin/$BRANCH_NAME"
echo ""
echo "  开始开发吧！完成后使用 ./release.sh 发版。"
