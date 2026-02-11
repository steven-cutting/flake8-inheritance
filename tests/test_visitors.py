"""Tests for AST visitors and import tracking."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from flake8_inheritance.codes import INH001, INH002
from flake8_inheritance.visitors import (
    RELATIVE_SENTINEL,
    ABCPurityError,
    ABCPurityVisitor,
    ImportTracker,
    InheritanceError,
    InheritanceVisitor,
    collect_module_class_names,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    """Read and return the contents of a fixture file."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


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
    module_classes = collect_module_class_names(tree)
    visitor = InheritanceVisitor(
        import_tracker=tracker,
        module_class_names=frozenset(module_classes),
    )
    visitor.visit(tree)
    return visitor.errors


def flagged_bases(errors: list[InheritanceError]) -> list[str]:
    """Return just the base names from a list of INH001 errors."""
    return [e.base for e in errors]


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
        source = _read_fixture("dynamic_bases.py")
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


# ---------------------------------------------------------------------------
# Helpers for INH002 tests
# ---------------------------------------------------------------------------


def collect_inh002_errors(source: str) -> list[ABCPurityError]:
    """Parse source, run ImportTracker + ABCPurityVisitor, return errors."""
    tree = ast.parse(source)
    tracker = ImportTracker()
    tracker.visit(tree)
    visitor = ABCPurityVisitor(import_tracker=tracker)
    visitor.visit(tree)
    return visitor.errors


def flagged_methods(errors: list[ABCPurityError]) -> list[str]:
    """Return just the method names from INH002 errors."""
    return [e.method for e in errors]


# ---------------------------------------------------------------------------
# INH002 — detect impure ABCs (concrete methods in abstract base classes)
# ---------------------------------------------------------------------------


class TestINH002PureABC:
    """Pure ABCs (only abstract methods) should not be flagged."""

    def test_pure_abc_passes(self) -> None:
        source = _read_fixture("pure_abc.py")
        assert collect_inh002_errors(source) == []

    def test_empty_abc_passes(self) -> None:
        source = """\
from abc import ABC

class MyABC(ABC):
    pass
"""
        assert collect_inh002_errors(source) == []


class TestINH002ConcreteMethodFlagged:
    """Concrete methods in ABCs should be flagged."""

    def test_concrete_method_in_abc_flagged(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert len(errors) == 1
        assert errors[0].code is INH002
        assert errors[0].method == "concrete_helper"
        assert errors[0].cls == "MyABC"

    def test_multiple_concrete_methods_flagged(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @abstractmethod
    def do_thing(self):
        pass

    def helper_one(self):
        return 1

    def helper_two(self):
        return 2
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["helper_one", "helper_two"]

    def test_all_concrete_no_abstract_flagged(self) -> None:
        """An ABC with no abstract methods at all flags every method."""
        source = """\
from abc import ABC

class MyABC(ABC):
    def foo(self):
        return 1

    def bar(self):
        return 2
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["foo", "bar"]


class TestINH002InitAllowed:
    """__init__ should be allowed by default in ABCs."""

    def test_init_allowed(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []

    def test_dunder_methods_allowed(self) -> None:
        """Dunder methods like __init__, __repr__ etc. should be allowed."""
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    def __init__(self):
        pass

    def __repr__(self):
        return "MyABC()"

    @abstractmethod
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []


class TestINH002DecoratorCombinations:
    """@staticmethod + @abstractmethod and @classmethod + @abstractmethod pass."""

    def test_staticmethod_abstractmethod_passes(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @staticmethod
    @abstractmethod
    def do_thing():
        pass
"""
        assert collect_inh002_errors(source) == []

    def test_classmethod_abstractmethod_passes(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @classmethod
    @abstractmethod
    def do_thing(cls):
        pass
"""
        assert collect_inh002_errors(source) == []

    def test_plain_staticmethod_flagged(self) -> None:
        """A staticmethod without @abstractmethod is concrete."""
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @abstractmethod
    def do_thing(self):
        pass

    @staticmethod
    def helper():
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["helper"]

    def test_plain_classmethod_flagged(self) -> None:
        """A classmethod without @abstractmethod is concrete."""
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @abstractmethod
    def do_thing(self):
        pass

    @classmethod
    def create(cls):
        return cls()
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["create"]


class TestINH002ABCMetaDetection:
    """ABCMeta metaclass should be detected as ABC."""

    def test_abcmeta_metaclass_detected(self) -> None:
        source = """\
from abc import ABCMeta, abstractmethod

class MyABC(metaclass=ABCMeta):
    @abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]

    def test_pure_abcmeta_passes(self) -> None:
        source = """\
from abc import ABCMeta, abstractmethod

class MyABC(metaclass=ABCMeta):
    @abstractmethod
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []


class TestINH002ABCAlias:
    """ABC imported with an alias should still be detected."""

    def test_abc_alias_detected(self) -> None:
        source = """\
from abc import ABC as AbstractBase, abstractmethod

class MyABC(AbstractBase):
    @abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]

    def test_abcmeta_alias_detected(self) -> None:
        source = """\
from abc import ABCMeta as Meta, abstractmethod

class MyABC(metaclass=Meta):
    @abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]


class TestINH002NonABCIgnored:
    """Non-ABC classes should not be checked for method purity."""

    def test_regular_class_ignored(self) -> None:
        source = """\
class RegularClass:
    def method(self):
        return 42
"""
        assert collect_inh002_errors(source) == []

    def test_class_inheriting_from_non_abc(self) -> None:
        source = """\
from collections import OrderedDict

class MyDict(OrderedDict):
    def custom_method(self):
        return 42
"""
        assert collect_inh002_errors(source) == []


class TestINH002ModuleQualifiedABC:
    """Module-qualified ABC usage: ``import abc; class X(abc.ABC): ...``."""

    def test_import_abc_dot_abc_detected(self) -> None:
        source = """\
import abc

class MyABC(abc.ABC):
    @abc.abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]

    def test_import_abc_dot_abc_pure_passes(self) -> None:
        source = """\
import abc

class MyABC(abc.ABC):
    @abc.abstractmethod
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []

    def test_import_abc_dot_abcmeta_metaclass(self) -> None:
        source = """\
