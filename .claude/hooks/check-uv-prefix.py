#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""

import json
import re
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = ["pytest", "pre-commit", "ruff", "mypy"]
needs_uv_run = not re.search(r"\buv\s+run\b", cmd)
for tool in bare_tools:
    if needs_uv_run and re.search(rf"\b{re.escape(tool)}\b", cmd):
        sys.stderr.write(f"Use 'uv run {tool.strip()}' instead of bare '{tool.strip()}'\n")
        sys.exit(2)
