import ast

from flake8_inheritance import codes, visitors
from flake8_inheritance.checker import InheritanceChecker


def test_plugin_importable() -> None:
    assert hasattr(InheritanceChecker, "name")


def test_plugin_produces_no_errors_on_empty_module() -> None:
    tree = ast.parse("")
    checker = InheritanceChecker(tree)
    assert list(checker.run()) == []


def test_run_tuples_use_checker_type() -> None:
    """The 4th element in flake8 tuples must be the checker class, not an error class."""
    tree = ast.parse("class Foo(Bar): pass")
    checker = InheritanceChecker(tree)
    for line, col, message, cls in checker.run():
        assert cls is InheritanceChecker, (
            f"Expected InheritanceChecker as 4th tuple element, got {cls}"
        )


def test_submodules_importable() -> None:
    assert codes is not None
    assert visitors is not None
