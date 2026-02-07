# flake8-inheritance: Development Task Plan

**Empty repo → published, fully functional plugin**

Each task is scoped to be completable in a single focused session. Tasks
within a milestone are ordered by dependency — later tasks may depend on
earlier ones, but tasks at the same level within a group can sometimes be
parallelized. Every task has a concrete "done" condition.

---

## Milestone 0: Repository Bootstrap

The goal is a repo that installs, runs `flake8 --version`, and shows the
plugin — with zero rules implemented yet.

### Task 0.1 — Initialize the repo and create the `src` layout skeleton

Create the directory structure:

```text
flake8-inheritance/
├── src/
│   └── flake8_inheritance/
│       ├── __init__.py      (empty or docstring only)
│       ├── checker.py       (stub)
│       ├── visitors.py      (stub)
│       └── codes.py         (stub)
├── tests/
│   ├── __init__.py
│   └── fixtures/
├── .gitignore
└── README.md                (one-liner placeholder)
```

`checker.py` contains a minimal `InheritanceChecker` class with `name`,
`version` (hardcoded `"0.0.0"` for now), `__init__(self, tree)`, and a
`run()` that yields nothing.

**Done when:** `git init` is done, all files exist, and the directory
structure matches the `src` layout.

---

### Task 0.2 — Write `pyproject.toml` with entry point and build config

Create `pyproject.toml` with:

- `[build-system]` using `setuptools>=77` and `setuptools-scm>=8`
- `[project]` metadata: name, description, license (BSD-3-Clause),
  `requires-python = ">=3.11"`, `dependencies = ["flake8>=6.0"]`,
  `dynamic = ["version"]`
- `[project.entry-points."flake8.extension"]` →
  `INH = "flake8_inheritance.checker:InheritanceChecker"`
- `[project.optional-dependencies]` for `test` and `dev` groups
- `[tool.setuptools.packages.find]` with `where = ["src"]`
- `[tool.setuptools-scm]`
- PyPI classifiers including `Framework :: Flake8`

**Done when:** `pip install -e ".[dev]"` succeeds in a clean venv.

---

### Task 0.3 — Verify entry point registration

After editable install from Task 0.2, run `flake8 --version` and confirm
`flake8-inheritance` appears in the output.

If it doesn't: debug the entry point declaration, confirm `src` layout is
configured correctly, and re-install.

**Done when:** `flake8 --version` output includes `flake8-inheritance: 0.0.0`
(or the SCM-derived version).

---

### Task 0.4 — Wire up `setuptools-scm` for version management

Create an initial git tag (`v0.0.1` or `v0.1.0.dev0`). Update `checker.py`
to read version via `importlib.metadata.version("flake8-inheritance")`
instead of the hardcoded string. Remove any hardcoded version strings from
the source tree.

**Done when:**
`python -c "import flake8_inheritance; from importlib.metadata import version; print(version('flake8-inheritance'))"`
prints a version derived from the git tag, and
`grep -r "0\.0\.0" src/` returns nothing.

---

### Task 0.5 — Add foundational repo files

Create:

