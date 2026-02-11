"""Integration tests using pytest-flake8-path to exercise the full flake8 pipeline."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_flake8_path import Flake8Path

# Every test uses ``--select=INH`` (via setup.cfg or extra_args) so that only
# this plugin's codes are active.  This isolates the assertions from unrelated
# pycodestyle / pyflakes diagnostics and lets us rely on ``exit_code == 0`` to
# confirm a genuinely clean run.

_FLAKE8_SELECT_INH = """\
[flake8]
select = INH
enable-extensions = INH
"""


def test_plugin_not_enabled_by_default(flake8_path: Flake8Path) -> None:
    """Without enable-extensions, INH rules stay inactive."""
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            class Base:
                pass

            class Child(Base):
                pass
        """)
    )

    result = flake8_path.run_flake8(extra_args=["--select=INH"])

    assert result.exit_code == 0
    assert result.out_lines == []


def test_inh001_with_config(flake8_path: Flake8Path) -> None:
    """Configured project package triggers INH001."""
    (flake8_path / "setup.cfg").write_text(
        textwrap.dedent("""\
            [flake8]
            select = INH
            enable-extensions = INH
            project-packages = myproject
        """)
    )
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            from myproject.models import Base

            class Child(Base):
                pass
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code != 0
    assert any("INH001" in line for line in result.out_lines)
    assert any("Base" in line for line in result.out_lines)


def test_no_false_positive_on_external(flake8_path: Flake8Path) -> None:
    """Pydantic BaseModel is not flagged (external dependency)."""
    (flake8_path / "setup.cfg").write_text(_FLAKE8_SELECT_INH)
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            from pydantic import BaseModel

            class User(BaseModel):
                name: str
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code == 0
    assert result.out_lines == []


def test_inh002_concrete_method(flake8_path: Flake8Path) -> None:
    """Concrete method in ABC triggers INH002."""
    (flake8_path / "setup.cfg").write_text(_FLAKE8_SELECT_INH)
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            from abc import ABC, abstractmethod

            class MyABC(ABC):
                @abstractmethod
                def required(self):
                    pass

                def helper(self):
                    return 42
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code != 0
    assert any("INH002" in line for line in result.out_lines)
    assert any("MyABC" in line for line in result.out_lines)
    assert any("helper" in line for line in result.out_lines)


def test_noqa_suppression(flake8_path: Flake8Path) -> None:
    """``# noqa: INH001`` suppresses the violation."""
    (flake8_path / "setup.cfg").write_text(_FLAKE8_SELECT_INH)
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            class Base:
                pass

            class Child(Base):  # noqa: INH001
                pass
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code == 0
    assert result.out_lines == []


def test_zero_config_same_file(flake8_path: Flake8Path) -> None:
    """Same-file inheritance is flagged without any configuration."""
    (flake8_path / "setup.cfg").write_text(_FLAKE8_SELECT_INH)
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            class Base:
                pass

            class Child(Base):
                pass
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code != 0
    assert any("INH001" in line for line in result.out_lines)
    assert any("Base" in line for line in result.out_lines)


def test_zero_config_absolute_import(flake8_path: Flake8Path) -> None:
    """Absolute import with no ``--project-packages`` produces no INH error."""
    (flake8_path / "setup.cfg").write_text(_FLAKE8_SELECT_INH)
    (flake8_path / "example.py").write_text(
        textwrap.dedent("""\
            from myproject.models import Base

            class Child(Base):
                pass
        """)
    )
    result = flake8_path.run_flake8()
    assert result.exit_code == 0
    assert result.out_lines == []
