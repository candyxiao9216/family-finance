#!/usr/bin/env bash
# cleanup.sh — 清理已合并到 main 的旧分支
# 用法: ./cleanup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⟳ 清理已合并分支...${NC}"
echo ""

# 切到 main
git checkout main --quiet 2>/dev/null || {
    echo -e "${RED}✗ 无法切换到 main 分支${NC}"
    exit 1
}

# 同步远程
git fetch --prune --quiet

# 找出已合并的本地分支（排除 main）
MERGED_LOCAL=$(git branch --merged main | grep -v '^\*' | grep -v 'main' | sed 's/^[[:space:]]*//' || true)

if [ -z "$MERGED_LOCAL" ]; then
    echo -e "${GREEN}✓ 无需清理，没有已合并的本地分支。${NC}"
    exit 0
fi

echo "以下本地分支已合并到 main："
echo "$MERGED_LOCAL" | while read -r branch; do
    echo "  - $branch"
done
echo ""

# 删除本地分支
echo -e "${YELLOW}删除本地分支...${NC}"
echo "$MERGED_LOCAL" | while read -r branch; do
    if [ -n "$branch" ]; then
        git branch -d "$branch" 2>/dev/null && \
            echo -e "  ${GREEN}✓${NC} 删除本地: $branch" || \
            echo -e "  ${RED}✗${NC} 删除失败: $branch"
    fi
done

# 删除远程分支
echo ""
echo -e "${YELLOW}删除远程分支...${NC}"
echo "$MERGED_LOCAL" | while read -r branch; do
    if [ -n "$branch" ] && git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
        git push origin --delete "$branch" 2>/dev/null && \
            echo -e "  ${GREEN}✓${NC} 删除远程: $branch" || \
            echo -e "  ${RED}✗${NC} 删除远程失败: $branch"
    fi
done

echo ""
echo -e "${GREEN}✓ 清理完成！${NC}"