- `LICENSE` (BSD-3-Clause full text)
- `CHANGELOG.md` (Keep a Changelog format, with an `[Unreleased]` section)
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md` (placeholder noting uv-based workflow)
- `.gitignore` (Python defaults + `.nox/`, `dist/`, `*.egg-info`, `.venv/`)

**Done when:** All files exist and `git status` is clean after commit.

---

## Milestone 1: Project Tooling, CI/CD, and AI Dev Configuration

Stand up the full developer experience infrastructure early so that every
subsequent task benefits from automated linting, testing, formatting, and
AI agent guardrails. This milestone produces a CI pipeline, pre-commit
hooks, ADR scaffolding, and Claude Code / Copilot configuration.

### Task 1.1 — Set up `uv` as the project manager

Initialize the project with `uv`:

1. Run `uv init` (or adapt the existing `pyproject.toml` to work with
   `uv sync`).
2. Add `[dependency-groups]` for `dev` in `pyproject.toml` including:
   `pre-commit`, `ipython`.
3. Add `[project.optional-dependencies]` `test` group:
   `pytest>=8.2`, `pytest-cov>=5.0`, `coverage>=7.6`,
   `pytest-flake8-path`.
4. Add `dev` optional-dependencies:
   `ruff>=0.6.9`, `mypy>=1.11`, `pymarkdownlnt>=0.9.17`.
5. Run `uv sync --all-extras --dev` and commit the resulting `uv.lock`.

**Done when:** `uv run python -c "import flake8_inheritance"` succeeds and
`uv.lock` exists.

---

### Task 1.2 — Configure Ruff (lint + format)

Add `[tool.ruff]` and `[tool.ruff.lint]` config to `pyproject.toml`:

- `line-length = 100`
- `target-version = "py311"`
- `select = ["ALL"]`
- `ignore` list for formatter conflicts and docstring incompatibilities
  (mirror the decree project pattern: `COM812`, `D203`, `D213`)
- `[tool.ruff.lint.per-file-ignores]` to relax docstring rules in `tests/`

Run `ruff check --fix` and `ruff format` on existing stubs.

**Done when:** `uv run ruff check src tests` and
`uv run ruff format --check src tests` both exit 0.

---

### Task 1.3 — Configure Mypy

Add `[tool.mypy]` config to `pyproject.toml`:

- `strict = true`, `warn_unused_configs = true`, `python_version = "3.11"`
- `show_error_codes = true`
- Override for `flake8.*`: `ignore_missing_imports = true`

Fix any type errors in the existing stubs.

**Done when:** `uv run mypy src` passes with zero errors.

---

### Task 1.4 — Set up `.pre-commit-config.yaml`

Create `.pre-commit-config.yaml` modeled on the decree project:

- `ruff-pre-commit` (ruff-check with `--fix`, ruff-format)
- `local` hook for mypy: `uv run dmypy run -- src tests`
- `pre-commit-hooks`: check-ast, check-toml, check-yaml, check-json,
  trailing-whitespace, end-of-file-fixer, check-added-large-files,
  debug-statements, mixed-line-ending, detect-private-key,
  check-merge-conflict, check-case-conflict, check-builtin-literals
- `shellcheck-py`
- `codespell` (with tomli)
- `detect-secrets`
- `typos`
- `pymarkdown` (with `.pymarkdown.json` config)
- `yamllint`

Create `.pymarkdown.json` (copy from decree project pattern).

**Done when:** `uv run pre-commit run --all-files` passes.

---

### Task 1.5 — Configure pytest and coverage

Add to `pyproject.toml`:

- `[tool.pytest.ini_options]`: `addopts = "-q --disable-warnings"`,
  `testpaths = ["tests"]`
- `[tool.coverage.run]`: `branch = true`,
  `source = ["flake8_inheritance"]`
- `[tool.coverage.report]`: `fail_under = 90`, `show_missing = true`

Write a single smoke test in `tests/test_smoke.py`:

```python
def test_plugin_importable():
    from flake8_inheritance.checker import InheritanceChecker
    assert hasattr(InheritanceChecker, "name")
