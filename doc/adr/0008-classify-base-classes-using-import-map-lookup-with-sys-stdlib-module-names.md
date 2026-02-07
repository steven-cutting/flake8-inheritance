# 8: Classify base classes using import-map lookup with sys.stdlib_module_names

Date: 2026-02-07
Status: Accepted

## Context

The plugin's core value proposition is distinguishing internal inheritance (flagged) from external inheritance (allowed). This requires classifying each base class by its origin. There are several approaches: (1) maintain a hardcoded list of stdlib and common third-party modules, (2) use type inference via `astroid` (the Pylint approach), (3) track imports at the AST level and classify by top-level package name using `sys.stdlib_module_names`. Option 1 is fragile and version-dependent. Option 2 is accurate but slow and adds a heavy dependency. Option 3 uses a single-pass AST walk with O(1) dictionary lookups and depends only on the standard library. `sys.stdlib_module_names`, available since Python 3.10, provides an authoritative set of stdlib module names for the running interpreter, eliminating the need for a manually maintained list. Relative imports (`from .foo import Bar`) are unambiguously internal regardless of configuration, so they receive a sentinel value `"__relative__"` in the import map. Names that cannot be classified (not imported, not defined locally) are labeled `"unknown"` and are never flagged — the plugin errs on the side of silence rather than false positives.

## Decision

We build an import map (`dict[str, str]`) during AST traversal that maps each imported local name to its top-level source package. Relative imports are mapped to the sentinel `"__relative__"`. Classification uses a priority-ordered lookup: same-file definitions first, then the import map (checking for relative sentinel, then the user-configured `project_packages` list, then `sys.stdlib_module_names`), with `"unknown"` as the fallback. All lookups use set/dict membership tests for O(1) performance.

## Consequences

The plugin cannot classify names imported via `from foo import *` (star imports) since the individual names are not in the import map — these are silently skipped. Classification accuracy depends on the user correctly configuring `--project-packages` for absolute imports from their own project. Without configuration, only same-file and relative-import inheritance are detected. The plugin adapts automatically to new stdlib modules in future Python versions because `sys.stdlib_module_names` is authoritative for the running interpreter.
