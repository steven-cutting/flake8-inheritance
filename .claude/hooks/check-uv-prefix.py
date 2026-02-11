#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""

import json
import re
import shlex
import sys

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = {"pytest", "pre-commit", "ruff", "mypy"}

# Wrapper commands and which of their short flags consume an argument value.
# Mapping: command -> set of flags that take a following token as their value.
_WRAPPER_FLAGS: dict[str, set[str]] = {
    "sudo": {"-u", "-g", "-C", "-D", "-R", "-T", "-p"},
    "env": set(),  # env uses KEY=VAL pairs, handled separately
    "nohup": set(),
    "nice": {"-n"},
    "ionice": {"-c", "-n", "-p"},
    "command": {"-v", "-V"},
    "exec": set(),
    "time": set(),
}
WRAPPER_COMMANDS = set(_WRAPPER_FLAGS)
# Number of tokens in the 'uv run' prefix (i.e., ["uv", "run"]).
_UV_RUN_TOKEN_COUNT = 2

# Split the command into segments separated by &&, ||, ;, |, or background &.
# Match && and || first so they aren't consumed as single & or |.
segments = re.split(r"&&|\|\||[;&|]", cmd)
for segment in segments:
    segment_stripped = segment.strip()
    if not segment_stripped:
        continue

    try:
        tokens = shlex.split(segment_stripped)
    except ValueError:
        # shlex can't parse the segment (unmatched quotes, shell syntax, etc.).
        # Fail closed: do a conservative word-boundary check for bare tools.
        for tool in bare_tools:
            if re.search(rf"(?<!\S){re.escape(tool)}(?!\S)", segment_stripped) and not re.search(
                rf"(?<!\S)uv\s+run\s+{re.escape(tool)}(?!\S)",
                segment_stripped,
            ):
                sys.stderr.write(f"Use 'uv run {tool}' instead of bare '{tool}'\n")
                sys.exit(2)
        continue

    if not tokens:
        continue

    # Walk past wrapper commands, their flags (including flag arguments), and
    # env-style KEY=VAL pairs to find the real command word.
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in WRAPPER_COMMANDS:
            wrapper = tok
            idx += 1
            # `env` can have KEY=VAL pairs before the command.
            if wrapper == "env":
                while idx < len(tokens) and ("=" in tokens[idx] or tokens[idx].startswith("-")):
                    idx += 1
                continue
            continue
        # End-of-options marker: the next token is the command word.
        if tok == "--":
            idx += 1
            break
        # Skip flags that belong to the wrapper, consuming their arguments
        # when the flag is known to take a value.
        if tok.startswith("-"):
            # Determine which wrapper we're inside (the most recent one).
            # Walk backwards through tokens to find it.
            known_flags: set[str] = set()
            for prev in reversed(tokens[:idx]):
                if prev in _WRAPPER_FLAGS:
                    known_flags = _WRAPPER_FLAGS[prev]
                    break
            idx += 1
            if tok in known_flags and idx < len(tokens):
                idx += 1  # consume the flag's argument
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
