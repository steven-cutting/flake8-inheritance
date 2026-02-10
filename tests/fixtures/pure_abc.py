"""Fixture: ABC with only abstract methods (no INH002 expected)."""

from abc import ABC, abstractmethod


class PureInterface(ABC):
    @abstractmethod
    def process(self):
        pass

    @abstractmethod
    def validate(self):
        pass
