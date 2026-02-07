# flake8-inheritance

A Flake8 plugin that enforces composition over inheritance in Python codebases.

> **Status:** Under development. Not yet published to PyPI.

## What it does

`flake8-inheritance` distinguishes between *necessary* inheritance (from external
frameworks like Pydantic or SQLAlchemy) and *discretionary* inheritance (from internal
project classes where composition would be more appropriate). It flags the latter.

## Installation

Not yet available. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.
