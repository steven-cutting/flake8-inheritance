# Contributing to flake8-inheritance

## Development setup

```bash
git clone https://github.com/steven-cutting/flake8-inheritance.git
cd flake8-inheritance
uv sync --all-extras --dev
```

## Running tests

```bash
uv run pytest
```

## Running linters

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

## Architecture decisions

We record significant decisions using [decree](https://github.com/steven-cutting/decree):

```bash
decree list          # see existing ADRs
decree new "Title"   # propose a new decision
```

ADRs live in `doc/adr/` and follow the Nygard format (Context, Decision, Consequences).

## Releasing

For instructions on creating and publishing a new release, see [RELEASING.md](./RELEASING.md).
