"""Tests for InheritanceChecker.run() integration with visitors."""

from __future__ import annotations

import ast
import textwrap

from flake8_inheritance.checker import InheritanceChecker


def _run_checker(source: str) -> list[tuple[int, int, str, type]]:
    """Parse *source* and return all errors from ``InheritanceChecker.run()``."""
    tree = ast.parse(textwrap.dedent(source))
    return list(InheritanceChecker(tree).run())


class TestCheckerINH001:
    """InheritanceChecker.run() yields INH001 errors for internal inheritance."""

    def test_same_file_inheritance(self) -> None:
        """Inheriting from a class defined in the same file triggers INH001."""
        source = """\
            class Base:
                pass

            class Child(Base):
                pass
        """
        child_line = 4
        results = _run_checker(source)

        assert len(results) == 1
        line, col, message, cls = results[0]
        assert line == child_line
        assert col == 0
        assert "INH001" in message
        assert "Base" in message
        assert cls is InheritanceChecker

    def test_relative_import_inheritance(self) -> None:
        """Inheriting from a relative import triggers INH001."""
        source = """\
            from .models import BaseModel

            class Child(BaseModel):
                pass
        """
        child_line = 3
        results = _run_checker(source)

        assert len(results) == 1
        line, col, message, cls = results[0]
        assert line == child_line
        assert col == 0
        assert "INH001" in message
        assert "BaseModel" in message

    def test_no_inheritance_no_errors(self) -> None:
        """A file with no inheritance produces no errors."""
        source = """\
            class Standalone:
                pass
        """
        assert _run_checker(source) == []

    def test_stdlib_inheritance_allowed(self) -> None:
        """Inheriting from stdlib classes does not trigger INH001."""
        source = """\
            from collections import OrderedDict

            class MyDict(OrderedDict):
                pass
        """
        assert _run_checker(source) == []

    def test_multiple_same_file_classes(self) -> None:
        """Multiple internal inheritance violations each produce an error."""
        source = """\
            class A:
                pass

            class B:
                pass

            class C(A):
                pass

            class D(B):
                pass
        """
        expected_count = 2
        results = _run_checker(source)

        assert len(results) == expected_count
        messages = [r[2] for r in results]
        assert any("A" in m for m in messages)
        assert any("B" in m for m in messages)


class TestCheckerINH002:
    """InheritanceChecker.run() yields INH002 errors for impure ABCs."""

    def test_concrete_method_in_abc(self) -> None:
        """A concrete method in an ABC triggers INH002."""
        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                @abstractmethod
                def abstract_method(self):
                    pass

                def concrete_method(self):
                    return 42
        """
        concrete_line = 8
        concrete_col = 4
        results = _run_checker(source)

        assert len(results) == 1
        line, col, message, cls = results[0]
        assert line == concrete_line
        assert col == concrete_col
        assert "INH002" in message
        assert "MyABC" in message
        assert "concrete_method" in message
        assert cls is InheritanceChecker

    def test_pure_abc_no_errors(self) -> None:
        """An ABC with only abstract methods produces no errors."""
        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                @abstractmethod
                def do_something(self):
                    pass
        """
        assert _run_checker(source) == []

    def test_dunder_methods_allowed(self) -> None:
        """Dunder methods in an ABC do not trigger INH002."""
        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                def __init__(self):
                    self.x = 1

                @abstractmethod
                def do_something(self):
                    pass
        """
        assert _run_checker(source) == []


class TestCheckerPluginType:
    """The 4th element of each yielded tuple must be the checker class."""

    def test_inh001_yields_checker_class(self) -> None:
        """INH001 tuples carry InheritanceChecker as the plugin type."""
        source = """\
            class Base:
                pass

            class Child(Base):
                pass
        """
        results = _run_checker(source)

        assert len(results) == 1
        assert results[0][3] is InheritanceChecker

    def test_inh002_yields_checker_class(self) -> None:
        """INH002 tuples carry InheritanceChecker as the plugin type."""
        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                @abstractmethod
                def abstract_method(self):
                    pass

                def concrete_method(self):
                    return 42
        """
        results = _run_checker(source)

        assert len(results) == 1
        assert results[0][3] is InheritanceChecker


class TestCheckerCombined:
    """InheritanceChecker.run() handles both INH001 and INH002 together."""

    def test_both_errors_in_one_file(self) -> None:
        """A file with both INH001 and INH002 violations yields both errors."""
        source = """\
            from abc import ABC, abstractmethod

            class Base:
                pass

            class Child(Base):
                pass

            class MyABC(ABC):
                @abstractmethod
                def abstract_method(self):
                    pass

                def concrete_method(self):
                    return 42
        """
        expected_count = 2
        results = _run_checker(source)

        assert len(results) == expected_count
        codes = [r[2] for r in results]
        assert any("INH001" in c for c in codes)
        assert any("INH002" in c for c in codes)

    def test_empty_module(self) -> None:
        """An empty module produces no errors."""
        assert _run_checker("") == []

    def test_result_tuple_format(self) -> None:
        """Each result is a 4-tuple of (int, int, str, type)."""
        source = """\
            class Base:
                pass

            class Child(Base):
                pass
        """
        results = _run_checker(source)

        assert len(results) == 1
        line, col, message, cls = results[0]
        assert isinstance(line, int)
        assert isinstance(col, int)
        assert isinstance(message, str)
        assert isinstance(cls, type)
