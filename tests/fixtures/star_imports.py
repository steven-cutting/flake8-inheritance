"""Fixture: star imports."""

from myproject.models import *  # noqa: F403


class Child(Base):  # noqa: F405
    """Base is not explicitly tracked — should not trigger INH001."""

    pass