```

**Done when:** `uv run pytest --cov=flake8_inheritance --cov-report=term-missing`
passes.

---

### Task 1.6 — Create the CI workflow (`.github/workflows/ci.yml`)

Create `.github/workflows/ci.yml` modeled on the decree project's
CI but adapted for flake8-inheritance. Triggered on push to `main` and
pull requests:

**Jobs:**

1. **lint-and-typecheck**: Matrix of Python 3.11, 3.12, 3.13 on
   `ubuntu-latest`. Install uv, `uv sync --all-extras --dev`, run
   `pre-commit run --all-files`.
2. **build-test**: Matrix of Python 3.11, 3.12, 3.13 × `ubuntu-latest`,
   plus Python 3.13 on `macos-latest` and `windows-latest`. Install uv,
   sync, run `uv run pytest --cov=flake8_inheritance --cov-report=term-missing`.

Use `astral-sh/setup-uv` action for uv installation. Pin actions with
commit SHAs or version tags.

**Done when:** Pushing to a branch triggers the workflow, and all jobs pass.

---

### Task 1.7 — Create the publish workflow (`.github/workflows/publish.yml`)

Create `.github/workflows/publish.yml` modeled on the decree project.
Triggered on GitHub release creation and `workflow_dispatch`:

**Jobs:**

1. **release-build**: Checkout, setup Python 3.13, install uv via
   `astral-sh/setup-uv`, build with `uv build`, upload artifacts.
2. **pypi-publish**: Download artifacts, publish via
   `pypa/gh-action-pypi-publish@release/v1` with `id-token: write`
   permission and `environment: pypi`.

**Done when:** Workflow file exists and passes `actionlint` or manual review.

---

### Task 1.8 — Add Dependabot configuration

Create `.github/dependabot.yml` modeled on the decree project:

- `package-ecosystem: "uv"` — weekly on Monday at 09:00 America/Los\_Angeles,
  with groups for `runtime` and `dev-tools`
- `package-ecosystem: "github-actions"` — weekly, grouped
- Labels: `dependencies`, `security`
- Commit message prefix: `deps`

**Done when:** File committed. Dependabot begins opening PRs (or is visible
in repo settings).

---

### Task 1.9 — Initialize ADRs with decree

1. Install decree: `uv tool install decree` (or add to dev dependencies).
2. Run `decree init` to create `doc/adr/` directory and the initial ADR template.
3. Create the first ADR:
   `decree new "Use composition-over-inheritance as the core design principle"`
4. Create a second ADR:
   `decree new "Use flake8 AST checker plugin architecture"`
5. Create a third ADR:
   `decree new "Use uv for project and dependency management"`

**Done when:** `decree list` shows the ADRs and `doc/adr/` contains
the numbered markdown files.

---

### Task 1.10 — Add `zizmor` security scan to CI

Add a job to `ci.yml` that runs `zizmor` against all workflow files to
detect insecure patterns (unpinned actions, missing permissions, etc.).

**Done when:** The zizmor job passes in CI with no high-severity findings.

---

### Task 1.11 — Configure Claude Code for AI-assisted development

Create `.claude/` directory with configuration for Claude Code. Inspired
by the "AI Zealotry" patterns (hooks, docs checking, structured feedback).

**`.claude/settings.json`:**

Configure hooks:

- **PreToolUse (Bash matcher)**: A Python hook script that:
  - Rejects bare `pytest` commands (must use `uv run pytest`)
  - Rejects bare `pre-commit` commands (must use `uv run pre-commit`)
  - Rejects bare `ruff` / `mypy` commands (must use `uv run`)
- **PostToolUse (Bash matcher)**: A reminder hook that after any file
  modification command, prints:
  `"Remember: run 'uv run pre-commit run --all-files' and 'uv run pytest' to validate changes."`
- **Stop**: Sound notification (optional, platform-dependent).
- **Notification**: Sound notification (optional, platform-dependent).

**`.claude/hooks/check-uv-prefix.py`:**

```python
#!/usr/bin/env python3
"""Hook: reject bare tool invocations that should use 'uv run'."""
import json, sys
data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
bare_tools = ["pytest", "pre-commit", "ruff ", "mypy "]
for tool in bare_tools:
    if tool in cmd and "uv run" not in cmd:
        print(f"Use 'uv run {tool.strip()}' instead of bare '{tool.strip()}'",
              file=sys.stderr)
        sys.exit(2)
```

**`.claude/hooks/post-change-reminder.py`:**

```python
#!/usr/bin/env python3
"""Hook: remind to run pre-commit and tests after changes."""
import sys
print("REMINDER: Run 'uv run pre-commit run --all-files' "
      "and 'uv run pytest' after changes.", file=sys.stderr)
sys.exit(0)
```

**Done when:** `.claude/settings.json` and hook scripts exist. Claude Code
sessions enforce `uv run` prefix and show post-change reminders.

---

### Task 1.12 — Create `CLAUDE.md` agent instructions

Create `CLAUDE.md` at the project root with instructions for AI coding
agents (Claude Code, Cursor, etc.):

```markdown
# CLAUDE.md — AI Agent Instructions for flake8-inheritance

