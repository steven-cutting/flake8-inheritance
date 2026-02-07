# 9: Decouple visitor analysis logic from flake8 plugin interface

Date: 2026-02-07
Status: Accepted

## Context

The plugin is built for flake8, but the engineering specification requires that the design not preclude future ports to other linter platforms — specifically the Ruff plugin API (when available), Pylint custom checkers, and a potential standalone CLI. Flake8's plugin contract is a specific interface (`name`, `version`, `__init__(tree)`, `run()` yielding 4-tuples), and coupling the analysis logic to this interface would require reimplementing it for each target platform. Additionally, testing analysis logic through the flake8 interface adds unnecessary indirection and fragility to the test suite. A clean separation between "what to analyze" (visitors, classification, error definitions) and "how to integrate with flake8" (the checker class) enables independent testing, reuse, and future portability. This decision has now been validated by the implementation: `codes.py` and `visitors.py` are fully implemented and tested with zero flake8 imports.

## Decision

The analysis layer is implemented in two modules — `codes.py` (error definitions) and `visitors.py` (AST walking, import tracking, base class classification, ABC inspection) — that depend only on the Python standard library. Neither module imports from `flake8`. The flake8 checker class (`checker.py`, wired in Milestone 2) will be a thin adapter that instantiates the visitor, passes configuration, and reformats the visitor's output into flake8's expected 4-tuple format. The adapter owns the flake8-specific `add_options`, `parse_options`, `name`, and `version` attributes.

## Consequences

`visitors.py` and `codes.py` can be imported and tested without flake8 installed. Unit tests call the visitor directly via `ast.parse`, which is fast and deterministic. A future port to another platform requires writing only a new adapter module — the analysis logic is reused unchanged. The tradeoff is a small amount of structural overhead (two modules plus an adapter, rather than a single monolithic checker class), but this is justified by the testing and portability benefits.
