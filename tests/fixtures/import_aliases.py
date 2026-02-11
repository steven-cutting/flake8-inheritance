"""Fixture: aliased imports."""

from abc import ABC as AbstractBase
from abc import abstractmethod as am


class AliasedABC(AbstractBase):
    @am
    def do_thing(self):
        pass

    def concrete_helper(self):
        """INH002: concrete method in aliased ABC."""
        return 42
