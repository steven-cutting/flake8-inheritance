"""Fixture: imports and functions only — no class definitions."""

import os
from collections import OrderedDict

CONSTANT = 42


def helper(x):
    return x + 1


def get_path():
    return os.getcwd()


def make_dict():
    return OrderedDict()
