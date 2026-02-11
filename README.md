# flake8-inheritance

![AI-Built](https://img.shields.io/badge/ai-built-brightgreen?logo=probot&logoColor=%2300B0D8)

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

This section documents every plugin option and the most common Flake8-native
settings used to adopt `flake8-inheritance` in real projects.

### Defaults at a glance

| Option | Default | Meaning |
|---|---|---|
| `--project-packages` | empty | Absolute imports are external unless package is configured |
| `--inh002-allowed-dunders` | `__init__` | Only `__init__` may be concrete in an ABC |

### `--project-packages`

Comma-separated list of top-level package names that belong to your
project. The plugin uses this to distinguish your code from third-party
libraries.

```ini
[flake8]
project-packages = myproject,myproject_utils
```

**Default:** empty (unset)

When left unset, the plugin still flags:

- inheritance from classes defined in the same file
- inheritance via relative imports (for example, `from .base import Base`)

But it treats absolute imports as external unless their top-level package is
listed here.

### `--inh002-allowed-dunders`

Comma-separated list of dunder method names that are permitted as
concrete methods in ABCs (e.g., `__init__`, `__repr__`).

```ini
[flake8]
inh002-allowed-dunders = __init__,__repr__
```

**Default:** `__init__`

## Full configuration reference by file format

You can configure these options in whichever Flake8 config style your project
uses.

### `.flake8`

```ini
[flake8]
project-packages = myproject,myproject_utils
inh002-allowed-dunders = __init__,__repr__

# Flake8-native filtering controls
select = INH
extend-ignore = E203
per-file-ignores =
    tests/*:INH001
```

### `setup.cfg`

```ini
[flake8]
project-packages = myproject,myproject_utils
inh002-allowed-dunders = __init__,__repr__

# Flake8-native filtering controls
select = INH,B,C,E,F,W
extend-ignore = E203,W503
per-file-ignores =
    tests/*:INH001
    src/myproject/legacy/*.py:INH001,INH002
```

### `pyproject.toml` (with `flake8-pyproject`)

Flake8 does not read `pyproject.toml` natively. Use
[`flake8-pyproject`](https://pypi.org/project/flake8-pyproject/) to enable
this format.

```toml
[tool.flake8]
project-packages = ["myproject", "myproject_utils"]
inh002-allowed-dunders = ["__init__", "__repr__"]

# Flake8-native filtering controls
select = ["INH", "E", "F", "W"]
extend-ignore = ["E203", "W503"]
per-file-ignores = [
  "tests/*:INH001",
  "src/myproject/legacy/*.py:INH001,INH002",
]
```

## Flake8-native options commonly used with this plugin

These are provided by Flake8 itself (not this plugin), but they are important
for adoption:

- `--select`: run only selected code families (for example, `--select=INH` to
  focus exclusively on inheritance rules).
- `--extend-ignore`: suppress specific codes while keeping defaults.
- `--per-file-ignores`: carve out exceptions for known legacy paths.

## Gradual Adoption (report-only workflow)

For existing codebases, adopt incrementally:

1. Start in **report-only mode** by running Flake8 with `--select=INH` in CI,
   but do not fail the build yet.
2. Track and review findings; classify true positives vs intentional patterns.
3. Add temporary `per-file-ignores` for legacy modules to keep signal high.
4. Fix violations in new/changed code first.
5. Remove ignores over time and then enforce INH rules as required checks.

Example report-only CI command:

```bash
flake8 --select=INH src tests || true
```

Example enforced command once ready:

```bash
flake8 --select=INH src tests
```

## License

BSD-3-Clause