## Project Overview
flake8-inheritance is a Flake8 plugin enforcing composition over
inheritance in Python codebases.

## Development Commands
- Install: `uv sync --all-extras --dev`
- Test: `uv run pytest`
- Test with coverage: `uv run pytest --cov=flake8_inheritance --cov-report=term-missing`
- Lint: `uv run pre-commit run --all-files`
- Type check: `uv run mypy src`
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
Check `docs/` for project documentation. Read `docs/README.md` first.
```

**Done when:** `CLAUDE.md` exists at project root with comprehensive
agent instructions.

---

### Task 1.13 — Create `docs/` directory with AI-readable documentation

Create a `docs/` directory following the "AI Zealotry" pattern of durable
documentation that AI agents can reference:

- `docs/README.md` — Index of available documentation
- `docs/architecture.md` — Overview of the plugin's architecture,
  module responsibilities, and data flow
- `docs/flake8-plugin-contract.md` — Summary of flake8's plugin API
  contract (constructor signature, `run()` yield format, `add_options`/
  `parse_options`)
- `docs/error-codes.md` — Reference for INH001 and INH002 with
  triggering examples and fix examples

These are internal developer docs, not user-facing README content.

**Done when:** `docs/README.md` exists with an index. At least 3
documentation files exist.

---

### Task 1.14 — Configure GitHub Copilot

Create `.github/copilot-instructions.md` with project-specific
instructions for GitHub Copilot:

- Project overview and architecture
- Testing conventions (TDD, pytest, fixtures in `tests/fixtures/`)
- Naming conventions (INH prefix for error codes)
- Style: use `from __future__ import annotations`, type hints everywhere,
  frozen dataclasses for value objects
- Always use `uv run` for tool invocations
- Core logic must not import from flake8

**Done when:** `.github/copilot-instructions.md` exists.

---

### Task 1.15 — Create `plans/` directory for ephemeral planning docs

Create a `plans/` directory for AI agent working documents:

- `plans/README.md` — Explains the purpose of the directory
  (ephemeral planning docs for multi-session AI development)
- `plans/.gitkeep`
- Add `plans/` to `.gitignore` (optional — some teams prefer to track
  plans for transparency)

This follows the "AI Zealotry" recommendation for keeping planning
documents in the repo for AI agent continuity across sessions.

**Done when:** `plans/` directory exists with README.

---

## Milestone 2: Core Analysis Engine (no flake8 wiring yet)

Build the AST visitors and import-tracking logic as standalone, testable
modules with no dependency on flake8. All tasks follow test-first TDD:
write the failing test, then implement.

### Task 2.1 — Define error codes in `codes.py` (TDD)

**Test first:** Write `tests/test_codes.py` with tests that:

- Import `INH001` and `INH002` from `flake8_inheritance.codes`
- Verify `INH001.format(base="Foo")` returns the expected string
- Verify `INH002.format(cls="MyABC", method="do_thing")` returns expected
- Verify `ErrorCode` is frozen (immutable)

**Then implement:** The `ErrorCode` frozen dataclass with `code`, `message`,
and a `format(**kwargs)` method. Define `INH001` and `INH002` with their
message templates:

- `INH001`: `"Inheritance from internal class '{base}' is not allowed (use composition instead)"`
- `INH002`: `"Abstract base class '{cls}' contains concrete method '{method}' (ABCs should only define abstract methods)"`

**Run:** `uv run pytest tests/test_codes.py` and
`uv run pre-commit run --all-files`.

**Done when:** All tests pass. `uv run pre-commit run --all-files` is clean.

---

### Task 2.2 — Record ADR for import classification strategy

Create an ADR documenting the import classification decision:

```bash
decree new "Classify imports using sys.stdlib_module_names and project-packages config"
```

Document the five classification categories (`internal`, `external`,
`stdlib`, `same_file`, `unknown`), the rationale for using
`sys.stdlib_module_names` (available since 3.10, eliminates hardcoded
lists), and the decision to use a sentinel value `__relative__` for
relative imports.

**Done when:** ADR exists in `doc/adr/` and `decree list` shows it.

---

### Task 2.3 — Implement import tracking in `visitors.py` (TDD)

**Test first:** Write `tests/test_visitors.py` with tests covering:

- `import foo` → `{"foo": "foo"}`
- `from foo.bar import Baz` → `{"Baz": "foo"}` (top-level package)
- `from foo.bar import Baz as B` → `{"B": "foo"}` (alias tracking)
- `from .models import Base` → `{"Base": "__relative__"}` (sentinel)
- `from . import utils` → `{"utils": "__relative__"}`
- Classification: `internal`, `external`, `stdlib`, `same_file`, `unknown`
  for each category

Tests must import `visitors.py` without flake8 installed (mock
`importlib.metadata` if needed).

**Then implement:** An `ImportTracker` that walks `ast.Import` and
`ast.ImportFrom` nodes and builds a mapping of
`{local_name: source_module}`. Plus classification logic using
`sys.stdlib_module_names`.

**Run:** `uv run pytest tests/test_visitors.py` and
`uv run pre-commit run --all-files`.

**Done when:** All tests pass covering all five classification categories
including alias handling.

---

### Task 2.4 — Implement INH001 logic: detect internal inheritance (TDD)

**Test first:** Write tests in `tests/test_visitors.py` covering:

- Same-file inheritance flagged
- Relative import inheritance flagged
- Configured project package flagged
- stdlib base class allowed
- Third-party base class allowed
- Unrecognized absolute import (no `project-packages` config) not flagged
- Dynamic base class silently skipped
- `ast.Attribute` base classes (e.g., `module.Class`) resolved correctly

**Then implement:** Extend the visitor to process `ast.ClassDef` nodes.
For each base class:

1. Resolve the base name (handle `ast.Name` and `ast.Attribute`).
2. Skip bases that are not `ast.Name` or `ast.Attribute` (dynamic bases).
3. Look up in the import map.
4. Classify as internal/external/stdlib/same\_file/unknown.
5. If `internal` or `same_file`, record an error.

Track all class names defined at module level for same-file detection.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** All INH001 tests pass.

---

### Task 2.5 — Implement INH002 logic: detect impure ABCs (TDD)

**Test first:** Write tests covering:

- Pure ABC (only abstract methods) passes
- Concrete method in ABC flagged
- `__init__` allowed by default
- `@staticmethod` + `@abstractmethod` passes
- `@classmethod` + `@abstractmethod` passes
- `ABCMeta` metaclass detected as ABC
- Class inheriting from `ABC` alias (e.g., `from abc import ABC as AbstractBase`) detected

**Then implement:** Extend the visitor to detect abstract base classes
and check method purity.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** All INH002 tests pass.

---

### Task 2.6 — Edge case hardening for visitors (TDD)

**Test first:** Write tests for:

- Star imports (`from myproject.models import *`) — skip, don't crash
- Empty files and files with no class definitions
- Deeply nested classes (class inside function or another class)
- Classes with many base classes (10+) — no quadratic behavior
- `ast.Attribute` base classes (e.g., `class Foo(module.Bar):`)
- Multiple inheritance with mixed internal and external bases

**Then implement:** Add explicit handling for each edge case.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** Every edge case has a passing test. No test takes more
than 1 second.

---

## Milestone 3: Flake8 Integration

Wire the standalone analysis engine into flake8's plugin contract.

### Task 3.1 — Wire `InheritanceChecker.run()` to the visitor (TDD)

**Test first:** Write `tests/test_checker.py` with tests that:

- Parse a simple INH001-triggering file via `ast.parse`
- Instantiate `InheritanceChecker(tree)` and call `run()`
- Assert the yielded tuples contain correct (line, col, message, type)
- Same for INH002

**Then implement:** Update `checker.py` so that `run()` creates the
visitor, calls `visitor.visit(self._tree)`, and yields results.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** Direct checker invocation produces correct results.

---

### Task 3.2 — Implement `add_options` and `parse_options` (TDD)

**Test first:** Write tests that:

- Call `parse_options` with a mock options object
- Verify class attributes are set correctly
- Test with empty values, single values, and multiple comma-separated values
- Test both `--project-packages` and `--inh002-allowed-dunders`

**Then implement:** Add the two flake8 option hooks to
`InheritanceChecker`:

- `--project-packages`: comma-separated, `parse_from_config=True`, default `""`
- `--inh002-allowed-dunders`: comma-separated, `parse_from_config=True`,
  default `"__init__"`

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** Options parsing tests pass.

---

### Task 3.3 — Handle no persistent state between files (TDD)

**Test first:** Write a regression test: instantiate the checker on two
different AST trees sequentially and confirm state from the first
doesn't leak into the second.

**Then implement:** Ensure all per-file mutable state lives in `__init__`.
Code review confirms no mutable instance state set outside `__init__`.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** State-leakage regression test passes.

---

### Task 3.4 — Write integration tests with `pytest-flake8-path` (TDD)

Write `tests/test_integration.py` with at minimum:

1. `test_plugin_loaded` — plugin appears in `flake8 --version`
2. `test_inh001_with_config` — configured project package triggers INH001
3. `test_no_false_positive_on_external` — pydantic BaseModel not flagged
4. `test_inh002_concrete_method` — concrete method in ABC triggers INH002
5. `test_noqa_suppression` — `# noqa: INH001` suppresses the violation
6. `test_zero_config_same_file` — same-file inheritance flagged without config
7. `test_zero_config_absolute_import` — absolute import with no
   `--project-packages` produces no error

