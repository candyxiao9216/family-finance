#!/usr/bin/env python3
"""
PreToolUse Hook: 命令权限守卫（保守档 B）。

三档决策（permissionDecision 优先级高于权限模式，即使 bypassPermissions 也生效）：
  1. allow —— 安全只读/构建/测试命令，自动放行，不弹窗。
  2. ask   —— 关键写操作（git commit/push/reset、部署脚本、rm 等），弹窗人工确认。
  3. deny  —— 灾难命令 + 项目红线（在 main 分支 commit），硬拦截。
其余命令走默认权限流程。
"""
import json
import subprocess
import sys

# ---- 1. 安全命令白名单（前缀匹配）→ 自动放行 ----
SAFE_COMMAND_PREFIXES = [
    "date", "cat ", "cat\t", "wc ", "wc\t", "mkdir -p", "mkdir ",
    "ls", "find ", "find\t", "chmod +x", "chmod ",
    "go build", "go test", "go vet", "go mod tidy",
    "pytest", "python -m pytest", "python3 -m pytest",
    "npx jest", "bash -n",
    # 只读 git 查询
    "git status", "git branch", "git log", "git diff", "git show", "git rev-parse",
]

SAFE_EXACT_COMMANDS = [
    "date", "ls", "go build", "go vet", "go mod tidy",
]

# ---- 2. 灾难命令黑名单 → 硬拒绝 ----
DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf ~", "dd if=/dev/zero", "dd if=/dev/random",
    "mkfs", "> /dev/sd", ":(){ :|:& };:",
    "git push -f", "git push --force",          # 禁止强推
    "cp backups/", "cp ./backups/",             # 防止用备份覆盖本地数据（数据隔离红线）
]

# ---- 3. 关键写操作 → 需人工确认（ask）----
CONFIRM_PREFIXES = [
    "git commit", "git push", "git merge", "git rebase",
    "git reset --hard", "git clean",
    "rm ", "rm\t", "mv ",
    # 部署 / 发版 / 备份脚本
    "./scripts/release.sh", "scripts/release.sh",
    "./scripts/push-deploy.sh", "scripts/push-deploy.sh",
    "./scripts/deploy.sh", "scripts/deploy.sh",
    "./scripts/backup.sh", "scripts/backup.sh",
    # 直接调 ssh/scp 触碰线上
    "ssh ", "scp ",
]


def current_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def decide(command: str):
    """返回 (decision, reason)；decision ∈ {allow, ask, deny, default}。"""
    cmd = command.strip()

    # 灾难命令：硬拒绝
    for bad in DANGEROUS_PATTERNS:
        if bad in cmd:
            return "deny", f"命中危险命令模式「{bad}」，已拦截。"

    # 项目红线：禁止在 main/master 提交
    if cmd.startswith("git commit"):
        br = current_branch()
        if br in ("main", "master"):
            return "deny", (
                f"红线拦截：当前在 {br} 分支，禁止直接提交。"
                "请先 `./scripts/start.sh feature/xxx` 开功能分支。"
            )

    # 安全命令：自动放行
    if cmd in SAFE_EXACT_COMMANDS:
        return "allow", ""
    for prefix in SAFE_COMMAND_PREFIXES:
        if cmd.startswith(prefix):
            return "allow", ""

    # 关键写操作：人工确认
    for prefix in CONFIRM_PREFIXES:
        if cmd.startswith(prefix):
            return "ask", "关键写/部署命令，请确认后再执行。"

    # 其余：走默认流程
    return "default", ""


def main() -> int:
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"continue": True}))
        return 0

    if input_data.get("tool_name") != "Bash":
        print(json.dumps({"continue": True}))
        return 0

    command = input_data.get("tool_input", {}).get("command", "")
    decision, reason = decide(command)

    if decision == "default":
        print(json.dumps({"continue": True}))
        return 0

    output = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        },
    }
    if reason:
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
