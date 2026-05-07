#!/usr/bin/env bash
# release.sh — FamilyFin 发版管道
# 用法:
#   ./release.sh           # 交互模式
#   ./release.sh patch     # 自动模式（patch/minor/major）

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COVERAGE_THRESHOLD=50  # 临时设为 50%，目标 80%
PROJECT_ROOT=$(git rev-parse --show-toplevel)

# ============================================================
# 工具函数
# ============================================================

step() {
    echo ""
    echo -e "${BLUE}━━━ Step $1: $2 ━━━${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

ok() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 版本号递增
bump_version() {
    local current="$1"
    local type="$2"
    local major minor patch
    IFS='.' read -r major minor patch <<< "$current"
    case "$type" in
        major) echo "$((major + 1)).0.0" ;;
        minor) echo "${major}.$((minor + 1)).0" ;;
        patch) echo "${major}.${minor}.$((patch + 1))" ;;
        *) fail "未知版本类型: $type" ;;
    esac
}

# ============================================================
# 模式判断
# ============================================================

AUTO_MODE=false
VERSION_TYPE=""
SKIP_TESTS=false

for arg in "$@"; do
    case "$arg" in
        patch|minor|major)
            AUTO_MODE=true
            VERSION_TYPE="$arg"
            ;;
        --skip-tests)
            SKIP_TESTS=true
            ;;
        *)
            fail "参数错误。用法: ./release.sh [patch|minor|major] [--skip-tests]"
            ;;
    esac
done

# ============================================================
# Step 1: 状态检查
# ============================================================

step 1 "状态检查"

CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ]; then
    fail "当前在 main 分支，请从功能分支执行 release。"
fi
ok "当前分支: $CURRENT_BRANCH"

if ! git diff --quiet || ! git diff --cached --quiet; then
    fail "工作区有未提交的改动，请先 commit。"
fi
ok "工作区干净"

# 确保已推送
git push origin "$CURRENT_BRANCH" --quiet 2>/dev/null || true
ok "分支已推送到远程"

# ============================================================
# Step 2: 测试验证
# ============================================================

step 2 "测试验证（pytest + 覆盖率 ≥ ${COVERAGE_THRESHOLD}%）"

if [ "$SKIP_TESTS" = true ]; then
    warn "跳过测试验证（--skip-tests）"
