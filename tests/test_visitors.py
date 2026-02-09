"""Tests for AST visitors and import tracking."""

from __future__ import annotations

import ast

import pytest

from flake8_inheritance.visitors import (
    RELATIVE_SENTINEL,
    ImportTracker,
    InheritanceVisitor,
)


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


# ---------------------------------------------------------------------------
# Helpers for INH001 tests
# ---------------------------------------------------------------------------


def collect_errors(
    source: str,
    project_package: str | None = None,
) -> list[tuple[int, int, str]]:
    """Parse source, run ImportTracker + InheritanceVisitor, return errors."""
    tree = ast.parse(source)
    tracker = ImportTracker(project_package=project_package)
    tracker.visit(tree)
    visitor = InheritanceVisitor(import_tracker=tracker)
    visitor.visit(tree)
    return visitor.errors


# ---------------------------------------------------------------------------
# INH001 — detect internal inheritance
# ---------------------------------------------------------------------------


class TestINH001SameFileInheritance:
    """Classes inheriting from other classes defined in the same file."""

    def test_same_file_class_flagged(self) -> None:
        source = """\
class Base:
    pass

class Child(Base):
    pass
"""
        child_line = 4
        errors = collect_errors(source)
        assert len(errors) == 1
        line, col, msg = errors[0]
        assert line == child_line
        assert col == 0
        assert "INH001" in msg
        assert "Base" in msg

    def test_multiple_same_file_bases_flagged(self) -> None:
        source = """\
class A:
    pass

class B:
    pass

class C(A, B):
    pass
"""
        expected_error_count = 2
        errors = collect_errors(source)
        assert len(errors) == expected_error_count


class TestINH001RelativeImportInheritance:
    """Classes inheriting from relatively imported classes."""

    def test_relative_import_flagged(self) -> None:
        source = """\
from .models import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source)
        assert len(errors) == 1
        assert "INH001" in errors[0][2]
        assert "Base" in errors[0][2]

    def test_relative_import_dot_only_flagged(self) -> None:
        source = """\
from . import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source)
        assert len(errors) == 1


class TestINH001ProjectPackageInheritance:
    """Classes inheriting from configured project package classes."""

    def test_project_package_flagged(self) -> None:
        source = """\
from myproject.models import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert len(errors) == 1
        assert "INH001" in errors[0][2]
        assert "Base" in errors[0][2]


class TestINH001AllowedBases:
    """Inheritance from stdlib and third-party classes should not be flagged."""

    def test_stdlib_base_allowed(self) -> None:
        source = """\
from collections import OrderedDict

class MyDict(OrderedDict):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_third_party_base_allowed(self) -> None:
        source = """\
from pydantic import BaseModel

class User(BaseModel):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_unrecognized_absolute_import_not_flagged(self) -> None:
        source = """\
from somepackage import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source)  # no project_package configured
        assert errors == []


class TestINH001DynamicBases:
    """Dynamic base classes should be silently skipped."""

    def test_dynamic_base_skipped(self) -> None:
        source = """\
class Child(get_base()):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_dynamic_base_with_regular_base(self) -> None:
        source = """\
from .models import Base

class Child(Base, get_mixin()):
    pass
"""
        errors = collect_errors(source)
        assert len(errors) == 1
        assert "Base" in errors[0][2]


class TestINH001AttributeBases:
    """ast.Attribute base classes (e.g., module.Class) resolved correctly."""

    def test_attribute_base_from_project_package(self) -> None:
        source = """\
import myproject.models

class Child(myproject.models.Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert len(errors) == 1
        assert "INH001" in errors[0][2]
        assert "myproject.models.Base" in errors[0][2]

    def test_attribute_base_from_stdlib(self) -> None:
        source = """\
import collections

class MyDict(collections.OrderedDict):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_attribute_base_from_third_party(self) -> None:
        source = """\
import flask

class MyApp(flask.Flask):
    pass
"""
        errors = collect_errors(source)
        assert errors == []


class TestINH001NoFalsePositives:
    """Edge cases that should not produce errors."""

    def test_class_with_no_bases(self) -> None:
        source = """\
class Standalone:
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_class_inheriting_from_unknown_name(self) -> None:
        """A name that was never imported and not defined in file."""
        source = """\
class Child(SomeUnknownBase):
    pass
"""
        errors = collect_errors(source)
        assert errors == []
