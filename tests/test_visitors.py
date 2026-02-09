"""Tests for AST visitors and import tracking."""

from __future__ import annotations

import ast

import pytest

from flake8_inheritance.visitors import RELATIVE_SENTINEL, ImportTracker


def track_imports(source: str) -> ImportTracker:
    """Parse source code and return a populated ImportTracker."""
    tree = ast.parse(source)
    tracker = ImportTracker()
    tracker.visit(tree)
    return tracker


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import foo", {"foo": "foo"}),
        ("import foo.bar as baz", {"baz": "foo"}),
        ("from foo.bar import Baz", {"Baz": "foo"}),
        ("from foo.bar import Baz as B", {"B": "foo"}),
        ("from .models import Base", {"Base": RELATIVE_SENTINEL}),
        ("from . import utils", {"utils": RELATIVE_SENTINEL}),
    ],
)
def test_import_mapping(source: str, expected: dict[str, str]) -> None:
    tracker = track_imports(source)
    assert tracker.imports == expected


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
