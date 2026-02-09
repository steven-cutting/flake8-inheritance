"""Tests for AST visitors and import tracking."""

from __future__ import annotations

import ast

import pytest

from flake8_inheritance.codes import INH001
from flake8_inheritance.visitors import (
    RELATIVE_SENTINEL,
    ImportTracker,
    InheritanceError,
    InheritanceVisitor,
    _collect_module_class_names,
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
) -> list[InheritanceError]:
    """Parse source, run ImportTracker + InheritanceVisitor, return errors."""
    tree = ast.parse(source)
    tracker = ImportTracker(project_package=project_package)
    tracker.visit(tree)
    module_classes = _collect_module_class_names(tree)
    visitor = InheritanceVisitor(
        import_tracker=tracker,
        module_class_names=frozenset(module_classes),
    )
    visitor.visit(tree)
    return visitor.errors


def flagged_bases(errors: list[InheritanceError]) -> list[str]:
    """Return just the base names from a list of errors."""
    return [e.base_name for e in errors]


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
        assert flagged_bases(errors) == ["Base"]
        assert errors[0].code is INH001
        assert errors[0].line == child_line

    def test_multiple_same_file_bases_flagged(self) -> None:
        source = """\
class A:
    pass

class B:
    pass

class C(A, B):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["A", "B"]

    def test_forward_declaration_flagged(self) -> None:
        """Base defined after child should still be flagged."""
        source = """\
class Child(Base):
    pass

class Base:
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_nested_class_not_treated_as_module_level(self) -> None:
        """A class nested inside another should not trigger same-file detection."""
        source = """\
class Outer:
    class Inner:
        pass

class Other(Inner):
    pass
"""
        errors = collect_errors(source)
        assert errors == []


class TestINH001RelativeImportInheritance:
    """Classes inheriting from relatively imported classes."""

    def test_relative_import_flagged(self) -> None:
        source = """\
from .models import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]
        assert errors[0].code is INH001

    def test_relative_import_dot_only_flagged(self) -> None:
        source = """\
from . import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]


class TestINH001ProjectPackageInheritance:
    """Classes inheriting from configured project package classes."""

    def test_project_package_flagged(self) -> None:
        source = """\
from myproject.models import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["Base"]
        assert errors[0].code is INH001


class TestINH001AllowedBases:
    """Inheritance from stdlib and third-party classes should not be flagged."""

    def test_stdlib_base_allowed(self) -> None:
        source = """\
from collections import OrderedDict

class MyDict(OrderedDict):
    pass
"""
        assert collect_errors(source) == []

    def test_third_party_base_allowed(self) -> None:
        source = """\
from pydantic import BaseModel

class User(BaseModel):
    pass
"""
        assert collect_errors(source) == []

    def test_unrecognized_absolute_import_not_flagged(self) -> None:
        source = """\
from somepackage import Base

class Child(Base):
    pass
"""
        assert collect_errors(source) == []  # no project_package configured


class TestINH001DynamicBases:
    """Dynamic base classes should be silently skipped."""

    def test_dynamic_base_skipped(self) -> None:
        source = """\
class Child(get_base()):
    pass
"""
        assert collect_errors(source) == []

    def test_dynamic_base_with_regular_base(self) -> None:
        source = """\
from .models import Base

class Child(Base, get_mixin()):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]


class TestINH001AttributeBases:
    """ast.Attribute base classes (e.g., module.Class) resolved correctly."""

    def test_attribute_base_from_project_package(self) -> None:
        source = """\
import myproject.models

class Child(myproject.models.Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["myproject.models.Base"]
        assert errors[0].code is INH001

    def test_attribute_base_from_stdlib(self) -> None:
        source = """\
import collections

class MyDict(collections.OrderedDict):
    pass
"""
        assert collect_errors(source) == []

    def test_attribute_base_from_third_party(self) -> None:
        source = """\
import flask

class MyApp(flask.Flask):
    pass
"""
        assert collect_errors(source) == []


class TestINH001SubscriptBases:
    """Generic base classes like Base[T] should be unwrapped and checked."""

    def test_subscript_same_file_flagged(self) -> None:
        source = """\
from typing import Generic, TypeVar

T = TypeVar("T")

class Base(Generic[T]):
    pass

class Child(Base[int]):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_subscript_relative_import_flagged(self) -> None:
        source = """\
from .models import Base

class Child(Base[int]):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_subscript_attribute_flagged(self) -> None:
        source = """\
import myproject.models

class Child(myproject.models.Base[int]):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["myproject.models.Base"]

    def test_subscript_stdlib_allowed(self) -> None:
        source = """\
from typing import Generic, TypeVar

T = TypeVar("T")

class MyClass(Generic[T]):
    pass
"""
        # Generic is stdlib, should not be flagged
        assert collect_errors(source) == []


class TestINH001NoFalsePositives:
    """Edge cases that should not produce errors."""

    def test_class_with_no_bases(self) -> None:
        source = """\
class Standalone:
    pass
"""
        assert collect_errors(source) == []

    def test_class_inheriting_from_unknown_name(self) -> None:
        """A name that was never imported and not defined in file."""
        source = """\
class Child(SomeUnknownBase):
    pass
"""
        assert collect_errors(source) == []
