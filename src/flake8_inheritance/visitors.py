"""AST visitors for inheritance rule checks."""
from __future__ import annotations

import ast
import sys
from typing import Sequence

from flake8_inheritance.codes import INH001, INH002

RELATIVE_SENTINEL = "__relative__"

_STDLIB_MODULES: frozenset[str] = frozenset(sys.stdlib_module_names)


# ---------------------------------------------------------------------------
# Import map construction
# ---------------------------------------------------------------------------

def build_import_map(tree: ast.Module) -> dict[str, str]:
    """Walk *tree* and return a map of imported local names to top-level packages.

    Relative imports are mapped to the sentinel ``"__relative__"``.
    Star imports are silently skipped because the individual names are
    not statically determinable.
    """
    import_map: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # ``import foo.bar`` -> local name "foo", package "foo"
                top = alias.name.split(".")[0]
                local_name = alias.asname if alias.asname else top
                import_map[local_name] = top
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import – always internal.
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local_name = alias.asname if alias.asname else alias.name
                    import_map[local_name] = RELATIVE_SENTINEL
            else:
                # Absolute ``from X.Y import Z``
                top = (node.module or "").split(".")[0]
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local_name = alias.asname if alias.asname else alias.name
                    import_map[local_name] = top
    return import_map


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_name(
    name: str,
    import_map: dict[str, str],
    local_classes: set[str],
    project_packages: Sequence[str],
) -> str:
    """Classify *name* as one of six categories.

    Returns one of:
    ``"same_file"``, ``"internal_relative"``, ``"internal_project"``,
    ``"stdlib"``, ``"external"``, or ``"unknown"``.
    """
    if name in local_classes:
        return "same_file"
    pkg = import_map.get(name)
    if pkg is None:
        return "unknown"
    if pkg == RELATIVE_SENTINEL:
        return "internal_relative"
    if pkg in _project_set(project_packages):
        return "internal_project"
    if pkg in _STDLIB_MODULES:
        return "stdlib"
    return "external"


def _project_set(project_packages: Sequence[str]) -> set[str]:
    # Thin wrapper so callers can pass a list; converts to set for O(1).
    return set(project_packages)


# ---------------------------------------------------------------------------
# Collect top-level class names
# ---------------------------------------------------------------------------

def _collect_top_level_classes(tree: ast.Module) -> set[str]:
    """Return the names of all classes defined at module level."""
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


# ---------------------------------------------------------------------------
# INH001 helpers
# ---------------------------------------------------------------------------

def _resolve_base(base: ast.expr) -> tuple[str, str] | None:
    """Return ``(lookup_name, display_name)`` for a base class node.

    * ``ast.Name``      → ``("Foo", "Foo")``
    * ``ast.Attribute`` → ``("module", "module.Bar")`` (root name for lookup,
      dotted form for display)
    * Anything else (e.g. function calls) → ``None`` (skip silently).
    """
    if isinstance(base, ast.Name):
        return base.id, base.id
    if isinstance(base, ast.Attribute):
        root = _attribute_root(base)
        if root is None:
            return None
        display = _attribute_dotted(base)
        return root, display
    return None


