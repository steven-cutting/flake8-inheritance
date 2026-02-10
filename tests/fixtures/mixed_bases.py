"""Fixture: class with both internal and external bases."""

from collections import OrderedDict

from .models import InternalBase


class MixedChild(InternalBase, OrderedDict):
    """INH001 for InternalBase only; OrderedDict is stdlib."""

    pass
