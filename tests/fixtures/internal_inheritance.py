"""Fixture: same-file and project-package inheritance (should trigger INH001)."""

from myproject.models import Model


class Base:
    pass


class Mixin:
    pass


class ChildOfSameFile(Base):
    """INH001: inherits from same-file class."""

    pass


class MultipleInternalBases(Base, Mixin):
    """INH001 x2: inherits from two same-file classes."""

    pass


class ChildOfProjectPackage(Model):
    """INH001: inherits from project-package class (when myproject is configured)."""

    pass
