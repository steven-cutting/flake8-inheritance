#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""

import json
import re
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = ["pytest", "pre-commit", "ruff", "mypy"]

# Split the command into segments (e.g., separated by &&, ;, |) and
# ensure any tool usage in a segment is guarded by 'uv run' in that segment.
segments = re.split(r"[;&|]+", cmd)
for segment in segments:
    segment = segment.strip()
    if not segment:
        continue
    has_uv_run = re.search(r"\buv\s+run\b", segment)
    for tool in bare_tools:
        if re.search(rf"\b{re.escape(tool)}\b", segment) and not has_uv_run:
            sys.stderr.write(f"Use 'uv run {tool.strip()}' instead of bare '{tool.strip()}'\n")
            sys.exit(2)
