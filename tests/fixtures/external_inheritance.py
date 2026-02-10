"""Fixture: inheritance from external / stdlib bases (no INH001 expected)."""

from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class MyDict(OrderedDict):
    """Stdlib base — allowed."""

    pass


class MyGeneric(Generic[T]):
    """Stdlib generic — allowed."""

    pass
