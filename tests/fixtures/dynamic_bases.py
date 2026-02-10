"""Fixture: dynamic base classes (function calls as bases)."""


def get_base():
    return type("DynBase", (), {})


class DynamicChild(get_base()):
    """Dynamic base — should be silently skipped."""

    pass
