# Architecture

## Module Map

```text
src/flake8_inheritance/
├── __init__.py        # Package marker; re-exports nothing
├── checker.py         # Flake8 plugin entry point (depends on flake8)
├── codes.py           # Error code constants (stdlib only)
└── visitors.py        # AST visitor logic (stdlib only)
```

### checker.py

Contains `InheritanceChecker`, the sole class registered with flake8.
It receives a parsed AST via `__init__` and yields diagnostics from
`run()`. This module is the only one that depends on flake8.

### visitors.py

Houses the AST walking logic. Visitors operate on `ast.AST` nodes and
return findings as plain data (no flake8 types). This separation means
the core detection logic can be tested and used without flake8 installed.

### codes.py

Defines error code constants (message strings keyed by code). Keeping
codes in their own module avoids circular imports and makes it easy for
other tools to enumerate available diagnostics.

## Dependency Rule

```text
checker.py  -->  visitors.py  -->  (stdlib only)
     |                              codes.py  -->  (stdlib only)
     v
  flake8
```

Only `checker.py` imports from flake8. Both `visitors.py` and `codes.py`
are importable with nothing beyond the standard library. This is enforced
by a smoke test in the test suite.

## Data Flow

```text
1. flake8 parses a Python file into an ast.Module
2. flake8 instantiates InheritanceChecker(tree=<ast.Module>)
3. flake8 calls checker.run()
4. run() delegates to visitors, passing the stored AST
5. Visitors walk the tree, collecting class definitions that inherit
   from non-exempt bases
6. run() yields (line, col, message, type) tuples back to flake8
```

## Error Code Ranges

| Range | Category |
|---|---|
| INH0xx | Inheritance restriction rules |
| INH1xx | ABC purity checks |
| INH2xx | Reserved for future use |

See [error-codes.md](error-codes.md) for individual code details.

## Design Principles

1. **Composition over inheritance** -- the plugin eats its own dogfood.
   `InheritanceChecker` does not subclass any flake8 base class; it
   satisfies the plugin contract through duck typing.

2. **Single-pass AST walk** -- one traversal of the tree, O(1) lookups
   for exempt bases.

3. **Zero runtime dependencies beyond flake8** -- the plugin adds no
   transitive dependencies to a user's environment.

4. **Decouple core logic from flake8** -- visitors and codes are
   testable in isolation without flake8 installed.

## Key ADRs

- [ADR-0002](../doc/adr/0002-use-src-layout-for-package-structure.md) --
  src layout
- [ADR-0007](../doc/adr/0007-use-composition-over-inheritance-as-the-core-design-principle.md) --
  composition over inheritance as design principle
- [ADR-0008](../doc/adr/0008-use-flake8-ast-checker-plugin-architecture.md) --
  AST checker architecture
