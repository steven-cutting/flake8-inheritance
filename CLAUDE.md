# CLAUDE.md — AI Agent Instructions for flake8-inheritance

## Project Overview

flake8-inheritance is a Flake8 plugin enforcing composition over inheritance in Python
codebases.

## Development Commands

- Install: `uv sync --all-extras --dev`
- Test: `uv run pytest`
- Test with coverage: `uv run pytest --cov=flake8_inheritance --cov-report=term-missing`
- Lint: `uv run pre-commit run --all-files`
- Type check: `uv run mypy src tests`
- Format: `uv run ruff format src tests`

## CRITICAL RULES

1. ALWAYS use `uv run` prefix for pytest, pre-commit, ruff, mypy
2. After EVERY code change, run: `uv run pre-commit run --all-files`
   then `uv run pytest`
3. Use test-first TDD: write the failing test BEFORE the implementation
4. All code must pass `ruff check`, `ruff format --check`, and
   `mypy --strict`

## Architecture

- `src/flake8_inheritance/checker.py` — Flake8 plugin class
- `src/flake8_inheritance/visitors.py` — AST visitors (no flake8 dependency)
- `src/flake8_inheritance/codes.py` — Error code definitions (no flake8 dependency)
- `tests/` — pytest test suite
- `tests/fixtures/` — Sample Python files for testing

## Design Principles

- Composition over inheritance (we eat our own dogfood)
- Core logic decoupled from flake8 (visitors.py and codes.py importable without flake8)
- Zero runtime dependencies beyond flake8
- Single-pass AST walk with O(1) lookups

## ADRs

Check `doc/adr/` for architectural decision records.
Create new ADRs with: `decree new "Title of decision"`

## Documentation

Check `doc/` for project documentation. Read `doc/README.md` first.