**Run:** `uv run pytest tests/test_integration.py` and
`uv run pre-commit run --all-files`.

**Done when:** All 7 integration tests pass.

---

## Milestone 4: Test Fixtures, Docstrings, and Quality Polish

### Task 4.1 — Create test fixtures directory

Populate `tests/fixtures/` with standalone `.py` files:

- `internal_inheritance.py` — same-file and project-package inheritance
- `external_inheritance.py` — pydantic, sqlalchemy, django, stdlib
- `pure_abc.py` — ABC with only abstract methods
- `impure_abc.py` — ABC with concrete methods
- `mixed_bases.py` — class with both internal and external bases
- `import_aliases.py` — aliased imports (`from pydantic import BaseModel as BM`)
- `star_imports.py` — `from myproject import *`
- `dynamic_bases.py` — `class Foo(get_base()):`
- `empty_file.py` — empty
- `no_classes.py` — imports and functions only

Refactor at least 3 existing tests to use fixture files instead of
inline strings.

**Run:** `uv run pytest` and `uv run pre-commit run --all-files`.

**Done when:** All fixture files are syntactically valid Python. Existing
tests pass. At least 3 tests reference fixture files.

---

### Task 4.2 — Add docstrings to all public API

Add docstrings to:

- `InheritanceChecker` class and its public methods
- All classes and functions in `visitors.py` and `codes.py`
- Module-level docstrings for each module in `src/flake8_inheritance/`

