"""Tests for AST visitors and import tracking."""

from __future__ import annotations

import ast

from flake8_inheritance.visitors import ImportTracker


def track_imports(source: str) -> ImportTracker:
    """Parse source code and return a populated ImportTracker."""
    tree = ast.parse(source)
    tracker = ImportTracker()
    tracker.visit(tree)
    return tracker


def test_import_statement_maps_module_name() -> None:
    tracker = track_imports("import foo")
    assert tracker.imports == {"foo": "foo"}


def test_import_statement_with_alias_tracks_local_name() -> None:
    tracker = track_imports("import foo.bar as baz")
    assert tracker.imports == {"baz": "foo"}


def test_from_import_maps_to_top_level_package() -> None:
    tracker = track_imports("from foo.bar import Baz")
    assert tracker.imports == {"Baz": "foo"}


def test_from_import_with_alias_tracks_alias_name() -> None:
    tracker = track_imports("from foo.bar import Baz as B")
    assert tracker.imports == {"B": "foo"}


def test_relative_import_records_relative_sentinel() -> None:
    tracker = track_imports("from .models import Base")
    assert tracker.imports == {"Base": "__relative__"}


def test_relative_import_without_module_records_relative_sentinel() -> None:
    tracker = track_imports("from . import utils")
    assert tracker.imports == {"utils": "__relative__"}


def test_classification_categories() -> None:
    source = """\
import sys
import requests
import internal_pkg.utils
from . import local_mod
"""
    tree = ast.parse(source)
    tracker = ImportTracker(project_package="internal_pkg")
    tracker.visit(tree)

    assert tracker.classify("sys") == "stdlib"
    assert tracker.classify("requests") == "external"
    assert tracker.classify("internal_pkg") == "internal"
    assert tracker.classify("local_mod") == "same_file"
    assert tracker.classify("missing") == "unknown"


def test_project_package_overrides_stdlib_name() -> None:
    tracker = ImportTracker(project_package="email")
    tracker.visit(ast.parse("import email"))

    assert tracker.classify("email") == "internal"


def test_empty_import_from_module_classifies_unknown() -> None:
    tracker = ImportTracker()
    node = ast.ImportFrom(module=None, names=[ast.alias(name="Thing")], level=0)
    tracker.visit_ImportFrom(node)

    assert tracker.classify("Thing") == "unknown"
