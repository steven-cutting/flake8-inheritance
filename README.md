# flake8-inheritance

A Flake8 plugin that enforces composition over inheritance in Python codebases.

> **Status:** Under development. Not yet published to PyPI.

## What it does

`flake8-inheritance` distinguishes between *necessary* inheritance (from external
frameworks like Pydantic or SQLAlchemy) and *discretionary* inheritance (from internal
project classes where composition would be more appropriate). It flags the latter.

## Error codes

| Code   | Description                     |
|--------|---------------------------------|
| INH001 | Inheritance from internal class |
| INH002 | Concrete method in ABC          |

### INH001 — Inheritance from internal class

**Triggers** when a class inherits from another class defined in the same file,
imported via a relative import, or imported from a package matching the
configured `--project-package` option.

Before (triggers INH001):

```python
class Engine:
    def start(self):
        return "running"


class Car(Engine):  # INH001: Inheritance from internal class 'Engine'
    def drive(self):
        return self.start()
```

After (fixed with composition):

```python
class Engine:
    def start(self):
        return "running"


class Car:
    def __init__(self):
        self._engine = Engine()

    def drive(self):
        return self._engine.start()
```

### INH002 — Concrete method in ABC

**Triggers** when an abstract base class (inheriting from `abc.ABC` or using
`metaclass=abc.ABCMeta`) contains a method without `@abstractmethod`. Dunder
methods are exempt by default.

Before (triggers INH002):

```python
from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def get(self, id):
        ...

    def get_or_none(self, id):  # INH002: concrete method 'get_or_none'
        try:
            return self.get(id)
        except KeyError:
            return None
```

After (fixed by making all methods abstract):

```python
from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def get(self, id):
        ...

    @abstractmethod
    def get_or_none(self, id):
        ...
```

Or extract the concrete helper into a utility function:

```python
from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def get(self, id):
        ...


def get_or_none(repo: Repository, id):
    try:
        return repo.get(id)
    except KeyError:
        return None
```

## Installation

Not yet available. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.
