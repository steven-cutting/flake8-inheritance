import ast

from flake8_inheritance import codes, visitors
from flake8_inheritance.checker import InheritanceChecker


def test_plugin_importable() -> None:
    assert hasattr(InheritanceChecker, "name")


def test_plugin_is_off_by_default() -> None:
    assert InheritanceChecker.off_by_default is True


def test_plugin_produces_no_errors_on_empty_module() -> None:
    tree = ast.parse("")
    checker = InheritanceChecker(tree)
    assert list(checker.run()) == []


def test_submodules_importable() -> None:
    assert codes is not None
    assert visitors is not None
