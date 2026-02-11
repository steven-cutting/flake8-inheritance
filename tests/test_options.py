"""Tests for InheritanceChecker.add_options and parse_options."""

from __future__ import annotations

import argparse
import ast
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest

from flake8_inheritance.checker import InheritanceChecker


class _OptionCall:
    def __init__(self, *args: str, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs


class _ParserSpy:
    def __init__(self) -> None:
        self.calls: list[_OptionCall] = []

    def add_option(self, *args: str, **kwargs: object) -> None:
        self.calls.append(_OptionCall(*args, **kwargs))


class TestAddOptions:
    """add_options registers CLI options with flake8's option_manager."""

    def test_registers_project_packages(self) -> None:
        """--project-packages is registered as a comma-separated option."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        long_names = [call.args[0] for call in calls]
        assert "--project-packages" in long_names

    def test_registers_inh002_allowed_dunders(self) -> None:
        """--inh002-allowed-dunders is registered as a comma-separated option."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        long_names = [call.args[0] for call in calls]
        assert "--inh002-allowed-dunders" in long_names

    def test_project_packages_parse_from_config(self) -> None:
        """--project-packages has parse_from_config=True."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        for call in calls:
            if call.args[0] == "--project-packages":
                assert call.kwargs["parse_from_config"] is True
                break
        else:
            pytest.fail("--project-packages was not registered")

    def test_inh002_allowed_dunders_parse_from_config(self) -> None:
        """--inh002-allowed-dunders has parse_from_config=True."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        for call in calls:
            if call.args[0] == "--inh002-allowed-dunders":
                assert call.kwargs["parse_from_config"] is True
                break
        else:
            pytest.fail("--inh002-allowed-dunders was not registered")

    def test_project_packages_default_empty(self) -> None:
        """--project-packages defaults to empty string."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        for call in calls:
            if call.args[0] == "--project-packages":
                assert call.kwargs["default"] == ""
                break
        else:
            pytest.fail("--project-packages was not registered")

    def test_inh002_allowed_dunders_default_none(self) -> None:
        """--inh002-allowed-dunders defaults to None (all dunders allowed)."""
        parser = _ParserSpy()
        InheritanceChecker.add_options(parser)

        calls = parser.calls
        for call in calls:
            if call.args[0] == "--inh002-allowed-dunders":
                assert call.kwargs["default"] is None
                break
        else:
            pytest.fail("--inh002-allowed-dunders was not registered")


class TestParseOptions:
    """parse_options stores parsed values as class attributes."""

    def test_empty_project_packages(self) -> None:
        """Empty string results in an empty tuple."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders="__init__")
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ()

    def test_single_project_package(self) -> None:
        """A single value is parsed into a one-element tuple."""
        options = argparse.Namespace(
            project_packages="myproject", inh002_allowed_dunders="__init__"
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ("myproject",)

    def test_multiple_project_packages(self) -> None:
        """Comma-separated values are split into a tuple."""
        options = argparse.Namespace(
            project_packages="myproject,otherlib,utils",
            inh002_allowed_dunders="__init__",
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ("myproject", "otherlib", "utils")

    def test_project_packages_strips_whitespace(self) -> None:
        """Whitespace around values is stripped."""
        options = argparse.Namespace(
            project_packages="  myproject , otherlib  ",
            inh002_allowed_dunders="__init__",
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ("myproject", "otherlib")

    def test_empty_allowed_dunders(self) -> None:
        """Empty string results in an empty tuple."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders="")
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == ()

    def test_single_allowed_dunder(self) -> None:
        """A single dunder is parsed into a one-element tuple."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders="__init__")
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == ("__init__",)

    def test_multiple_allowed_dunders(self) -> None:
        """Comma-separated dunders are split into a tuple."""
        options = argparse.Namespace(
            project_packages="",
            inh002_allowed_dunders="__init__,__new__,__post_init__",
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == (
            "__init__",
            "__new__",
            "__post_init__",
        )

    def test_allowed_dunders_strips_whitespace(self) -> None:
        """Whitespace around values is stripped."""
        options = argparse.Namespace(
            project_packages="",
            inh002_allowed_dunders="  __init__ , __new__  ",
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == ("__init__", "__new__")

    def test_project_packages_as_list(self) -> None:
        """Flake8 may pass project_packages as a pre-split list."""
        options = argparse.Namespace(
            project_packages=["myproject", "otherlib"],
            inh002_allowed_dunders=None,
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ("myproject", "otherlib")

    def test_project_packages_as_list_strips_whitespace(self) -> None:
        """List items with whitespace are stripped; empty items are dropped."""
        options = argparse.Namespace(
            project_packages=["  myproject  ", "", "  otherlib"],
            inh002_allowed_dunders=None,
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._project_packages == ("myproject", "otherlib")

    def test_allowed_dunders_as_list(self) -> None:
        """Flake8 may pass inh002_allowed_dunders as a pre-split list."""
        options = argparse.Namespace(
            project_packages="",
            inh002_allowed_dunders=["__init__", "__repr__"],
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == ("__init__", "__repr__")

    def test_allowed_dunders_as_list_strips_whitespace(self) -> None:
        """List items with whitespace are stripped; empty items are dropped."""
        options = argparse.Namespace(
            project_packages="",
            inh002_allowed_dunders=["  __init__  ", "", "  __new__"],
        )
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders == ("__init__", "__new__")


class TestOptionsIntegration:
    """Options affect checker behavior through run()."""

    @pytest.fixture(autouse=True)
    def _reset_class_attrs(self) -> Iterator[None]:
        """Reset class-level option attributes after each test."""
        yield
        # Reset to defaults
        InheritanceChecker._project_packages = ()
        InheritanceChecker._inh002_allowed_dunders = None

    def test_project_packages_flags_absolute_import(self) -> None:
        """With --project-packages set, absolute imports from that package trigger INH001."""
        options = argparse.Namespace(
            project_packages="myproject", inh002_allowed_dunders="__init__"
        )
        InheritanceChecker.parse_options(options)

        source = """\
            from myproject.models import Base

            class Child(Base):
                pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        assert len(results) == 1
        assert "INH001" in results[0][2]
        assert "Base" in results[0][2]

    def test_no_project_packages_allows_absolute_import(self) -> None:
        """Without --project-packages, absolute imports are not flagged."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders="__init__")
        InheritanceChecker.parse_options(options)

        source = """\
            from myproject.models import Base

            class Child(Base):
                pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        assert results == []

    def test_allowed_dunders_all_allowed_by_default(self) -> None:
        """Without config, dunder methods in ABCs are all allowed."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders=None)
        InheritanceChecker.parse_options(options)

        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                def __init__(self):
                    self.x = 1

                def __repr__(self):
                    return "MyABC"

                @abstractmethod
                def do_something(self):
                    pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        assert results == []

    def test_allowed_dunders_empty_flags_all_dunders(self) -> None:
        """With empty allowed-dunders, concrete dunders in ABCs trigger INH002."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders="")
        InheritanceChecker.parse_options(options)

        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                def __init__(self):
                    self.x = 1

                @abstractmethod
                def do_something(self):
                    pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        assert len(results) == 1
        assert "INH002" in results[0][2]
        assert "__init__" in results[0][2]

    def test_allowed_dunders_custom_list(self) -> None:
        """Custom allowed-dunders list controls which dunders are exempt."""
        options = argparse.Namespace(
            project_packages="",
            inh002_allowed_dunders="__init__,__repr__",
        )
        InheritanceChecker.parse_options(options)

        source = """\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                def __init__(self):
                    self.x = 1

                def __repr__(self):
                    return "MyABC"

                def __str__(self):
                    return "abc"

                @abstractmethod
                def do_something(self):
                    pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        # __init__ and __repr__ allowed, __str__ flagged
        assert len(results) == 1
        assert "__str__" in results[0][2]

    def test_missing_allowed_dunders_uses_none(self) -> None:
        """None keeps default behavior (all dunders allowed)."""
        options = argparse.Namespace(project_packages="", inh002_allowed_dunders=None)
        InheritanceChecker.parse_options(options)

        assert InheritanceChecker._inh002_allowed_dunders is None

    def test_multiple_project_packages_deduplicate_errors(self) -> None:
        """Multiple --project-packages merge errors without duplicates."""
        options = argparse.Namespace(
            project_packages=["myproject", "otherlib"],
            inh002_allowed_dunders=None,
        )
        InheritanceChecker.parse_options(options)

        source = """\
            from myproject.models import Base
            from otherlib.core import Mixin

            class Child(Base, Mixin):
                pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        # Both bases should be flagged, no duplicates
        messages = [r[2] for r in results]
        assert len(results) == 2  # noqa: PLR2004
        assert any("Base" in m for m in messages)
        assert any("Mixin" in m for m in messages)

    def test_multiple_project_packages_shared_error_not_duplicated(self) -> None:
        """When the same base is flagged by multiple trackers, it appears once."""
        options = argparse.Namespace(
            project_packages=["myproject", "myproject"],
            inh002_allowed_dunders=None,
        )
        InheritanceChecker.parse_options(options)

        source = """\
            from myproject.models import Base

            class Child(Base):
                pass
        """
        tree = ast.parse(textwrap.dedent(source))
        results = list(InheritanceChecker(tree).run())

        assert len(results) == 1
        assert "Base" in results[0][2]
