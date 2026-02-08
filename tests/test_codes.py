"""Tests for error code definitions."""

from __future__ import annotations

import dataclasses

from flake8_inheritance.codes import INH001, INH002, ErrorCode


class TestErrorCodeImmutability:
    """ErrorCode instances must be frozen (immutable)."""

    def test_error_code_is_frozen_dataclass(self) -> None:
        assert dataclasses.is_dataclass(ErrorCode)
        assert dataclasses.fields(ErrorCode)  # has fields
        # Frozen dataclasses raise FrozenInstanceError on attribute assignment
        code = ErrorCode(code="TST001", message="test {x}")
        try:
            code.code = "TST002"  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            msg = "ErrorCode should be frozen"
            raise AssertionError(msg)


class TestINH001:
    """INH001: inheritance from internal class."""

    def test_code_value(self) -> None:
        assert INH001.code == "INH001"

    def test_format(self) -> None:
        result = INH001.format(base="Foo")
        assert result == (
            "INH001 Inheritance from internal class 'Foo' is not allowed (use composition instead)"
        )


class TestINH002:
    """INH002: ABC with concrete method."""

    def test_code_value(self) -> None:
        assert INH002.code == "INH002"

    def test_format(self) -> None:
        result = INH002.format(cls="MyABC", method="do_thing")
        assert result == (
            "INH002 Abstract base class 'MyABC' contains concrete method "
            "'do_thing' (ABCs should only define abstract methods)"
        )
