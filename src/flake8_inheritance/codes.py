"""Error code definitions for the flake8-inheritance plugin."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    """A single error code with a formattable message template.

    Attributes:
        code: The short identifier (e.g. ``"INH001"``).
        message: A `str.format` template for the human-readable message.
    """

    code: str
    message: str

    def format(self, **kwargs: str) -> str:
        """Return the full diagnostic string with placeholders filled in.

        Args:
            **kwargs: Values to substitute into *message*.

        Returns:
            A string of the form ``"{code} {formatted_message}"``.
        """
        return f"{self.code} {self.message.format(**kwargs)}"


INH001 = ErrorCode(
    code="INH001",
    message="inheritance from internal class '{base}'; use composition instead",
)

INH002 = ErrorCode(
    code="INH002",
    message="ABC '{cls}' has concrete method '{method}'",
)
