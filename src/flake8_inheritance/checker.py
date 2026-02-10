"""Flake8 plugin that enforces inheritance restrictions."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, ClassVar

from flake8_inheritance.visitors import (
    ABCPurityVisitor,
    ImportTracker,
    InheritanceVisitor,
    collect_module_class_names,
)

if TYPE_CHECKING:
    import ast
    from collections.abc import Generator


class InheritanceChecker:
    """Flake8 AST checker enforcing composition over inheritance.

    This checker implements the flake8 plugin contract:
    - ``name`` and ``version``: class-level metadata for ``flake8 --version``.
    - ``__init__(self, tree)``: receives the AST for each file.
    - ``run()``: generator yielding ``(line, col, message, type)`` tuples.
    """

    name: ClassVar[str] = "flake8-inheritance"
    version: ClassVar[str] = importlib.metadata.version("flake8-inheritance")

    def __init__(self, tree: ast.AST) -> None:
        """Initialize the checker with the AST for a single file."""
        self._tree = tree

    def run(self) -> Generator[tuple[int, int, str, type], None, None]:
        """Run the checker and yield flake8 error tuples."""
        tracker = ImportTracker()
        tracker.visit(self._tree)

        module_classes = frozenset(collect_module_class_names(self._tree))

        inh_visitor = InheritanceVisitor(tracker, module_classes)
        inh_visitor.visit(self._tree)

        abc_visitor = ABCPurityVisitor(tracker)
        abc_visitor.visit(self._tree)

        for inh_error in inh_visitor.errors:
            yield inh_error.as_flake8_tuple()
        for abc_error in abc_visitor.errors:
            yield abc_error.as_flake8_tuple()