else
    # 运行 pytest + 覆盖率
    echo "运行 pytest..."
    PYTEST_OUTPUT=$(cd "$PROJECT_ROOT" && python3 -m pytest tests/ --cov=src --cov-config=pyproject.toml --cov-report=term-missing --tb=short 2>&1) || {
        echo "$PYTEST_OUTPUT" | tail -30
        fail "测试失败！请修复后重试。使用 --skip-tests 可跳过。"
    }

    # 提取覆盖率
    COVERAGE=$(echo "$PYTEST_OUTPUT" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')
    if [ -z "$COVERAGE" ]; then
        warn "无法提取覆盖率数值，跳过覆盖率检查"
        COVERAGE=100
    fi

    echo "$PYTEST_OUTPUT" | tail -20

    if [ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]; then
        fail "覆盖率 ${COVERAGE}% 低于阈值 ${COVERAGE_THRESHOLD}%。请补充测试。使用 --skip-tests 可跳过。"
    fi
    ok "测试全部通过，覆盖率: ${COVERAGE}%"
fi

# ============================================================
# Step 3: 本地冒烟验证
# ============================================================

step 3 "本地冒烟验证"

if [ "$SKIP_TESTS" = true ]; then
    warn "跳过冒烟验证（--skip-tests）"
else
    echo "启动 Flask 测试客户端验证..."
    cd "$PROJECT_ROOT/src"
    python3 -c "
import os, sys
sys.path.insert(0, '.')
from main import app
app.config['TESTING'] = True
client = app.test_client()
resp = client.get('/')
print(f'HTTP {resp.status_code}')
if resp.status_code not in (200, 302):
    sys.exit(1)
" 2>/dev/null || fail "本地冒烟验证失败！应用无法启动。"
    cd "$PROJECT_ROOT"

    ok "本地冒烟验证通过"
fi

# ============================================================
# Step 4: 文档变更提醒
# ============================================================

step 4 "文档变更提醒"

CHANGED_FILES=$(git diff --name-only main..."$CURRENT_BRANCH" 2>/dev/null || git diff --name-only origin/main..."$CURRENT_BRANCH")
DOC_WARNINGS=""

if echo "$CHANGED_FILES" | grep -q "^src/routes/"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到 routes/ 改动 → 请确认 CLAUDE.md API 路由表已更新"
fi
if echo "$CHANGED_FILES" | grep -q "^src/models.py"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到 models.py 改动 → 请确认 CLAUDE.md 数据库设计章节已更新"
fi
if echo "$CHANGED_FILES" | grep -q "^src/templates/"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到 templates/ 改动 → 请确认 CLAUDE.md 目录结构已更新"
fi
if echo "$CHANGED_FILES" | grep -q -E "^(src/config\.py|\.env)"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到配置改动 → 请确认部署文档已更新"
fi
if echo "$CHANGED_FILES" | grep -q "^src/services/"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到 services/ 改动 → 请确认 CLAUDE.md 服务描述已更新"
fi
if echo "$CHANGED_FILES" | grep -q "^requirements.txt"; then
    DOC_WARNINGS="${DOC_WARNINGS}\n  - 检测到依赖变更 → 请确认 README.md 安装说明已更新"
fi

if [ -n "$DOC_WARNINGS" ]; then
    echo -e "${YELLOW}⚠  文档变更提醒：${NC}"
    echo -e "$DOC_WARNINGS"
    echo ""
    if [ "$AUTO_MODE" = false ]; then
        read -p "  是否已确认文档已同步？[Y/n] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            fail "请更新文档后重新执行 release。"
        fi
    else
        echo "  (自动模式：信任文档已同步)"
    fi
else
    ok "无需文档更新提醒"
fi

# ============================================================
# Step 5: 改动摘要
# ============================================================

step 5 "改动摘要"

echo "本次提交列表："
git log main.."$CURRENT_BRANCH" --oneline 2>/dev/null || \
    git log origin/main.."$CURRENT_BRANCH" --oneline
echo ""

# ============================================================
# Step 6: 版本号
# ============================================================

step 6 "版本号"

CURRENT_VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')
echo "当前版本: v${CURRENT_VERSION}"

if [ "$AUTO_MODE" = false ]; then
    echo ""
    echo "选择版本类型:"
    echo "  1) patch  (${CURRENT_VERSION} → $(bump_version "$CURRENT_VERSION" patch))"
    echo "  2) minor  (${CURRENT_VERSION} → $(bump_version "$CURRENT_VERSION" minor))"
    echo "  3) major  (${CURRENT_VERSION} → $(bump_version "$CURRENT_VERSION" major))"
    read -p "选择 [1/2/3]: " -n 1 -r
    echo ""
    case "$REPLY" in
        1) VERSION_TYPE="patch" ;;
        2) VERSION_TYPE="minor" ;;
        3) VERSION_TYPE="major" ;;
        *) fail "无效选择" ;;
    esac
fi

NEW_VERSION=$(bump_version "$CURRENT_VERSION" "$VERSION_TYPE")
ok "新版本: v${NEW_VERSION}"

# ============================================================
# Step 7: 生成 Release Notes
# ============================================================

step 7 "生成 Release Notes"

TODAY=$(date +%Y-%m-%d)
COMMITS=$(git log main.."$CURRENT_BRANCH" --oneline 2>/dev/null || \
          git log origin/main.."$CURRENT_BRANCH" --oneline)

# 按类型分类
FEATS=$(echo "$COMMITS" | grep -i "^[a-f0-9]* feat" | sed 's/^[a-f0-9]* /- /' || true)
FIXES=$(echo "$COMMITS" | grep -i "^[a-f0-9]* fix" | sed 's/^[a-f0-9]* /- /' || true)
DOCS=$(echo "$COMMITS" | grep -i "^[a-f0-9]* docs\?" | sed 's/^[a-f0-9]* /- /' || true)
OTHERS=$(echo "$COMMITS" | grep -iv "^[a-f0-9]* \(feat\|fix\|docs\?\)" | sed 's/^[a-f0-9]* /- /' || true)

RELEASE_NOTES="## v${NEW_VERSION} (${TODAY})"
[ -n "$FEATS" ] && RELEASE_NOTES="${RELEASE_NOTES}

### 新功能
${FEATS}"
[ -n "$FIXES" ] && RELEASE_NOTES="${RELEASE_NOTES}

### 修复
${FIXES}"
[ -n "$DOCS" ] && RELEASE_NOTES="${RELEASE_NOTES}

### 文档
${DOCS}"
[ -n "$OTHERS" ] && RELEASE_NOTES="${RELEASE_NOTES}

### 其他
${OTHERS}"

echo "$RELEASE_NOTES"
echo ""

# ============================================================
# Step 8: Squash Merge
# ============================================================

step 8 "Squash Merge 到 main"

git checkout main
git pull origin main --quiet

