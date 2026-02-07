#!/usr/bin/env python3
"""Hook: remind to run pre-commit and tests after changes."""
import sys

print(
    "REMINDER: Run 'uv run pre-commit run --all-files' "
    "and 'uv run pytest' after changes.",
    file=sys.stderr,
)
sys.exit(0)
