# Milestone: Base Class Whitelist Option (Issue #68)

Add an `--inh001-whitelisted-bases` option that allows users to exempt specific
base classes from INH001 violations. Whitelisted entries use fully qualified
references (e.g., `mypackage.models.BaseModel`) and the implementation must
correctly resolve relative imports against these references.

---

## Ticket 1 — Design and register the `--inh001-whitelisted-bases` CLI/config option

**Description:**
Add a new flake8 option `--inh001-whitelisted-bases` to `InheritanceChecker`.
The option accepts a comma-separated list of fully qualified class references
(e.g., `mypackage.models.Base,mypackage.core.Mixin`). It should be
configurable via CLI flag and config files (`.flake8`, `setup.cfg`,
`pyproject.toml` via flake8-pyproject).

**Implementation details:**

- Register the option in `add_options()` in `checker.py`
  - Type: `str`, default: `""`, `parse_from_config=True`, `comma_separated_list=True`
- Parse into a `frozenset[str]` in `parse_options()` and store as a class
  attribute `_inh001_whitelisted_bases`
- Follow the existing pattern used by `--project-packages` and
  `--inh002-allowed-dunders`

**Acceptance criteria:**

- [ ] Option registered and parseable from CLI and config files
- [ ] Empty default produces an empty frozenset
- [ ] Whitespace around entries is stripped
- [ ] Duplicate entries are deduplicated
- [ ] `parse_options` stores a `frozenset[str]` on the class

**Complexity:** Low

---

## Ticket 2 — Write option parsing tests (TDD)

**Description:**
Following the project's test-first TDD approach, write tests in
`tests/test_options.py` for the new `--inh001-whitelisted-bases` option
**before** implementing the option in Ticket 1.

**Test cases:**

- Option is registered on the parser (attribute exists after `add_options`)
- Single fully qualified class: `"mypackage.models.Base"` → `frozenset({"mypackage.models.Base"})`
- Multiple classes: `"a.B,c.D"` → `frozenset({"a.B", "c.D"})`
- Whitespace handling: `" a.B , c.D "` → stripped correctly
- Empty string: `""` → empty frozenset
- Duplicates: `"a.B,a.B"` → single entry in frozenset
- Integration: checker with whitelist skips whitelisted bases

**Acceptance criteria:**

- [ ] All test cases written and initially failing (red phase)
- [ ] Tests follow existing patterns in `test_options.py`
- [ ] No use of MagicMock or monkeypatching

**Complexity:** Low

---

## Ticket 3 — Parse and validate fully qualified class references

**Description:**
Implement logic to match a base class encountered during AST analysis against
a fully qualified whitelist entry. This requires resolving the base class name
to its fully qualified form using import information collected by
`ImportTracker`.

**Implementation details:**

Given a base class reference like `Base` or `models.Base` in the source code,
and the import map from `ImportTracker`, reconstruct the fully qualified name:

- `from mypackage.models import Base` + base `Base` → `mypackage.models.Base`
- `import mypackage.models` + base `mypackage.models.Base` → `mypackage.models.Base`
- `from mypackage import models` + base `models.Base` → `mypackage.models.Base`
- `from mypackage.models import Base as B` + base `B` → `mypackage.models.Base`

Add a helper function (or extend `ImportTracker`) to resolve a base name to
its fully qualified dotted path. Store original import paths (not just
top-level packages) in `ImportTracker` to enable this resolution.

**Acceptance criteria:**

- [ ] Helper function resolves `ast.Name` bases to fully qualified names
- [ ] Helper function resolves `ast.Attribute` bases to fully qualified names
- [ ] Aliased imports resolved to original fully qualified name
- [ ] Relative imports produce a recognizable form (e.g., `.__relative__.ClassName`)
- [ ] Unresolvable bases return `None` (no crash)

**Complexity:** Medium

---

## Ticket 4 — Write fully qualified name resolution tests (TDD)

**Description:**
Write tests for the fully qualified name resolution logic from Ticket 3
**before** implementing it.

**Test cases:**

