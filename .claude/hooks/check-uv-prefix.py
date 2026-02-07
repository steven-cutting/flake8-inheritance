#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""
import json
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = ["pytest", "pre-commit", "ruff ", "mypy "]
for tool in bare_tools:
    if tool in cmd and "uv run" not in cmd:
        print(
            f"Use 'uv run {tool.strip()}' instead of bare '{tool.strip()}'",
            file=sys.stderr,
        )
        sys.exit(2)
