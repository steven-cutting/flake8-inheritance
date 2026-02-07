"""Flake8 plugin that enforces inheritance restrictions."""
from __future__ import annotations

import ast
from typing import ClassVar, Generator


class InheritanceChecker:
    """Flake8 AST checker enforcing composition over inheritance.

    This checker implements the flake8 plugin contract:
    - ``name`` and ``version``: class-level metadata for ``flake8 --version``.
    - ``__init__(self, tree)``: receives the AST for each file.
    - ``run()``: generator yielding ``(line, col, message, type)`` tuples.
    """

    name: ClassVar[str] = "flake8-inheritance"
    version: ClassVar[str] = "0.0.0"  # placeholder until setuptools-scm wired

    def __init__(self, tree: ast.AST) -> None:
        self._tree = tree

    def run(self) -> Generator[tuple[int, int, str, type], None, None]:
        """Run the checker. Yields nothing until rules are implemented."""
        return
        yield  # make this a generator
