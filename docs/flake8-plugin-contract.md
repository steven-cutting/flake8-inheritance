# Flake8 Plugin Contract

How flake8 discovers, loads, and invokes `flake8-inheritance`.

## Discovery

Flake8 finds plugins through Python entry points. The relevant
configuration in `pyproject.toml`:

```toml
[project.entry-points."flake8.extension"]
INH = "flake8_inheritance.checker:InheritanceChecker"
```

The entry-point **key** (`INH`) determines which error codes the plugin
owns. Flake8 routes codes starting with `INH` to this checker.

## Plugin Class Requirements

An AST checker plugin must expose:

### Class Attributes

| Attribute | Type | Purpose |
|---|---|---|
| `name` | `str` | Human-readable plugin name shown in `flake8 --version` |
| `version` | `str` | Plugin version shown in `flake8 --version` |

### Constructor

```python
def __init__(self, tree: ast.AST) -> None:
```

Flake8 calls the constructor once per file, passing the parsed AST. The
checker stores the tree for later traversal in `run()`.

### run()

```python
def run(self) -> Generator[tuple[int, int, str, type], None, None]:
```

Called once per file after construction. Must yield zero or more tuples:

| Index | Type | Description |
|---|---|---|
| 0 | `int` | Line number (1-based) |
| 1 | `int` | Column offset (0-based) |
| 2 | `str` | Message including the error code, e.g. `"INH001 ..."` |
| 3 | `type` | The checker class itself (`InheritanceChecker`) |

### Optional: Options

Plugins may participate in flake8's option system:

```python
@classmethod
def add_options(cls, parser: OptionManager) -> None:
    """Register plugin-specific CLI/config options."""

@classmethod
def parse_options(cls, options: Namespace) -> None:
    """Receive parsed option values. Store on the class for run() to use."""
```

These are **class methods** called once at startup, before any file is
processed. `parse_options` is called after `add_options` and receives the
resolved `argparse.Namespace`.

## Lifecycle Summary

```text
flake8 startup
  ├── discover entry points
  ├── call add_options(parser)      [if defined]
  ├── parse CLI + config
  └── call parse_options(options)   [if defined]

for each file:
  ├── parse file -> ast.Module
  ├── checker = InheritanceChecker(tree)
  └── for (line, col, msg, cls) in checker.run():
        report diagnostic
```

## References

- [Flake8 docs: writing plugins](https://flake8.pycqa.org/en/latest/plugin-development/)
- [ADR-0008](../doc/adr/0008-use-flake8-ast-checker-plugin-architecture.md)
