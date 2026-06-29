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

# ── 找出已合并的本地分支（排除 main）──
# 注意：本项目用 squash merge 发版，分支原始 commit 不会进入 main 历史，
# 因此 `git branch --merged` 检测不到它们。这里对每个分支双重判定：
#   1) 标准/快进合并 → git branch --merged
#   2) squash 合并   → 把分支相对 merge-base 的全部改动压成一个虚拟 commit，
#                      用 git cherry 看其 patch 是否已在 main（'-' 前缀=已合并）
FF_MERGED=$(git branch --merged main | grep -v '^\*' | grep -v 'main' | sed 's/^[[:space:]]*//' || true)

MERGED_LOCAL=""
while read -r branch; do
    [ -z "$branch" ] && continue
    # 快进/标准合并
    if echo "$FF_MERGED" | grep -qx "$branch"; then
        MERGED_LOCAL+="$branch"$'\n'
        continue
    fi
    # squash 合并检测
    mb=$(git merge-base main "$branch" 2>/dev/null) || continue
    virtual=$(git commit-tree "$(git rev-parse "$branch^{tree}")" -p "$mb" -m _ 2>/dev/null) || continue
    if git cherry main "$virtual" 2>/dev/null | grep -q '^-'; then
        MERGED_LOCAL+="$branch"$'\n'
    fi
done < <(git for-each-ref --format='%(refname:short)' refs/heads/ | grep -v '^main$')

MERGED_LOCAL=$(echo "$MERGED_LOCAL" | sed '/^$/d' || true)

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
        # 用 -D 强删：上面已通过 squash 感知判据确认内容已并入 main，
        # 而 git branch -d 对 squash 合并的分支会误判拒绝
        git branch -D "$branch" 2>/dev/null && \
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
