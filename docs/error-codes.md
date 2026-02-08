# Error Codes

Reference for all diagnostics produced by flake8-inheritance.

## INH001 -- Class inherits from a concrete class

**Status:** Planned

**What it detects:** A class definition that inherits from a concrete
(non-abstract, non-exempt) base class defined within the same project.

**Rationale:** Inheriting from concrete classes creates tight coupling.
Composition (holding a reference and delegating) is usually more flexible
and easier to test.

### Triggers

```python
class Engine:
    def start(self) -> None: ...

class TurboEngine(Engine):  # <-- INH001
    def start(self) -> None: ...
```

### Fix

```python
class Engine:
    def start(self) -> None: ...

class TurboEngine:
    def __init__(self, base: Engine) -> None:
        self._base = base

    def start(self) -> None:
        self._base.start()
```

### Exemptions

Classes inheriting from the following are **not** flagged:

- Abstract base classes (`ABC`, `ABCMeta`)
- Exception classes (`Exception`, `BaseException`, and subclasses)
- Framework bases specified via configuration (e.g. Pydantic, Django,
  SQLAlchemy model bases)
- Bases imported from external (non-project) packages

---

## INH002 -- Abstract class should use ABC

**Status:** Planned

**What it detects:** A class that defines `@abstractmethod`-decorated
methods but does not inherit from `abc.ABC` or use `abc.ABCMeta` as its
metaclass.

**Rationale:** Without `ABC`/`ABCMeta`, Python will not prevent
instantiation of the incomplete class, silently defeating the purpose of
abstract methods.

### Triggers

```python
from abc import abstractmethod

class Animal:  # <-- INH002: has abstract methods but doesn't use ABC
    @abstractmethod
    def speak(self) -> str: ...
```

### Fix

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self) -> str: ...
```

---

## Code Range Allocation

| Range | Category | Status |
|---|---|---|
| INH0xx | Inheritance restriction rules | Active |
| INH1xx | ABC purity checks | Active |
| INH2xx | Reserved | -- |