- `from mypackage.models import Base` → base `Base` resolves to `mypackage.models.Base`
- `import mypackage.models` → base `mypackage.models.Base` resolves to `mypackage.models.Base`
- `from mypackage import models` → base `models.Base` resolves to `mypackage.models.Base`
- `from mypackage.models import Base as B` → base `B` resolves to `mypackage.models.Base`
- `import mypackage.models as m` → base `m.Base` resolves to `mypackage.models.Base`
- Relative import: `from .models import Base` → base `Base` resolves to a
  relative form (cannot fully qualify without package context)
- Bare name (same-file class): `Base` with no import → resolves to bare `Base`
- Dynamic/unresolvable base → returns `None`
- `ast.Subscript` base: `Base[T]` → unwraps to `Base` before resolving

**Acceptance criteria:**

- [ ] All test cases written and initially failing
- [ ] Tests cover `ast.Name`, `ast.Attribute`, `ast.Subscript`, and dynamic nodes
- [ ] Tests are in `tests/test_visitors.py`

**Complexity:** Medium

---

## Ticket 5 — Integrate whitelist check into `InheritanceVisitor` / checker

**Description:**
Modify the INH001 checking logic so that a base class whose fully qualified
name matches a whitelist entry is silently skipped (no error emitted).

**Implementation details:**

- `InheritanceChecker.run()` passes the parsed `_inh001_whitelisted_bases`
  frozenset to `InheritanceVisitor` (or to a filtering step)
- Before recording an INH001 error, resolve the base to its fully qualified
  name and check membership in the whitelist frozenset
- O(1) lookup via frozenset membership test
- If the base is whitelisted, skip it; otherwise, report as before

**Acceptance criteria:**

- [ ] Whitelisted bases produce no INH001 error
- [ ] Non-whitelisted bases still produce INH001 as before
- [ ] Whitelist has no effect on INH002
- [ ] Mixed bases (some whitelisted, some not) correctly report only the
      non-whitelisted violations
- [ ] Empty whitelist preserves existing behavior exactly

**Complexity:** Medium

---

## Ticket 6 — Write whitelist integration tests (TDD)

**Description:**
Write end-to-end tests that exercise the full whitelist flow from option
parsing through AST analysis.

**Test cases:**

- Same-file base whitelisted by bare name: still flagged (whitelist requires
  fully qualified name; same-file classes have no module path)
- Internal base via `from mypackage.models import Base` whitelisted as
  `mypackage.models.Base`: no INH001
- Internal base via `import mypackage.models` whitelisted as
  `mypackage.models.Base`: no INH001
- Aliased import (`from mypackage.models import Base as B`) whitelisted as
  `mypackage.models.Base`: no INH001
- Non-whitelisted internal base: INH001 reported as usual
- Multiple bases on a class, one whitelisted and one not: only the
  non-whitelisted base flagged
- Whitelist entry that doesn't match anything: no effect, no crash
- Empty whitelist: all existing behavior preserved (regression guard)

**Acceptance criteria:**

- [ ] All test cases written and initially failing
- [ ] Tests cover both `InheritanceVisitor` directly and via
      `InheritanceChecker.run()`
- [ ] Integration test with `pytest-flake8-path` confirming CLI option works

**Complexity:** Medium

---

## Ticket 7 — Handle relative imports against the whitelist

**Description:**
Relative imports (`from .models import Base`, `from ..core import Mixin`)
cannot be resolved to a fully qualified name without knowing the current
file's package path, which flake8's AST checker API does not provide.

**Design decision needed:** Choose one of:

1. **Do not match relative imports against the whitelist.** Document this as
   a known limitation. Users must use absolute imports for whitelisted bases.
2. **Accept a relative-style whitelist entry** (e.g., `.models.Base`) and
   match it against the relative import path as-is.
3. **Derive the package path** from the filename (if available via
   `flake8.options` or checker metadata) and reconstruct fully qualified names
   for relative imports.

The recommended approach is option (1) with clear documentation, as it is the
simplest and most predictable. Relative imports flagged as INH001 can be
suppressed with `# noqa: INH001` if they are intentionally whitelisted but
use relative syntax.

**Acceptance criteria:**

- [ ] Chosen approach is implemented
- [ ] ADR documenting the decision created in `doc/adr/`
- [ ] Tests confirm relative imports behave as documented
- [ ] Edge cases (deeply nested relative imports, `from . import X`) handled

