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
    import argparse
    import ast
    from collections.abc import Generator

    from flake8.options.manager import OptionManager


def _parse_comma_separated(value: str) -> tuple[str, ...]:
    """Split a comma-separated string into a tuple, stripping whitespace."""
    if not value or not value.strip():
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


class InheritanceChecker:
    """Flake8 AST checker enforcing composition over inheritance.

    This checker implements the flake8 plugin contract:
    - ``name`` and ``version``: class-level metadata for ``flake8 --version``.
    - ``__init__(self, tree)``: receives the AST for each file.
    - ``run()``: generator yielding ``(line, col, message, type)`` tuples.
    - ``add_options(parser)``: registers CLI/config options with flake8.
    - ``parse_options(options)``: stores parsed option values as class attrs.
    """

    name: ClassVar[str] = "flake8-inheritance"
    version: ClassVar[str] = importlib.metadata.version("flake8-inheritance")

    _project_packages: ClassVar[tuple[str, ...]] = ()
    _inh002_allowed_dunders: ClassVar[tuple[str, ...] | None] = None

    def __init__(self, tree: ast.AST) -> None:
        """Initialize the checker with the AST for a single file."""
        self._tree = tree

    @classmethod
    def add_options(cls, parser: OptionManager) -> None:
        """Register plugin options with flake8's option manager."""
        parser.add_option(
            "--project-packages",
            default="",
            parse_from_config=True,
            comma_separated_list=True,
            help="Comma-separated list of project package names to treat as internal.",
        )
        parser.add_option(
            "--inh002-allowed-dunders",
            default=None,
            parse_from_config=True,
            comma_separated_list=True,
            help="Comma-separated list of dunder methods allowed in ABCs.",
        )

    @classmethod
    def parse_options(cls, options: argparse.Namespace) -> None:
        """Store parsed option values as class attributes."""
        raw_packages = options.project_packages
        if isinstance(raw_packages, list):
            cls._project_packages = tuple(item.strip() for item in raw_packages if item.strip())
        else:
            cls._project_packages = _parse_comma_separated(raw_packages)

        raw_dunders = options.inh002_allowed_dunders
        if raw_dunders is None:
            cls._inh002_allowed_dunders = None
        elif isinstance(raw_dunders, list):
            cls._inh002_allowed_dunders = tuple(
                item.strip() for item in raw_dunders if item.strip()
            )
        else:
            cls._inh002_allowed_dunders = _parse_comma_separated(raw_dunders)

    def run(self) -> Generator[tuple[int, int, str, type], None, None]:
        """Run the checker and yield flake8 error tuples."""
        # Create a tracker for each configured project package
        trackers: list[ImportTracker] = []
        if self._project_packages:
            for pkg in self._project_packages:
                tracker = ImportTracker(project_package=pkg)
                tracker.visit(self._tree)
                trackers.append(tracker)
        else:
            tracker = ImportTracker()
            tracker.visit(self._tree)
            trackers.append(tracker)

        module_classes = frozenset(collect_module_class_names(self._tree))

        # Use the first tracker for primary classification; merge errors from all
        primary_tracker = trackers[0]

        inh_visitor = InheritanceVisitor(primary_tracker, module_classes)
        inh_visitor.visit(self._tree)

        # For additional project packages, run extra visitors and collect errors
        for extra_tracker in trackers[1:]:
            extra_visitor = InheritanceVisitor(extra_tracker, module_classes)
            extra_visitor.visit(self._tree)
            # Add errors not already found
            existing = {(e.line, e.col, e.base) for e in inh_visitor.errors}
            for error in extra_visitor.errors:
                if (error.line, error.col, error.base) not in existing:
                    inh_visitor.errors.append(error)

        # Build allowed dunder configuration for ABCPurityVisitor
        allowed_dunders = (
            None
            if self._inh002_allowed_dunders is None
            else frozenset(self._inh002_allowed_dunders)
        )
        abc_visitor = ABCPurityVisitor(primary_tracker, allowed_dunders=allowed_dunders)
        abc_visitor.visit(self._tree)

        checker_cls = type(self)
        for inh_error in inh_visitor.errors:
            yield (inh_error.line, inh_error.col, inh_error.format(), checker_cls)
        for abc_error in abc_visitor.errors:
            yield (abc_error.line, abc_error.col, abc_error.format(), checker_cls)
