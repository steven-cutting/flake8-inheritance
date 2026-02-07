# 7: Define error codes as framework-agnostic frozen dataclasses

Date: 2026-02-07
Status: Accepted

## Context

The plugin's error codes need a structured representation for formatting messages, testing, and future extensibility. Flake8 plugins typically define errors as raw string tuples inline in the checker class. However, the engineering specification requires that the core analysis logic be decoupled from flake8 to enable future ports to other linter platforms (Ruff plugin API, Pylint checker, standalone CLI). Error definitions that are flake8-specific tuples would couple the analysis layer to the presentation layer. A frozen dataclass provides type safety, immutability, and a clean `format()` interface while depending only on the standard library's `dataclasses` module.

## Decision

We define error codes as instances of a `@dataclass(frozen=True)` class `ErrorCode` in a dedicated `codes.py` module. Each instance holds a `code` string and a `message` template string. A `format(**kwargs)` method produces the final message. The module has no dependency on flake8 — it uses only the standard library.

## Consequences

Error codes are importable and testable without flake8 installed. New rules are added by defining new `ErrorCode` instances. The message format is enforced via tests, not convention. If the plugin is ported to another linter framework, `codes.py` requires zero changes.