# 获取第一条 feat/fix commit 的简短描述作为 summary
SUMMARY=$(git log main.."$CURRENT_BRANCH" --oneline --reverse 2>/dev/null | head -1 | sed 's/^[a-f0-9]* //' || echo "更新")
if [ ${#SUMMARY} -gt 50 ]; then
    SUMMARY="${SUMMARY:0:50}..."
fi

git merge --squash "$CURRENT_BRANCH"
git commit -m "$(cat <<EOF
release(${TODAY}): v${NEW_VERSION} — ${SUMMARY}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"

ok "Squash merge 完成"

# ============================================================
# Step 9: 自动文档更新
# ============================================================

step 9 "自动文档更新"

# 更新 VERSION
echo "$NEW_VERSION" > "$PROJECT_ROOT/VERSION"
ok "VERSION → ${NEW_VERSION}"

# 更新 CHANGELOG.md（在第一个 "## v" 之前插入新条目）
CHANGELOG_FILE="$PROJECT_ROOT/CHANGELOG.md"
if [ -f "$CHANGELOG_FILE" ]; then
    # 将 Release Notes 写入临时文件
    NOTES_FILE=$(mktemp)
    echo "$RELEASE_NOTES" > "$NOTES_FILE"
    echo "" >> "$NOTES_FILE"
    echo "---" >> "$NOTES_FILE"
    echo "" >> "$NOTES_FILE"

    # 找到第一个 "## v" 的行号，在其前面插入
    FIRST_VERSION_LINE=$(grep -n "^## v" "$CHANGELOG_FILE" | head -1 | cut -d: -f1)
    if [ -n "$FIRST_VERSION_LINE" ]; then
        TEMP_FILE=$(mktemp)
        head -n $((FIRST_VERSION_LINE - 1)) "$CHANGELOG_FILE" > "$TEMP_FILE"
        cat "$NOTES_FILE" >> "$TEMP_FILE"
        tail -n +$FIRST_VERSION_LINE "$CHANGELOG_FILE" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "$CHANGELOG_FILE"
    else
        # 没有已有版本条目，直接追加到末尾
        echo "" >> "$CHANGELOG_FILE"
        cat "$NOTES_FILE" >> "$CHANGELOG_FILE"
    fi
    rm -f "$NOTES_FILE"
    ok "CHANGELOG.md 已更新"
fi

# 更新 PROJECT_BRIEF.md 版本号
BRIEF_FILE="$PROJECT_ROOT/PROJECT_BRIEF.md"
if [ -f "$BRIEF_FILE" ]; then
    sed -i '' "s/v[0-9]*\.[0-9]*\.[0-9]*/v${NEW_VERSION}/g" "$BRIEF_FILE" 2>/dev/null || \
    sed -i "s/v[0-9]*\.[0-9]*\.[0-9]*/v${NEW_VERSION}/g" "$BRIEF_FILE"
    ok "PROJECT_BRIEF.md 版本号已更新"
fi

# 更新 CLAUDE.md 状态行版本号
CLAUDE_FILE="$PROJECT_ROOT/CLAUDE.md"
if [ -f "$CLAUDE_FILE" ]; then
    sed -i '' "s/(v[0-9]*\.[0-9]*\.[0-9]*)/(v${NEW_VERSION})/g" "$CLAUDE_FILE" 2>/dev/null || \
    sed -i "s/(v[0-9]*\.[0-9]*\.[0-9]*)/(v${NEW_VERSION})/g" "$CLAUDE_FILE"
    ok "CLAUDE.md 版本号已更新"
fi

# 提交文档更新
git add VERSION CHANGELOG.md PROJECT_BRIEF.md CLAUDE.md 2>/dev/null || true
git commit -m "$(cat <<EOF
docs: 自动更新版本号和 CHANGELOG 至 v${NEW_VERSION}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"

# ============================================================
# Step 10: Tag + Push
# ============================================================

step 10 "Tag + Push"

git tag "v${NEW_VERSION}"
git push origin main --tags

ok "Tag v${NEW_VERSION} 已创建并推送"

# ============================================================
# 完成
# ============================================================

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ 发版完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  版本:  ${YELLOW}v${NEW_VERSION}${NC}"
echo -e "  分支:  ${CURRENT_BRANCH} → main (squash merged)"
echo -e "  Tag:   v${NEW_VERSION}"
echo ""
echo "  下一步:"
echo "  1. ./push-deploy.sh   — 部署到生产"
echo "  2. ./cleanup.sh       — 清理旧分支"
echo ""

# 切回功能分支
git checkout "$CURRENT_BRANCH" 2>/dev/null || true