**Run:** `uv run ruff check --select=D100,D101,D102,D103 src/` and
`uv run pre-commit run --all-files`.

**Done when:** No docstring violations in `src/`.

---

### Task 4.3 — Coverage audit and gap filling

Run `uv run pytest --cov=flake8_inheritance --cov-branch --cov-report=html`.
Review the HTML report. Add tests to cover any uncovered branches:

- Error handling paths (malformed AST, unexpected node types)
- Configuration edge cases (empty strings, whitespace-only values)
- The `format()` method on `ErrorCode`

**Run:** `uv run pytest --cov=flake8_inheritance --cov-branch`.

**Done when:** Line coverage ≥ 95%, branch coverage ≥ 90%.

---

## Milestone 5: Documentation

### Task 5.1 — Write the README: overview, install, and quickstart

Structure:

1. One-paragraph description of what the plugin does and why.
2. Installation: `pip install flake8-inheritance`
3. Quickstart (three steps): install → configure `--project-packages` → run
4. Verification: `flake8 --version` shows the plugin

Keep it concise. The quickstart should be copy-pasteable.

**Done when:** A new user can follow the README and get a working result
in under 2 minutes.

---

### Task 5.2 — Write the README: error code reference table

Add a table documenting all error codes:

| Code | Description | Triggers when… | Fix by… |
|------|-------------|-----------------|---------|
| INH001 | Inheritance from internal class | A class inherits from same-file, relative import, or configured project package class | Replace inheritance with composition |
| INH002 | Concrete method in ABC | An ABC contains a method without `@abstractmethod` | Add `@abstractmethod` or extract to utility |

