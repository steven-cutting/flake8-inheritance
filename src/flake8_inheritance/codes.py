"""Error code definitions for the flake8-inheritance plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ErrorCode:
    """A single flake8 error code with a formattable message template."""

    code: str
    message: str

    def format(self, **kwargs: str) -> str:
        """Return the full error string with the code prefix and formatted message."""
        return f"{self.code} {self.message.format(**kwargs)}"


INH001: Final[ErrorCode] = ErrorCode(
    code="INH001",
    message="Inheritance from internal class '{base}' is not allowed (use composition instead)",
)

INH002: Final[ErrorCode] = ErrorCode(
    code="INH002",
    message=(
        "Abstract base class '{cls}' contains concrete method "
        "'{method}' (ABCs should only define abstract methods)"
    ),
)