**Complexity:** Low-Medium (depends on chosen approach)

---

## Ticket 8 — Write relative import whitelist tests (TDD)

**Description:**
Write tests for the relative import handling decision from Ticket 7.

**Test cases (assuming option 1 — no relative import matching):**

- `from .models import Base` with `Base` in whitelist as `.models.Base`:
  still flagged (relative imports not matched)
- `from .models import Base` with `# noqa: INH001`: suppressed
- Document-style test: verify the chosen behavior is consistent

**Test cases (if option 2 or 3 is chosen instead):**

- Adjust tests to match the resolved design

**Acceptance criteria:**

- [ ] Tests written and initially failing
- [ ] Tests match the chosen design from Ticket 7

**Complexity:** Low

---

## Ticket 9 — Update documentation

**Description:**
Update all relevant documentation to describe the new whitelist option.

**Files to update:**

- `README.md` — Add `--inh001-whitelisted-bases` to the configuration
  reference section with examples in `.flake8`, `setup.cfg`, and
  `pyproject.toml` formats
- `docs/error-codes.md` — Note that INH001 respects the whitelist
- `CHANGELOG.md` — Add entry under `[Unreleased]`
- `CLAUDE.md` — If the architecture section needs updating

**Documentation content:**

- Option name, format, and default value
- Example configuration:
  ```ini
  [flake8]
  inh001-whitelisted-bases =
      mypackage.models.BaseModel,
      mypackage.core.BaseMixin
  ```
- Explanation that entries must be fully qualified dotted names
- Note on relative imports (based on Ticket 7 decision)
- Example showing a whitelisted base producing no error

**Acceptance criteria:**

- [ ] README updated with option reference and examples
- [ ] CHANGELOG updated
- [ ] All documentation passes `uv run pre-commit run --all-files`

**Complexity:** Low

---

## Ticket 10 — Create ADR for whitelist design decisions

**Description:**
Record the architectural decisions made during this feature's implementation.

**ADR content:**

- Title: "Use fully qualified names for base class whitelist"
- Context: Users need to exempt specific base classes from INH001 while
  keeping the rule active for other internal inheritance
- Decision: Whitelist entries are fully qualified dotted names matched against
  resolved import paths; relative imports are handled per Ticket 7 decision
- Consequences: Users must know the fully qualified name of whitelisted bases;
  relative imports may require `# noqa` if not using absolute imports

**Acceptance criteria:**

- [ ] ADR created via `decree new "..."` in `doc/adr/`
- [ ] ADR documents the fully qualified name requirement
- [ ] ADR documents the relative import handling decision

**Complexity:** Low

---

## Summary

| Ticket | Title | Complexity | Dependencies |
|--------|-------|------------|--------------|
| 1 | Register `--inh001-whitelisted-bases` option | Low | — |
| 2 | Option parsing tests (TDD) | Low | — |
| 3 | Fully qualified name resolution logic | Medium | 1 |
| 4 | Name resolution tests (TDD) | Medium | — |
| 5 | Integrate whitelist into INH001 checking | Medium | 1, 3 |
| 6 | Whitelist integration tests (TDD) | Medium | — |
| 7 | Handle relative imports | Low-Medium | 3, 5 |
| 8 | Relative import whitelist tests (TDD) | Low | — |
| 9 | Update documentation | Low | 5, 7 |
| 10 | Create ADR | Low | 7 |

**Recommended implementation order (TDD pairs):**

1. Tickets 2 + 1 (option parsing: tests first, then implementation)
2. Tickets 4 + 3 (name resolution: tests first, then implementation)
3. Tickets 6 + 5 (integration: tests first, then implementation)
4. Tickets 8 + 7 (relative imports: tests first, then implementation)
5. Tickets 9 + 10 (documentation and ADR)

**Dependency graph:**

```text
Tickets 2,4,6,8 (tests)     Tickets 1,3 (foundation)
        │                          │
        ▼                          ▼
   Ticket 5 (integration) ◄── Tickets 1 + 3
        │
        ▼
   Ticket 7 (relative imports)
        │
        ├──► Ticket 9 (docs)
        └──► Ticket 10 (ADR)
```