import abc

class MyABC(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]

    def test_import_abc_aliased_module(self) -> None:
        """``import abc as a; class X(a.ABC): ...``."""
        source = """\
import abc as a

class MyABC(a.ABC):
    @a.abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert flagged_methods(errors) == ["concrete_helper"]


class TestINH002ABCMetaFalsePositives:
    """ABCMeta in base classes should not be treated as ABC base."""

    def test_class_inheriting_from_abcmeta_not_treated_as_abc_base(self) -> None:
        """``class X(ABCMeta)`` is a metaclass def, not an ABC."""
        source = """\
from abc import ABCMeta

class MyMeta(ABCMeta):
    def some_method(self):
        return 42
"""
        assert collect_inh002_errors(source) == []

    def test_metaclass_abstractmethod_not_abc(self) -> None:
        """``metaclass=abstractmethod`` should not be treated as ABC."""
        source = """\
from abc import abstractmethod

class MyClass(metaclass=abstractmethod):
    def some_method(self):
        return 42
"""
        assert collect_inh002_errors(source) == []


class TestINH002AbstractmethodAliases:
    """Aliased abstractmethod imports should be resolved."""

    def test_abstractmethod_alias_recognized(self) -> None:
        source = """\
from abc import ABC, abstractmethod as am

class MyABC(ABC):
    @am
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []

    def test_module_qualified_abstractmethod_recognized(self) -> None:
        source = """\
import abc

class MyABC(abc.ABC):
    @abc.abstractmethod
    def do_thing(self):
        pass
"""
        assert collect_inh002_errors(source) == []


class TestINH002ErrorFormat:
    """INH002 errors should format correctly with class and method names."""

    def test_error_format_includes_class_and_method(self) -> None:
        source = """\
from abc import ABC, abstractmethod

class MyABC(ABC):
    @abstractmethod
    def do_thing(self):
        pass

    def concrete_helper(self):
        return 42
"""
        errors = collect_inh002_errors(source)
        assert len(errors) == 1
        formatted = errors[0].format()
        assert "MyABC" in formatted
        assert "concrete_helper" in formatted
        assert formatted.startswith("INH002")


# ---------------------------------------------------------------------------
# Error object immutability and hashability
# ---------------------------------------------------------------------------