def _attribute_root(node: ast.Attribute) -> str | None:
    """Return the leftmost ``ast.Name.id`` in a chain of ``ast.Attribute``."""
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _attribute_dotted(node: ast.Attribute) -> str:
    """Reconstruct the dotted form, e.g. ``module.sub.Class``."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


# ---------------------------------------------------------------------------
# INH002 helpers
# ---------------------------------------------------------------------------

def _is_abc_class(
    node: ast.ClassDef,
    import_map: dict[str, str],
) -> bool:
    """Return *True* if *node* is an abstract base class.

    Detection heuristics:
    1. Inherits from a name that resolves to ``abc.ABC``.
    2. Has ``metaclass=ABCMeta`` where ``ABCMeta`` resolves to ``abc``.
    """
    for base in node.bases:
        if isinstance(base, ast.Name) and import_map.get(base.id) == "abc":
            if base.id in _abc_class_aliases(import_map):
                return True
        if isinstance(base, ast.Attribute):
            root = _attribute_root(base)
            if root is not None and import_map.get(root) == "abc" and base.attr == "ABC":
                return True
    for kw in node.keywords:
        if kw.arg == "metaclass" and isinstance(kw.value, ast.Name):
            name = kw.value.id
            if import_map.get(name) == "abc" and name in _abc_metaclass_aliases(import_map):
                return True
    return False


def _abc_class_aliases(import_map: dict[str, str]) -> set[str]:
    """Return all local names that map to abc and could be ABC."""
    # Names imported from abc that might alias ABC.
    # We check: from abc import ABC, from abc import ABC as X
    # The import map just maps local_name -> "abc".  We accept any name that
    # was imported from abc and whose *original* import name we can't easily
    # recover.  Since we only store the top-level package, we rely on a
    # heuristic: any local name mapping to "abc" that is NOT "abstractmethod"
    # and NOT "ABCMeta" is treated as a potential ABC alias.
    return {
        name
        for name, pkg in import_map.items()
        if pkg == "abc" and name not in ("abstractmethod", "ABCMeta")
    }


def _abc_metaclass_aliases(import_map: dict[str, str]) -> set[str]:
    """Return all local names that could be ABCMeta."""
    return {
        name
        for name, pkg in import_map.items()
        if pkg == "abc" and name != "abstractmethod"
        and name not in _abc_class_aliases(import_map)
    } | {
        name
        for name, pkg in import_map.items()
        if pkg == "abc" and name == "ABCMeta"
    }


def _is_abstract_method(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    import_map: dict[str, str],
) -> bool:
    """Return *True* if any decorator on *node* resolves to ``abc.abstractmethod``."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            if import_map.get(dec.id) == "abc":
                return True
        if isinstance(dec, ast.Attribute):
            root = _attribute_root(dec)
            if root is not None and import_map.get(root) == "abc" and dec.attr == "abstractmethod":
                return True
    return False


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------

class InheritanceVisitor:
    """Analyse an AST module for INH001 and INH002 violations.

    Args:
        project_packages: Top-level package names belonging to the user's
            project (for ``INH001`` internal-import detection).
        allowed_dunders: Dunder method names allowed as concrete methods
            inside ABCs (for ``INH002``).  Defaults to ``["__init__"]``.
    """

    def __init__(
        self,
        project_packages: Sequence[str] = (),
        allowed_dunders: Sequence[str] | None = None,
    ) -> None:
        self.project_packages = list(project_packages)
        self.allowed_dunders: list[str] = (
            list(allowed_dunders) if allowed_dunders is not None else ["__init__"]
        )
        self.errors: list[tuple[int, int, str]] = []

    def visit(self, tree: ast.Module) -> list[tuple[int, int, str]]:
        """Run both INH001 and INH002 checks on *tree*.

        Returns a list of ``(line, col, message)`` tuples.
        """
        self.errors = []
        import_map = build_import_map(tree)
        local_classes = _collect_top_level_classes(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_inh001(node, import_map, local_classes)
                self._check_inh002(node, import_map)

        return self.errors

    # -- INH001 -------------------------------------------------------------

    def _check_inh001(
        self,
        node: ast.ClassDef,
        import_map: dict[str, str],
        local_classes: set[str],
    ) -> None:
        """Flag internal inheritance."""
        for base in node.bases:
            resolved = _resolve_base(base)
            if resolved is None:
                continue
            lookup_name, display_name = resolved
            category = classify_name(
                lookup_name, import_map, local_classes, self.project_packages,
            )
            if category in ("same_file", "internal_relative", "internal_project"):
                self.errors.append((
                    base.lineno,
                    base.col_offset,
                    INH001.format(base=display_name),
                ))

    # -- INH002 -------------------------------------------------------------

    def _check_inh002(
        self,
        node: ast.ClassDef,
        import_map: dict[str, str],
    ) -> None:
        """Flag concrete methods in ABCs."""
        if not _is_abc_class(node, import_map):
            return
        allowed = set(self.allowed_dunders)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not _is_abstract_method(item, import_map) and item.name not in allowed:
                    self.errors.append((
                        item.lineno,
                        item.col_offset,
                        INH002.format(cls=node.name, method=item.name),
                    ))
