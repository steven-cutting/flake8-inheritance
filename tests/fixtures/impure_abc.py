"""Fixture: ABC with concrete methods (should trigger INH002)."""

from abc import ABC, abstractmethod


class ImpureABC(ABC):
    @abstractmethod
    def required(self):
        pass

    def helper(self):
        """INH002: concrete method in ABC."""
        return 42

    def another_helper(self):
        """INH002: another concrete method."""
        return "hello"
