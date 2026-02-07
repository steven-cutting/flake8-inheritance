"""Tests for AST visitors — import tracking, INH001, and INH002."""
from __future__ import annotations

import ast
import textwrap

import pytest

from flake8_inheritance.visitors import (
    InheritanceVisitor,
    build_import_map,
    classify_name,
    RELATIVE_SENTINEL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(source: str) -> ast.Module:
    return ast.parse(textwrap.dedent(source))


def _visit(source: str, **kwargs: object) -> list[tuple[int, int, str]]:
    tree = _parse(source)
    visitor = InheritanceVisitor(**kwargs)  # type: ignore[arg-type]
    return visitor.visit(tree)


# ===================================================================
# Task 1.2 — Import map & classification
# ===================================================================


class TestBuildImportMap:
    """build_import_map correctly maps names to top-level packages."""

    def test_import_bare(self) -> None:
        tree = _parse("import foo")
        assert build_import_map(tree) == {"foo": "foo"}

    def test_import_dotted(self) -> None:
        tree = _parse("import foo.bar")
        assert build_import_map(tree) == {"foo": "foo"}

    def test_from_import(self) -> None:
        tree = _parse("from foo.bar import Baz")
        assert build_import_map(tree) == {"Baz": "foo"}

    def test_from_import_alias(self) -> None:
        tree = _parse("from foo.bar import Baz as B")
        assert build_import_map(tree) == {"B": "foo"}

    def test_relative_import(self) -> None:
        tree = _parse("from .models import Base")
        assert build_import_map(tree) == {"Base": RELATIVE_SENTINEL}

    def test_relative_import_dot_only(self) -> None:
        tree = _parse("from . import utils")
        assert build_import_map(tree) == {"utils": RELATIVE_SENTINEL}

    def test_relative_import_parent(self) -> None:
        tree = _parse("from ..core import Thing")
        assert build_import_map(tree) == {"Thing": RELATIVE_SENTINEL}

    def test_star_import_skipped(self) -> None:
        tree = _parse("from myproject.models import *")
        assert build_import_map(tree) == {}


class TestClassifyName:
    """classify_name returns the correct category."""

    def test_same_file(self) -> None:
        assert classify_name("Foo", {}, {"Foo"}, []) == "same_file"

    def test_internal_relative(self) -> None:
        assert classify_name("Base", {"Base": RELATIVE_SENTINEL}, set(), []) == "internal_relative"

    def test_internal_project(self) -> None:
        assert classify_name("X", {"X": "myproject"}, set(), ["myproject"]) == "internal_project"

    def test_stdlib(self) -> None:
        assert classify_name("OrderedDict", {"OrderedDict": "collections"}, set(), []) == "stdlib"

    def test_external(self) -> None:
        assert classify_name("BaseModel", {"BaseModel": "pydantic"}, set(), []) == "external"

    def test_unknown(self) -> None:
        assert classify_name("Whatever", {}, set(), []) == "unknown"

    def test_alias_handling(self) -> None:
        imap = {"B": "foo"}
        assert classify_name("B", imap, set(), ["foo"]) == "internal_project"


# ===================================================================
# Task 1.3 — INH001 detection
# ===================================================================


class TestINH001:
    """INH001 flags internal inheritance."""

    def test_same_file_inheritance(self) -> None:
        errors = _visit("""\
            class Base:
                pass
            class Child(Base):
                pass
        """)
        assert len(errors) == 1
        assert "INH001" in errors[0][2]
        assert "Base" in errors[0][2]

    def test_relative_import_inheritance(self) -> None:
        errors = _visit("""\
            from .models import Base
            class Child(Base):
                pass
        """)
        assert len(errors) == 1
        assert "INH001" in errors[0][2]

    def test_project_package_import(self) -> None:
        errors = _visit(
            """\
            from myproject.models import Base
            class Child(Base):
                pass
            """,
            project_packages=["myproject"],
        )
        assert len(errors) == 1
        assert "INH001" in errors[0][2]

    def test_external_not_flagged(self) -> None:
        errors = _visit("""\
            from pydantic import BaseModel
            class User(BaseModel):
                pass
        """)
        assert errors == []

    def test_stdlib_not_flagged(self) -> None:
        errors = _visit("""\
            from collections import OrderedDict
            class MyDict(OrderedDict):
                pass
        """)
        assert errors == []

    def test_unknown_not_flagged(self) -> None:
        # Absolute import with no project_packages configured → external
        errors = _visit("""\
            from somelib import Thing
            class Foo(Thing):
                pass
        """)
        assert errors == []

    def test_dynamic_base_skipped(self) -> None:
        errors = _visit("""\
            class Foo(get_base()):
                pass
        """)
        assert errors == []

    def test_dotted_base_project_package(self) -> None:
        errors = _visit(
            """\
            import myproject.models
            class Foo(myproject.models.Bar):
                pass
            """,
            project_packages=["myproject"],
        )
        assert len(errors) == 1
        assert "myproject.models.Bar" in errors[0][2]


# ===================================================================
# Task 1.4 — INH002 detection
# ===================================================================


class TestINH002:
    """INH002 flags concrete methods in ABCs."""

    def test_pure_abc_no_errors(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @abstractmethod
                def do_thing(self):
                    pass
        """)
        assert errors == []

    def test_abc_with_concrete_method(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @abstractmethod
                def do_thing(self):
                    pass
                def helper(self):
                    pass
        """)
        assert len(errors) == 1
        assert "INH002" in errors[0][2]
        assert "MyABC" in errors[0][2]
        assert "helper" in errors[0][2]

    def test_init_allowed_by_default(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                def __init__(self):
                    pass
                @abstractmethod
                def do_thing(self):
                    pass
        """)
        assert errors == []

    def test_init_flagged_with_empty_allowed(self) -> None:
        errors = _visit(
            """\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                def __init__(self):
                    pass
                @abstractmethod
                def do_thing(self):
                    pass
            """,
            allowed_dunders=[],
        )
        assert len(errors) == 1
        assert "__init__" in errors[0][2]

    def test_staticmethod_abstractmethod_not_flagged(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @staticmethod
                @abstractmethod
                def do_thing():
                    pass
        """)
        assert errors == []

    def test_classmethod_abstractmethod_not_flagged(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @classmethod
                @abstractmethod
                def do_thing(cls):
                    pass
        """)
        assert errors == []

    def test_abcmeta_metaclass_detection(self) -> None:
        errors = _visit("""\
            from abc import ABCMeta, abstractmethod
            class MyABC(metaclass=ABCMeta):
                def helper(self):
                    pass
        """)
        assert len(errors) == 1
        assert "INH002" in errors[0][2]

    def test_aliased_abc(self) -> None:
        errors = _visit("""\
            from abc import ABC as AbstractBase, abstractmethod
            class MyABC(AbstractBase):
                def helper(self):
                    pass
        """)
        assert len(errors) == 1
        assert "INH002" in errors[0][2]

    def test_non_abc_not_flagged(self) -> None:
        errors = _visit("""\
            class Regular:
                def helper(self):
                    pass
        """)
        # No INH002 — Regular is not an ABC.
        inh002_errors = [e for e in errors if "INH002" in e[2]]
        assert inh002_errors == []

    def test_async_abstractmethod_not_flagged(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @abstractmethod
                async def do_thing(self):
                    pass
        """)
        assert errors == []


# ===================================================================
# Task 1.5 — Edge cases
# ===================================================================


class TestEdgeCases:
    """Edge case hardening — no crashes, no false positives."""

    def test_star_import_no_crash(self) -> None:
        errors = _visit("""\
            from myproject.models import *
            class Child(Base):
                pass
        """)
        # Base is unknown → not flagged
        assert errors == []

    def test_empty_file(self) -> None:
        errors = _visit("")
        assert errors == []

    def test_no_classes(self) -> None:
        errors = _visit("""\
            import os
            x = 1
            def foo():
                pass
        """)
        assert errors == []

    def test_deeply_nested_class(self) -> None:
        errors = _visit("""\
            class Outer:
                pass
            def factory():
                class Inner(Outer):
                    pass
        """)
        # Inner inherits from Outer (top-level class) → flagged
        inh001 = [e for e in errors if "INH001" in e[2]]
        assert len(inh001) == 1
        assert "Outer" in inh001[0][2]

    def test_many_bases_mixed(self) -> None:
        errors = _visit(
            """\
            from collections import OrderedDict
            from pydantic import BaseModel
            from myproject.a import A
            from myproject.b import B
            from .local import C
            import os

            class Mega(OrderedDict, BaseModel, A, B, C):
                pass
            """,
            project_packages=["myproject"],
        )
        inh001 = [e for e in errors if "INH001" in e[2]]
        flagged_bases = {e[2] for e in inh001}
        assert len(inh001) == 3  # A, B, C
        assert any("A" in msg for msg in flagged_bases)
        assert any("B" in msg for msg in flagged_bases)
        assert any("C" in msg for msg in flagged_bases)

    def test_multiple_inheritance_mixed(self) -> None:
        errors = _visit(
            """\
            from pydantic import BaseModel
            from .models import MyBase
            class Foo(BaseModel, MyBase):
                pass
            """,
        )
        inh001 = [e for e in errors if "INH001" in e[2]]
        assert len(inh001) == 1
        assert "MyBase" in inh001[0][2]

    def test_attribute_base_unimported_module(self) -> None:
        errors = _visit("""\
            class Foo(unknown.Bar):
                pass
        """)
        assert errors == []

    def test_async_abstract_in_abc(self) -> None:
        errors = _visit("""\
            from abc import ABC, abstractmethod
            class MyABC(ABC):
                @abstractmethod
                async def do_thing(self):
                    pass
        """)
        assert errors == []