class TestErrorImmutability:
    """Error objects must be truly immutable and hashable."""

    def test_inh001_error_is_hashable(self) -> None:
        errors = collect_errors("class A:\n    pass\n\nclass B(A):\n    pass\n")
        assert len(errors) == 1
        # Must be hashable (usable in sets and as dict keys)
        hash(errors[0])
        assert len({errors[0], errors[0]}) == 1

    def test_inh002_error_is_hashable(self) -> None:
        source = """\
from abc import ABC

class MyABC(ABC):
    def foo(self):
        return 1
"""
        errors = collect_inh002_errors(source)
        assert len(errors) == 1
        # Must be hashable (usable in sets and as dict keys)
        hash(errors[0])
        assert len({errors[0], errors[0]}) == 1

    def test_inh001_error_is_immutable(self) -> None:
        errors = collect_errors("class A:\n    pass\n\nclass B(A):\n    pass\n")
        with pytest.raises(AttributeError):
            errors[0].line = 99  # type: ignore[misc]

    def test_inh002_error_is_immutable(self) -> None:
        source = """\
from abc import ABC

class MyABC(ABC):
    def foo(self):
        return 1
"""
        errors = collect_inh002_errors(source)
        with pytest.raises(AttributeError):
            errors[0].line = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Edge case hardening
# ---------------------------------------------------------------------------


class TestStarImports:
    """Star imports should be skipped without crashing."""

    def test_star_import_no_crash(self) -> None:
        """``from myproject.models import *`` must not crash."""
        source = _read_fixture("star_imports.py")
        # Should not raise — star imports are silently recorded
        errors = collect_errors(source, project_package="myproject")
        # "Base" is not explicitly imported, so it's unknown — no error
        assert errors == []

    def test_star_import_relative_no_crash(self) -> None:
        """``from . import *`` must not crash."""
        source = """\
from . import *

class Child(SomeBase):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_star_import_with_regular_imports(self) -> None:
        """Star import alongside regular imports should not interfere."""
        source = """\
from myproject.models import *
from .base import Base

class Child(Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["Base"]

    def test_star_import_inh002_no_crash(self) -> None:
        """Star imports should not crash ABCPurityVisitor either."""
        source = """\
from abc import *

class MyABC(ABC):
    def concrete_method(self):
        return 42
"""
        # Star import means "ABC" and "abstractmethod" are not tracked by name
        # so the visitor may not detect this as an ABC — that's acceptable.
        # The key thing is: no crash.
        collect_inh002_errors(source)


class TestEmptyAndNoClassFiles:
    """Empty files and files with no class definitions."""

    def test_empty_file_inh001(self) -> None:
        source = _read_fixture("empty_file.py")
        errors = collect_errors(source)
        assert errors == []

    def test_empty_file_inh002(self) -> None:
        source = _read_fixture("empty_file.py")
        errors = collect_inh002_errors(source)
        assert errors == []

    def test_file_with_only_imports(self) -> None:
        source = """\
import os
from collections import OrderedDict
"""
        assert collect_errors(source) == []
        assert collect_inh002_errors(source) == []

    def test_file_with_only_functions(self) -> None:
        source = _read_fixture("no_classes.py")
        assert collect_errors(source) == []
        assert collect_inh002_errors(source) == []

    def test_file_with_only_variables(self) -> None:
        source = """\
x = 1
y = "hello"
z = [1, 2, 3]
"""
        assert collect_errors(source) == []

    def test_collect_module_class_names_empty(self) -> None:
        source = _read_fixture("empty_file.py")
        tree = ast.parse(source)
        assert collect_module_class_names(tree) == set()

    def test_collect_module_class_names_no_classes(self) -> None:
        tree = ast.parse("x = 1\ndef foo(): pass\n")
        assert collect_module_class_names(tree) == set()


class TestDeeplyNestedClasses:
    """Classes inside functions or nested deeply in other classes."""

    def test_class_inside_function_not_module_level(self) -> None:
        """A class defined inside a function should not be treated as module-level."""
        source = """\
def factory():
    class Inner:
        pass
    return Inner

class Other(Inner):
    pass
"""
        # Inner is not a module-level class, so Other(Inner) where Inner is
        # unknown should produce no error
        errors = collect_errors(source)
        assert errors == []

    def test_class_nested_two_levels(self) -> None:
        """Class nested inside a class inside a class."""
        source = """\
class Outer:
    class Middle:
        class Inner:
            pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_class_inside_if_block(self) -> None:
        """Class defined inside an if block IS a module-level statement."""
        source = """\
class Base:
    pass

if True:
    class Child(Base):
        pass
"""
        # Note: ast.Module.body includes the if statement, but the ClassDef
        # inside it is not directly in module.body — it's in the if.body.
        # collect_module_class_names only scans module.body directly.
        # However InheritanceVisitor.visit_ClassDef will still find Child
        # and check Base — which IS in module_classes.
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_deeply_nested_class_inheriting_from_module_level(self) -> None:
        """A nested class inheriting from a module-level class."""
        source = """\
class Base:
    pass

class Outer:
    class Inner(Base):
        pass
"""
        # Inner inherits from Base which is module-level — should be flagged
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_class_in_function_inheriting_from_import(self) -> None:
        """Class inside function inheriting from imported class."""
        source = """\
from .models import Base

def factory():
    class Product(Base):
        pass
    return Product
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]


