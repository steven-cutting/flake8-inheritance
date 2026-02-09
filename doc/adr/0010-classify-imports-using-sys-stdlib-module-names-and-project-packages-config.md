# 10: Classify imports using sys.stdlib_module_names and project-packages config

Date: 2026-02-09
Status: Accepted

## Context

The import analysis engine needs a consistent way to classify imported
modules so it can reason about composition rules. The classification must
distinguish standard library modules from third-party dependencies and local
project modules, while also handling relative imports and edge cases where
the origin is not clear at analysis time. Maintaining a hardcoded list of
stdlib modules is brittle and error-prone across Python versions. We also
need a deterministic representation for relative imports so we can defer
resolution to later stages while still recording their presence.

## Decision

Classify imports into five categories: `internal`, `external`, `stdlib`,
`same_file`, and `unknown`. Use `sys.stdlib_module_names` (available since
Python 3.10) to identify standard library modules, and use the
project-packages configuration to recognize third-party dependencies. For
relative imports, record the module name as the sentinel value
`__relative__`.

## Consequences

- The stdlib classification stays aligned with the running Python version
  without maintaining a custom list.
- The analyzer can distinguish local modules (`internal`), dependencies
  (`external`), standard library (`stdlib`), imports from the same module
  (`same_file`), and unresolved cases (`unknown`) in a consistent way.
- Relative imports are explicitly tracked with `__relative__`, allowing later
  resolution logic to treat them separately.
- The approach relies on `sys.stdlib_module_names`, available in Python 3.10+,
  and is fully compatible with the project's minimum supported Python version
  (3.11+).

## Alternatives considered

- Maintain a hardcoded stdlib list: rejected due to ongoing maintenance and
  version drift.
- Use `importlib.util.find_spec` for classification: rejected because it can
  execute import hooks and is slow or unreliable for non-installed modules
  during static analysis.
- Encode relative imports with empty module names: rejected because it is
  ambiguous and harder to distinguish from missing data.