Include triggering and fixed code examples for each.

**Done when:** Table is in the README with before/after code examples.

---

### Task 5.3 — Write the README: configuration reference

Document all options with defaults and examples for `.flake8`, `setup.cfg`,
and `pyproject.toml` (via Flake8-pyproject):

- `--project-packages` (default: empty)
- `--inh002-allowed-dunders` (default: `__init__`)
- Flake8-native options: `--select`, `--extend-ignore`, per-file ignores

Include a "Gradual Adoption" section describing the report-only workflow.

**Done when:** Configuration section covers all three config formats.

---

### Task 5.4 — Write the README: known limitations

Document:

- Dynamic base classes (silently skipped)
- Import aliases (tracked correctly)
- Star imports (names unresolvable, skipped)
- Re-exports through `__init__.py` (classified by import path as written)
- Single-file analysis only (no cross-file type inference)

**Done when:** Each limitation has a one-sentence explanation and
workaround where applicable.

---

### Task 5.5 — Write the README: compatibility section and badges

Add:

- Supported Python versions (3.11, 3.12, 3.13)
- Supported Flake8 versions (6.x, 7.x)
- OS support (Linux, macOS, Windows)
- CI status badge, PyPI version badge, Python version badge

**Done when:** Badges render correctly and compatibility info is present.

---

## Milestone 6: Pre-Release Hardening

### Task 6.1 — Add `off_by_default` consideration and document opt-in

Decide whether to set `off_by_default = True` on the checker class.
Create an ADR:

```bash
decree new "Decision on off_by_default for INH checker"
```

If yes, document that users must add `--enable-extensions=INH`. If no,
document that the plugin is active on install. Update README accordingly.

**Done when:** ADR recorded, code reflects decision, documentation matches.

---

### Task 6.2 — Add `.pre-commit-hooks.yaml`

Create the hook definition for users of the plugin:

```yaml
- id: flake8-inheritance
  name: flake8-inheritance
  entry: flake8 --select=INH
  language: python
  types: [python]
  additional_dependencies: ["flake8>=6"]
```

**Done when:** File exists and a test validates it is syntactically
correct YAML with required keys.

---

### Task 6.3 — Run against real-world codebases (smoke test)

Run the plugin against at least 3 well-known open-source projects:

- CPython stdlib (or a subset)
- `requests`
- `FastAPI`

Record any crashes or false positives. Fix if critical.

**Done when:** Plugin completes without unhandled exceptions on all three.
Any issues filed as GitHub issues.

---

### Task 6.4 — Confirm no prefix collision

