"""Tests for error code definitions."""
from __future__ import annotations

import dataclasses

import pytest

from flake8_inheritance.codes import INH001, INH002, ErrorCode


class TestErrorCodeDataclass:
    """ErrorCode is a frozen dataclass."""

    def test_inh001_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            INH001.code = "X"  # type: ignore[misc]

    def test_inh002_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            INH002.code = "X"  # type: ignore[misc]


class TestINH001Format:
    """INH001.format() produces the expected diagnostic string."""

    def test_basic(self) -> None:
        result = INH001.format(base="Foo")
        assert result == (
            "INH001 inheritance from internal class 'Foo'; "
            "use composition instead"
        )

    def test_message_length_with_long_name(self) -> None:
        result = INH001.format(base="A" * 40)
        assert len(result) < 120


class TestINH002Format:
    """INH002.format() produces the expected diagnostic string."""

    def test_basic(self) -> None:
        result = INH002.format(cls="MyABC", method="helper")
        assert result == (
            "INH002 ABC 'MyABC' has concrete method 'helper'"
        )

    def test_message_length_with_long_names(self) -> None:
        result = INH002.format(cls="A" * 40, method="B" * 40)
        assert len(result) < 120
