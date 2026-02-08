#!/usr/bin/env python3
"""Hook: remind to run pre-commit and tests after changes."""

import sys

sys.stderr.write(
    "Remember: run 'uv run pre-commit run --all-files' and 'uv run pytest' to validate changes.\n"
)
sys.exit(0)
