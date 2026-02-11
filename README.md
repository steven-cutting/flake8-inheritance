# flake8-inheritance

![Static Badge](https://img.shields.io/badge/ai-built-thing?style=plastic&logo=probot&logoColor=%2300B0D8)

A Flake8 plugin that nudges you toward composition over inheritance.
It detects when classes inherit from concrete internal classes — cases where
composition would reduce coupling — and flags concrete methods in abstract
base classes that should remain pure interfaces.

> **Status:** Under development. Not yet published to PyPI.

## Installation

```bash
pip install flake8-inheritance
```

## Quickstart

1. **Install** the plugin (it registers itself with Flake8 automatically):

   ```bash
   pip install flake8-inheritance
   ```

2. **Configure** `--project-packages` so the plugin knows which imports
   are part of your project. Add it to `.flake8` or `setup.cfg`:

   ```ini
   # .flake8 or setup.cfg
   [flake8]
   project-packages = myproject
   ```

   Without this option, same-file inheritance and relative imports
   (e.g. `from .models import Base`) are still flagged. However,
   absolute imports from your own packages are treated as external
   and silently allowed.

3. **Run** Flake8:

   ```bash
   flake8 src/
   ```

## Verify the plugin is loaded

```bash
flake8 --version
```

The output should include a line like:

```text
flake8-inheritance: X.Y.Z
```

## Error codes

| Code   | Description                                                         |
|--------|---------------------------------------------------------------------|
| INH001 | Inheritance from an internal concrete class (use composition)       |
| INH002 | Concrete method in an abstract base class (ABCs should be pure)     |

### INH001 — inheritance from internal class

Triggered when a class inherits from a concrete (non-abstract) class
that lives in the same file or in one of the configured
`--project-packages`.

```python
class Engine:
    def start(self) -> None: ...

# INH001: Inheritance from internal class 'Engine' is not allowed
class TurboEngine(Engine):
    def start(self) -> None: ...
```

**Fix:** replace inheritance with composition:

```python
class TurboEngine:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def start(self) -> None:
        self._engine.start()
```

### INH002 — concrete method in an ABC

Triggered when a class that derives from `abc.ABC` (or uses
`abc.ABCMeta`) defines a non-abstract method.

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self) -> str: ...

    # INH002: ABC 'Animal' contains concrete method 'legs'
    def legs(self) -> int:
        return 4
```

**Fix:** make the method abstract, or move the default implementation
into a concrete class.

## Configuration

### `--project-packages`

Comma-separated list of top-level package names that belong to your
project. The plugin uses this to distinguish your code from third-party
libraries.

```ini
[flake8]
project-packages = myproject,myproject_utils
```

### `--inh002-allowed-dunders`

Comma-separated list of dunder method names that are permitted as
concrete methods in ABCs (e.g., `__init__`, `__repr__`).

```ini
[flake8]
inh002-allowed-dunders = __init__,__repr__
```

## License

BSD-3-Clause
