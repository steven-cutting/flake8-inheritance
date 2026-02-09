"""AST visitors for inheritance rule checks."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from typing import Final

from flake8_inheritance.codes import INH001, INH002, ErrorCode

RELATIVE_SENTINEL: Final[str] = "__relative__"


@dataclass(frozen=True)
class InheritanceError:
    """INH001 error: inheritance from an internal class."""

    line: int
    col: int
    code: ErrorCode
    base: str

    def format(self) -> str:
        """Return the full flake8 error string."""
        return self.code.format(base=self.base)

    def as_flake8_tuple(self) -> tuple[int, int, str, type]:
        """Return the ``(line, col, message, type)`` tuple flake8 expects."""
        return (self.line, self.col, self.format(), type(self))


@dataclass(frozen=True)
class ABCPurityError:
    """INH002 error: concrete method in an abstract base class."""

    line: int
    col: int
    code: ErrorCode
    cls: str
    method: str

    def format(self) -> str:
        """Return the full flake8 error string."""
        return self.code.format(cls=self.cls, method=self.method)

    def as_flake8_tuple(self) -> tuple[int, int, str, type]:
        """Return the ``(line, col, message, type)`` tuple flake8 expects."""
        return (self.line, self.col, self.format(), type(self))


LintError = InheritanceError | ABCPurityError


class ImportTracker(ast.NodeVisitor):
    """Collect import statements and classify their origin."""

    def __init__(self, project_package: str | None = None) -> None:
        """Initialize tracker with an optional project package name."""
        self.imports: dict[str, str] = {}
        self.original_names: dict[str, str] = {}
        self._project_package = project_package

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """Record modules imported with ``import ...`` statements."""
        for alias in node.names:
            top_level = alias.name.split(".")[0]
            local_name = alias.asname or top_level
            self.imports[local_name] = top_level
            self.original_names[local_name] = alias.name

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
            self.original_names[local_name] = alias.name

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
                        base=base_name,
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
                        base=base_name,
                    )
                )

        self.generic_visit(node)


class ABCPurityVisitor(ast.NodeVisitor):
    """Detect impure ABCs (INH002).

    Walks ``ast.ClassDef`` nodes and flags concrete (non-abstract) methods
    in classes that inherit from ``abc.ABC`` or use ``abc.ABCMeta`` as their
    metaclass.  Dunder methods (e.g. ``__init__``) are always allowed.
    """

    def __init__(self, import_tracker: ImportTracker) -> None:
        """Initialize with a pre-populated import tracker."""
        self._tracker = import_tracker
        self.errors: list[ABCPurityError] = []
        self._abc_local_names = self._resolve_names_for("ABC")
        self._abcmeta_local_names = self._resolve_names_for("ABCMeta")
        self._abstractmethod_local_names = self._resolve_names_for("abstractmethod")
        self._abc_module_aliases = self._resolve_abc_module_aliases()

    def _resolve_names_for(self, original: str) -> set[str]:
        """Find all local names that were imported as *original* from ``abc``."""
        names: set[str] = set()
        for local_name, source in self._tracker.imports.items():
            if source == "abc" and self._tracker.original_names.get(local_name) == original:
                names.add(local_name)
        return names

    def _resolve_abc_module_aliases(self) -> set[str]:
        """Find local names that are module-level imports of ``abc``.

        Handles ``import abc`` and ``import abc as a``.
        """
        names: set[str] = set()
        for local_name, source in self._tracker.imports.items():
            if source == "abc" and self._tracker.original_names.get(local_name) == "abc":
                names.add(local_name)
        return names

    def _is_abc_base(self, base_name: str) -> bool:
        """Check if a resolved base name refers to ``abc.ABC``.

        Handles both direct (``ABC``) and module-qualified (``abc.ABC``)
        forms, including aliases.
        """
        # Direct: from abc import ABC [as X]
        if base_name in self._abc_local_names:
            return True
        # Module-qualified: import abc [as a]; class X(a.ABC)
        parts = base_name.split(".")
        return (
            len(parts) == 2  # noqa: PLR2004
            and parts[0] in self._abc_module_aliases
            and parts[1] == "ABC"
        )

    def _is_abcmeta_keyword(self, keyword: ast.keyword) -> bool:
        """Check if a class keyword is ``metaclass=ABCMeta`` (any form)."""
        if keyword.arg != "metaclass":
            return False
        # Direct: from abc import ABCMeta [as X]; metaclass=X
        if isinstance(keyword.value, ast.Name):
            return keyword.value.id in self._abcmeta_local_names
        # Module-qualified: import abc [as a]; metaclass=a.ABCMeta
        if isinstance(keyword.value, ast.Attribute):
            resolved = _resolve_base(keyword.value)
            if resolved is not None:
                parts = resolved.split(".")
                if (
                    len(parts) == 2  # noqa: PLR2004
                    and parts[0] in self._abc_module_aliases
                    and parts[1] == "ABCMeta"
                ):
                    return True
        return False

    def _is_abc(self, node: ast.ClassDef) -> bool:
        """Check if a class is an ABC (inherits from ABC or uses ABCMeta)."""
        for base in node.bases:
            base_name = _resolve_base(base)
            if base_name is not None and self._is_abc_base(base_name):
                return True
        return any(self._is_abcmeta_keyword(kw) for kw in node.keywords)

    def _is_abstractmethod(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a method is decorated with ``@abstractmethod`` (any form)."""
        for decorator in node.decorator_list:
            # Direct: @abstractmethod or @am (alias)
            if isinstance(decorator, ast.Name):
                if decorator.id in self._abstractmethod_local_names:
                    return True
            # Module-qualified: @abc.abstractmethod or @a.abstractmethod
            elif isinstance(decorator, ast.Attribute):
                resolved = _resolve_base(decorator)
                if resolved is not None:
                    parts = resolved.split(".")
                    if (
                        len(parts) == 2  # noqa: PLR2004
                        and parts[0] in self._abc_module_aliases
                        and parts[1] == "abstractmethod"
                    ):
                        return True
        return False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Process a class definition, checking ABC purity."""
        if self._is_abc(node):
            for item in node.body:
                if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue

                # Allow dunder methods
                if item.name.startswith("__") and item.name.endswith("__"):
                    continue

                # Check if decorated with @abstractmethod
                if self._is_abstractmethod(item):
                    continue

                # Concrete method found - flag it
                self.errors.append(
                    ABCPurityError(
                        line=item.lineno,
                        col=item.col_offset,
                        code=INH002,
                        cls=node.name,
                        method=item.name,
                    ),
                )

        self.generic_visit(node)
