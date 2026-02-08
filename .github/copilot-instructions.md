# Copilot Instructions for flake8-inheritance

## Project Overview

flake8-inheritance is a Flake8 plugin that enforces composition over
inheritance in Python codebases. It distinguishes between necessary
inheritance (from external frameworks like Pydantic, SQLAlchemy) and
discretionary inheritance (from internal project classes), flagging the
latter.

### Architecture

- `src/flake8_inheritance/checker.py` — Flake8 plugin class
  (`InheritanceChecker`). This is the only module that imports from flake8.
- `src/flake8_inheritance/visitors.py` — AST visitors and import tracking
  logic. Must not import from flake8.
- `src/flake8_inheritance/codes.py` — Error code definitions. Must not
  import from flake8.
- `tests/` — pytest test suite.
- `tests/fixtures/` — Sample `.py` files used as test inputs.
- `doc/adr/` — Architectural decision records.

### Key constraint

Core logic in `visitors.py` and `codes.py` must be importable without
flake8 installed. Only `checker.py` may depend on flake8.

## Error Codes

All error codes use the `INH` prefix (three letters, to reduce collision
risk with other flake8 plugins):

| Code   | Meaning                                        |
|--------|------------------------------------------------|
| INH001 | Inheritance from an internal class is not allowed |
| INH002 | Abstract base class contains a concrete method    |

## Testing Conventions

- **TDD**: Write a failing test before the implementation.
- **Framework**: pytest (always invoked via `uv run pytest`).
- **Unit tests for visitors**: Use `ast.parse()` to build AST trees, then
  assert on visitor results.
- **Integration tests**: Use `pytest-flake8-path` to run flake8 end-to-end.
- **Fixtures**: Place sample Python source files in `tests/fixtures/`.
- **Coverage**: Line and branch coverage must stay at or above 90 %.

## Style and Conventions

- In production code under `src/flake8_inheritance/`, always include
  `from __future__ import annotations` at the top of each module. Tests are
  exempt from this requirement.
- Use type hints everywhere. The project runs `mypy --strict`.
- Use frozen dataclasses for value objects (immutable, hashable by
  default).
- Prefer composition over inheritance in the plugin's own code (we eat our
  own dogfood).
- Follow the existing ruff configuration: line length 100,
  target Python 3.11, `select = ["ALL"]`.

## Tool Invocations

Always use `uv run` to invoke project tools:

```bash
uv run pytest                          # run tests
uv run pytest --cov=flake8_inheritance # run tests with coverage
uv run pre-commit run --all-files      # lint and format
uv run mypy src tests                  # type-check
uv run ruff format src tests           # auto-format
uv run ruff check src tests            # lint
```

Never call `pytest`, `pre-commit`, `ruff`, or `mypy` without the
`uv run` prefix.

## Design Principles

- Zero runtime dependencies beyond flake8.
- Single-pass AST walk with O(1) lookups for import classification.
- Keep the plugin small and focused — avoid feature creep.
