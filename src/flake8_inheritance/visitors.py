"""AST visitors for inheritance rule checks."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from typing import Final

from flake8_inheritance.codes import INH001, ErrorCode

RELATIVE_SENTINEL: Final[str] = "__relative__"


@dataclass(frozen=True)
class InheritanceError:
    """A located error produced by the inheritance visitor."""

    line: int
    col: int
    code: ErrorCode
    base_name: str

    def format(self) -> str:
        """Return the full flake8 error string."""
        return self.code.format(base=self.base_name)

    def as_flake8_tuple(self) -> tuple[int, int, str, type]:
        """Return the ``(line, col, message, type)`` tuple flake8 expects."""
        return (self.line, self.col, self.format(), type(self))


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
        if not source_module:
            return "unknown"
        if source_module == RELATIVE_SENTINEL:
            return "same_file"
        if self._project_package and source_module == self._project_package:
            return "internal"
        if source_module in sys.stdlib_module_names:
            return "stdlib"
        return "external"


def _resolve_base(node: ast.expr) -> str | None:
    """Resolve a base class node to a dotted name string.

    Returns ``None`` for dynamic bases (e.g. function calls).
    Unwraps ``ast.Subscript`` so that ``Base[T]`` resolves to ``Base``.
    """
    if isinstance(node, ast.Subscript):
        return _resolve_base(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = [node.attr]
        current: ast.expr = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
    return None


def _collect_module_class_names(tree: ast.AST) -> set[str]:
    """Pre-scan the module body and return all top-level class names."""
    names: set[str] = set()
    if isinstance(tree, ast.Module):
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return names


class InheritanceVisitor(ast.NodeVisitor):
    """Detect internal inheritance (INH001).

    Walks ``ast.ClassDef`` nodes and flags base classes that are classified
    as ``internal`` or ``same_file`` by the provided :class:`ImportTracker`.
    Also tracks module-level class definitions for same-file detection.
    """

    def __init__(
        self,
        import_tracker: ImportTracker,
        module_class_names: frozenset[str] = frozenset(),
    ) -> None:
        """Initialize with a pre-populated import tracker."""
        self._tracker = import_tracker
        self._module_classes = module_class_names
        self.errors: list[InheritanceError] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Process a class definition, checking each base class."""
        for base in node.bases:
            base_name = _resolve_base(base)
            if base_name is None:
                continue

            # For attribute access (e.g. module.Class), classify the root name
            root_name = base_name.split(".")[0]

            # Check if it's a class defined at module level in the same file
            if root_name in self._module_classes and root_name == base_name:
                self.errors.append(
                    InheritanceError(
                        line=node.lineno,
                        col=node.col_offset,
                        code=INH001,
                        base_name=base_name,
                    )
                )
                continue

            classification = self._tracker.classify(root_name)
            if classification in ("internal", "same_file"):
                self.errors.append(
                    InheritanceError(
                        line=node.lineno,
                        col=node.col_offset,
                        code=INH001,
                        base_name=base_name,
                    )
                )

        self.generic_visit(node)