Search the [awesome-flake8-extensions](https://github.com/DmytroLitvinov/awesome-flake8-extensions)
list and PyPI for any existing plugin using the `INH` prefix.

**Done when:** No collision found, or alternative prefix chosen and all
code/docs updated.

---

## Milestone 7: First Release

### Task 7.1 — Register PyPI Trusted Publisher

On pypi.org:

1. Go to account → Publishing → Add pending publisher.
2. Enter: project name `flake8-inheritance`, GitHub owner/repo, workflow
   file `publish.yml`, environment `pypi`.

On GitHub:

1. Create a `pypi` environment in repo Settings → Environments.
2. Optionally add required reviewers.

**Done when:** Trusted Publisher registered and environment exists.

---

### Task 7.2 — Finalize CHANGELOG for v0.1.0

Move `[Unreleased]` to `[0.1.0] - YYYY-MM-DD`. Include:

- **Added**: INH001 rule, INH002 rule, `--project-packages` option,
  `--inh002-allowed-dunders` option, pre-commit hook support.

**Done when:** CHANGELOG accurately reflects all features.

---

### Task 7.3 — Tag and release v0.1.0

1. Create git tag: `git tag v0.1.0`
2. Push the tag: `git push origin v0.1.0`
3. Create a GitHub Release, copying CHANGELOG entry as release notes.

**Done when:** Publish workflow runs, package appears on pypi.org.
`pip install flake8-inheritance` downloads v0.1.0 and
`flake8 --version` shows it.

---

### Task 7.4 — Post-release verification

In a completely clean environment:

1. `pip install flake8-inheritance`
2. Create a test file with a known INH001 violation.
3. Run `flake8 --project-packages=myproject test_file.py`
4. Confirm the violation is reported.
5. Check PyPI attestation bundle exists.

**Done when:** End-to-end flow works as a new user would experience it.

---

## Summary: Task Count by Milestone

| Milestone | Tasks | Focus |
|-----------|-------|-------|
| 0 — Repo Bootstrap | 5 | Skeleton, packaging, entry point |
| 1 — Tooling, CI/CD, AI Dev | 15 | uv, linting, CI, AI hooks, docs, ADRs |
| 2 — Core Engine | 6 | AST visitors, import tracking, rule logic (TDD) |
| 3 — Flake8 Integration | 4 | Plugin wiring, options, integration tests (TDD) |
| 4 — Quality Polish | 3 | Fixtures, docstrings, coverage |
| 5 — Documentation | 5 | README sections |
| 6 — Pre-Release Hardening | 4 | Smoke tests, collision check, pre-commit hook |
| 7 — First Release | 4 | PyPI publish, verification |
| **Total** | **46** | |

---

## Dependency Graph

```text
M0 (Bootstrap)
  │
  ▼
M1 (Tooling, CI/CD, AI Dev) ──────────────────────┐
  │                                                 │
  ├──► M1.1-1.5 (uv, ruff, mypy, pre-commit,      │
  │    pytest) ──► M1.6-1.8 (CI, publish,          │
  │    dependabot) ──► M1.10 (zizmor)              │
  │                                                 │
  ├──► M1.9 (ADRs with decree)                     │
  │                                                 │
  ├──► M1.11-1.15 (AI dev config)                  │
  │                                                 │
  ▼                                                 │
M2 (Core Engine — TDD) ◄───────────────────────────┘
  │                        (CI runs on every push)
  ▼
M3 (Flake8 Integration — TDD)
  │
  ├──► M4 (Quality Polish)
  │
  ├──► M5 (Documentation)
  │
  ▼
M6 (Pre-Release Hardening)
  │
  ▼
M7 (First Release)
```

Key parallelization opportunities:

- M1.9 (ADRs), M1.11-M1.15 (AI config) can run in parallel with
  M1.1-M1.8 (tooling/CI)
- M4 (quality polish) and M5 (docs) can progress concurrently once
  M3 is complete
- CI runs automatically from M1.6 onward, catching regressions on
  every push

---

## AI Development Workflow Summary

This project is designed for AI-assisted development from the start.
The following artifacts support this:

| Artifact | Purpose | Pattern Source |
|----------|---------|---------------|
| `CLAUDE.md` | Agent instructions (commands, rules, architecture) | AI Zealotry: docs/ |
| `.claude/settings.json` | Hooks enforcing `uv run` prefix | AI Zealotry: Hooks |
| `.claude/hooks/*.py` | Pre/post tool-use guardrails | AI Zealotry: Hooks |
| `.github/copilot-instructions.md` | GitHub Copilot context | Project convention |
| `docs/` | Durable architecture docs for agents | AI Zealotry: docs/ |
| `plans/` | Ephemeral planning docs for sessions | AI Zealotry: plans/ |
| `doc/adr/` | Architectural decisions via decree | Project convention |
| TDD throughout | Automated feedback loop for agents | AI Zealotry: Testing |
| Pre-commit + CI | Immediate automated validation | AI Zealotry: Feedback |

The hooks enforce two critical invariants:

1. **All tool invocations use `uv run`** — prevents environment mismatches.
2. **Every change triggers a reminder to run `uv run pre-commit run --all-files`
   and `uv run pytest`** — ensures continuous validation.

The TDD approach provides the "automated feedback" that Rocklin identifies
as the key to effective AI development: agents write tests first, implement
to make them pass, and get immediate signal on correctness without human
review of every line.
