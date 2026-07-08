#!/usr/bin/env python3
"""
PreToolUse Hook: 安全命令白名单自动批准。
当 Bash 命令匹配白名单前缀时，自动返回 permissionDecision: "allow"，
跳过人工确认弹窗。未匹配的命令走默认权限流程。
"""
import json
import sys

# 安全命令白名单（前缀匹配）
# 合并所有 agent 的命令集
SAFE_COMMAND_PREFIXES = [
    # 通用工具
    "date",
    "cat ",
    "cat\t",
    "wc ",
    "wc\t",
    "mkdir -p",
    "mkdir ",
    "ls",
    "find ",
    "find\t",
    "chmod +x",
    "chmod ",
    # Go 工具链
    "go build",
    "go test",
    "go vet",
    "go mod tidy",
    # Python 测试
    "pytest",
    "python -m pytest",
    "python3 -m pytest",
    # Node.js 测试
    "npx jest",
    # 脚本检查
    "bash -n",
]

# 精确匹配（命令本身就是完整命令，无参数）
SAFE_EXACT_COMMANDS = [
    "date",
    "ls",
    "go build",
    "go vet",
    "go mod tidy",
]

# 危险命令黑名单（即使前缀匹配也拒绝）
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "> /dev/sd",
    ":(){ :|:& };:",
]


def is_safe_command(command: str) -> bool:
    """检查命令是否在安全白名单中。"""
    cmd = command.strip()

    # 先检查危险命令黑名单
    for dangerous in DANGEROUS_PATTERNS:
        if dangerous in cmd:
            return False

    # 精确匹配
    if cmd in SAFE_EXACT_COMMANDS:
        return True

    # 前缀匹配
    for prefix in SAFE_COMMAND_PREFIXES:
        if cmd.startswith(prefix):
            return True

    return False


def main() -> int:
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, IOError):
        # 解析失败，走默认流程
        print(json.dumps({"continue": True}))
        return 0

    # 仅处理 Bash 工具
    if input_data.get("tool_name") != "Bash":
        print(json.dumps({"continue": True}))
        return 0

    command = input_data.get("tool_input", {}).get("command", "")

    if is_safe_command(command):
        output = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            },
        }
        print(json.dumps(output))
        return 0

    # 未匹配白名单，走默认权限流程
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