class TestManyBaseClasses:
    """Classes with many base classes should not exhibit quadratic behavior."""

    def test_ten_plus_bases_no_error(self) -> None:
        """A class with 10+ external bases should produce no errors."""
        bases = ", ".join(f"Base{i}" for i in range(15))
        imports = "\n".join(f"from external_pkg import Base{i}" for i in range(15))
        source = f"""\
{imports}

class Child({bases}):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_ten_plus_internal_bases_all_flagged(self) -> None:
        """A class with 10+ internal bases should flag all of them."""
        num_bases = 12
        base_defs = "\n".join(f"class Base{i}:\n    pass\n" for i in range(num_bases))
        bases = ", ".join(f"Base{i}" for i in range(num_bases))
        source = f"""\
{base_defs}
class Child({bases}):
    pass
"""
        errors = collect_errors(source)
        assert len(errors) == num_bases
        for i, err in enumerate(errors):
            assert err.base == f"Base{i}"

    @pytest.mark.timeout(1)
    def test_many_bases_performance(self) -> None:
        """Processing 10+ bases should complete in well under 1 second."""
        num_bases = 50
        bases = ", ".join(f"Base{i}" for i in range(num_bases))
        imports = "\n".join(f"from .models import Base{i}" for i in range(num_bases))
        source = f"""\
{imports}

class Child({bases}):
    pass
"""
        errors = collect_errors(source)
        assert len(errors) == num_bases


class TestAttributeBasesEdgeCases:
    """Additional edge cases for ast.Attribute base classes."""

    def test_deeply_nested_attribute_base(self) -> None:
        """``class Foo(a.b.c.d.Base):`` should resolve correctly."""
        source = """\
import myproject

class Child(myproject.sub.models.Base):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["myproject.sub.models.Base"]

    def test_attribute_base_unknown_root(self) -> None:
        """Attribute base with unknown root module should not be flagged."""
        source = """\
class Child(unknown_module.Base):
    pass
"""
        errors = collect_errors(source)
        assert errors == []

    def test_attribute_base_relative_import(self) -> None:
        """Attribute access on a relatively imported module."""
        source = """\
from . import models

class Child(models.Base):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["models.Base"]


class TestMixedInternalExternalBases:
    """Multiple inheritance with mixed internal and external bases."""

    def test_mixed_internal_and_external(self) -> None:
        """Only internal bases should be flagged, external ones skipped."""
        source = """\
from collections import OrderedDict
from .models import Base

class Child(Base, OrderedDict):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_mixed_same_file_and_stdlib(self) -> None:
        source = """\
import typing

class Base:
    pass

class Child(Base, typing.Protocol):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["Base"]

    def test_mixed_internal_external_and_dynamic(self) -> None:
        """Internal, external, and dynamic bases together."""
        source = """\
from pydantic import BaseModel
from .models import InternalBase

class Child(InternalBase, BaseModel, get_mixin()):
    pass
"""
        errors = collect_errors(source)
        assert flagged_bases(errors) == ["InternalBase"]

    def test_mixed_project_package_and_third_party(self) -> None:
        source = """\
import flask
import myproject.models

class MyView(myproject.models.BaseView, flask.views.View):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        assert flagged_bases(errors) == ["myproject.models.BaseView"]

    def test_all_three_internal_types_mixed(self) -> None:
        """Same-file, relative import, and project package bases all flagged."""
        source = """\
from .mixins import Mixin
from myproject.models import Model

class LocalBase:
    pass

class Child(LocalBase, Mixin, Model):
    pass
"""
        errors = collect_errors(source, project_package="myproject")
        expected = ["LocalBase", "Mixin", "Model"]
        assert flagged_bases(errors) == expected
