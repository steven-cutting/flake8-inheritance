#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""

import json
import re
import shlex
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = {"pytest", "pre-commit", "ruff", "mypy"}

# Prefixes that are transparent wrappers around the real command.
WRAPPER_COMMANDS = {"sudo", "env", "nohup", "nice", "ionice", "command", "exec", "time"}
# Number of tokens in the 'uv run' prefix (i.e., ["uv", "run"]).
_UV_RUN_TOKEN_COUNT = 2

# Split the command into segments (separated by &&, ||, ;, or pipes) and
# ensure any tool invocation in a segment is guarded by 'uv run'.
segments = re.split(r"&&|\|\||[;|]", cmd)
for segment in segments:
    segment_stripped = segment.strip()
    if not segment_stripped:
        continue

    try:
        tokens = shlex.split(segment_stripped)
    except ValueError:
        # If shlex can't parse it (unmatched quotes, etc.), skip this segment
        # rather than blocking potentially valid commands.
        continue

    if not tokens:
        continue

    # Walk past any wrapper commands (and their flag arguments) to find the
    # real command word.  For `env`, also skip KEY=VAL pairs.
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in WRAPPER_COMMANDS:
            idx += 1
            # `env` can have KEY=VAL pairs before the command.
            if tok == "env":
                while idx < len(tokens) and "=" in tokens[idx]:
                    idx += 1
            continue
        # Skip flags that belong to the wrapper (e.g., `sudo -u root`).
        if tok.startswith("-"):
            idx += 1
            continue
        break

    if idx >= len(tokens):
        continue

    command_word = tokens[idx]

    # Check if the command word is a bare tool that should use 'uv run'.
    if command_word in bare_tools:
        # Verify that 'uv run' does NOT precede the tool in the token list.
        # A valid invocation looks like: [...] uv run <tool> [...]
        if idx >= _UV_RUN_TOKEN_COUNT and tokens[idx - 2] == "uv" and tokens[idx - 1] == "run":
            continue
        sys.stderr.write(f"Use 'uv run {command_word}' instead of bare '{command_word}'\n")
        sys.exit(2)
