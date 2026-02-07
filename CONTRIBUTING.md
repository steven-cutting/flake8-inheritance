# Contributing to flake8-inheritance

## Development setup

```bash
git clone https://github.com/steven-cutting/flake8-inheritance.git
cd flake8-inheritance
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
nox -s tests
```

## Running linters

```bash
nox -s lint
nox -s typecheck
```

## Architecture decisions

We record significant decisions using [decree](https://github.com/steven-cutting/decree):

```bash
decree list          # see existing ADRs
decree new "Title"   # propose a new decision
```

ADRs live in `doc/adr/` and follow the Nygard format (Context, Decision, Consequences).
