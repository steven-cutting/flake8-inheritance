"""AST visitors for inheritance rule checks."""

from __future__ import annotations

import ast
import sys
from typing import Final

RELATIVE_SENTINEL: Final[str] = "__relative__"


class ImportTracker(ast.NodeVisitor):
    """Collect import statements and classify their origin."""

    def __init__(self, project_package: str | None = None) -> None:
        """Initialize tracker with an optional project package name."""
        self.imports: dict[str, str] = {}
        self._project_package = project_package

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """Record modules imported with ``import ...`` statements."""
        for alias in node.names:
            top_level = alias.name.split(".")[0]
            local_name = alias.asname or top_level
            self.imports[local_name] = top_level

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Record modules imported with ``from ... import ...`` statements."""
        if node.level > 0:
            source_module = RELATIVE_SENTINEL
        elif node.module:
            source_module = node.module.split(".")[0]
        else:
            source_module = ""

        for alias in node.names:
            local_name = alias.asname or alias.name
            self.imports[local_name] = source_module

    def classify(self, local_name: str) -> str:
        """Return classification for a local import name."""
        if local_name not in self.imports:
            return "unknown"

        source_module = self.imports[local_name]
        if source_module == RELATIVE_SENTINEL:
            return "same_file"
        if self._project_package and source_module == self._project_package:
            return "internal"
        if source_module in sys.stdlib_module_names:
            return "stdlib"
        return "external"
