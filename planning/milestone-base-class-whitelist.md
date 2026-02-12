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

## Ticket 3 — Enrich `ImportTracker` and implement FQN resolution

**Description:**
Extend `ImportTracker` to preserve full import paths (not just top-level
packages) and, for relative imports, preserve the dot level and module suffix.
Then implement a helper to resolve a base class reference to its fully
qualified name (FQN), or to a structured relative form that retains enough
information for plausible whitelist matching.

**Current state (what's lost today):**

In `visitors.py:64-84`, `ImportTracker` currently stores:
- `imports[local_name]` → top-level package only (e.g., `"mypackage"`) or
  `RELATIVE_SENTINEL` for all relative imports
- `original_names[local_name]` → the original imported name (e.g., `"Base"`)

This discards:
- The full module path for absolute imports (e.g., `mypackage.models` is
  reduced to `mypackage`)
- The dot level (`node.level`) for relative imports
- The module suffix after the dots (e.g., `models` in `from .models import Base`)

**Implementation details:**

### 3a. Enrich `ImportTracker` storage

Add a new dict (or extend existing ones) to store full import context:

```python
# New storage for FQN resolution:
self.full_modules: dict[str, str | None] = {}
# Maps local_name → full module path as written in the import statement
# e.g., "Base" → "mypackage.models" (from `from mypackage.models import Base`)
# e.g., "m"    → "mypackage.models" (from `import mypackage.models as m`)

# For relative imports, store structured info:
self.relative_imports: dict[str, RelativeImportInfo] = {}
```

Where `RelativeImportInfo` is a frozen dataclass:

```python
@dataclass(frozen=True)
class RelativeImportInfo:
    level: int           # number of dots (1 for ".", 2 for "..", etc.)
    module: str | None   # module path after the dots (e.g., "models" or "core.models")
    name: str            # the original imported name (e.g., "Base")
```

In `visit_Import`:
- `import mypackage.models` → `full_modules["mypackage"] = "mypackage.models"`
  (or the local alias)
- `import mypackage.models as m` → `full_modules["m"] = "mypackage.models"`

In `visit_ImportFrom`:
- `from mypackage.models import Base` → `full_modules["Base"] = "mypackage.models"`
- `from mypackage.models import Base as B` → `full_modules["B"] = "mypackage.models"`
- `from .models import Base` (level=1, module="models") →
  `relative_imports["Base"] = RelativeImportInfo(level=1, module="models", name="Base")`
- `from ..core import Mixin` (level=2, module="core") →
  `relative_imports["Mixin"] = RelativeImportInfo(level=2, module="core", name="Mixin")`
- `from . import utils` (level=1, module=None) →
  `relative_imports["utils"] = RelativeImportInfo(level=1, module=None, name="utils")`

### 3b. FQN resolution for absolute imports

Add a method `resolve_fqn(base_name: str) -> str | None` to `ImportTracker`
(or as a standalone function):

- `Base` (ast.Name) where `full_modules["Base"] = "mypackage.models"` and
  `original_names["Base"] = "Base"` → `"mypackage.models.Base"`
- `m.Base` (ast.Attribute) where `full_modules["m"] = "mypackage.models"` →
  `"mypackage.models.Base"`
- `mypackage.models.Base` (ast.Attribute, no alias) where
  `full_modules["mypackage"] = "mypackage.models"` →
  `"mypackage.models.Base"`
- Same-file class with no import → returns bare name `"Base"` (no FQN)
- Unresolvable → returns `None`

### 3c. Structured relative import representation

For relative imports, instead of resolving to a single FQN (impossible without
knowing file location), return a `RelativeImportInfo` or a structured string
that preserves the level and suffix. This feeds into the plausible matching
logic in Ticket 7.

**Important:** The existing `imports` and `original_names` dicts must continue
to work as before — the new storage is additive, not a replacement. All
existing `classify()` behavior must be preserved.

**Acceptance criteria:**

- [ ] `ImportTracker` stores full module paths in `full_modules`
- [ ] `ImportTracker` stores `RelativeImportInfo` for relative imports
- [ ] `resolve_fqn()` resolves `ast.Name` bases to FQN via `full_modules`
- [ ] `resolve_fqn()` resolves `ast.Attribute` bases (e.g., `m.Base`) to FQN
- [ ] Aliased imports resolve to original FQN
- [ ] Relative imports return structured info (not a lossy sentinel)
- [ ] Unresolvable bases return `None` (no crash)
- [ ] All existing `classify()` and `imports`/`original_names` behavior preserved
- [ ] `RelativeImportInfo` is a frozen dataclass

**Complexity:** Medium

---

## Ticket 4 — Write enriched `ImportTracker` and FQN resolution tests (TDD)

**Description:**
Write tests for the enriched `ImportTracker` storage and FQN resolution logic
from Ticket 3 **before** implementing it.

**Test cases for enriched storage:**

- `full_modules` populated correctly:
  - `from mypackage.models import Base` → `full_modules["Base"] = "mypackage.models"`
  - `import mypackage.models` → `full_modules["mypackage"] = "mypackage.models"`
  - `import mypackage.models as m` → `full_modules["m"] = "mypackage.models"`
  - `from mypackage import models` → `full_modules["models"] = "mypackage"`
- `relative_imports` populated correctly:
  - `from .models import Base` → `RelativeImportInfo(level=1, module="models", name="Base")`
  - `from ..core.models import Base` → `RelativeImportInfo(level=2, module="core.models", name="Base")`
  - `from . import utils` → `RelativeImportInfo(level=1, module=None, name="utils")`
  - `from ... import deep` → `RelativeImportInfo(level=3, module=None, name="deep")`
- Existing `imports` and `original_names` dicts unchanged (regression tests)

**Test cases for FQN resolution:**

- `from mypackage.models import Base` → base `Base` resolves to `"mypackage.models.Base"`
- `import mypackage.models` → base `mypackage.models.Base` resolves to `"mypackage.models.Base"`
- `from mypackage import models` → base `models.Base` resolves to `"mypackage.models.Base"`
- `from mypackage.models import Base as B` → base `B` resolves to `"mypackage.models.Base"`
- `import mypackage.models as m` → base `m.Base` resolves to `"mypackage.models.Base"`
- Relative import: `from .models import Base` → returns `None` or
  `RelativeImportInfo` (not a FQN string — handled separately in Ticket 7)
- Bare name (same-file class): `Base` with no import → resolves to bare `"Base"`
- Dynamic/unresolvable base → returns `None`
- `ast.Subscript` base: `Base[T]` → unwraps to `Base` before resolving

**Acceptance criteria:**

- [ ] All test cases written and initially failing
- [ ] Tests cover `full_modules`, `relative_imports`, and `resolve_fqn()`
- [ ] Tests cover `ast.Name`, `ast.Attribute`, `ast.Subscript`, and dynamic nodes
- [ ] Regression tests confirm existing `imports`/`original_names` behavior
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

## Ticket 7 — Handle relative imports via plausible suffix matching

**Description:**
Relative imports (`from .models import Base`, `from ..core import Mixin`)
cannot be resolved to an exact fully qualified name without knowing the
current file's package path, which flake8's AST checker API does not provide.

However, by combining the structured `RelativeImportInfo` (from Ticket 3)
with the `--project-packages` configuration, we can perform **plausible
suffix matching**: checking whether a whitelist entry *could* correspond to
the relative import, even if we can't be 100% certain.

**Approach: plausible suffix matching with `--project-packages`**

Given a relative import and a whitelist entry, determine whether the entry is
a plausible match by checking three conditions:

1. **Project package prefix**: The whitelist entry starts with a configured
   `--project-packages` value (relative imports are always within the project)
2. **Suffix match**: The whitelist entry ends with the import's module suffix
   + name
3. **Depth plausibility**: The whitelist entry has enough intermediate path
   segments to be consistent with the relative import level

**Worked examples:**

```python
# --project-packages=mypackage

# Example 1: from .models import Base  (level=1, module="models")
# Suffix = "models.Base"
# Whitelist entry "mypackage.models.Base":
#   ✓ starts with "mypackage"
#   ✓ ends with "models.Base"
#   ✓ depth: entry has 3 segments, suffix has 2 → 1 intermediate segment
#     level=1 means current file is ≥1 deep, so ≥0 segments between pkg root
#     and the relative target. 1 intermediate segment is plausible.
#   → PLAUSIBLE MATCH

# Example 2: from ..core.models import Base  (level=2, module="core.models")
# Suffix = "core.models.Base"
# Whitelist entry "mypackage.core.models.Base":
#   ✓ starts with "mypackage"
#   ✓ ends with "core.models.Base"
#   ✓ depth: 4 segments total, suffix=3 → 1 intermediate. level=2 means
#     we go up 2, so the target is 2 levels above current. Plausible if
#     current file is ≥2 deep in the package.
#   → PLAUSIBLE MATCH

# Example 3: from .models import Base  (level=1, module="models")
# Whitelist entry "mypackage.utils.Base":
#   ✓ starts with "mypackage"
#   ✗ does NOT end with "models.Base"
#   → NOT A MATCH

# Example 4: from .models import Base  (level=1, module="models")
# Whitelist entry "mypackage.foo.models.Base":
#   ✓ starts with "mypackage"
#   ✓ ends with "models.Base"
#   ✓ depth is plausible
#   → PLAUSIBLE MATCH (may be a false positive — different subpackage
#     could have a "models.Base" too, but this is acceptable)

# Example 5: from .models import Base  (level=1, module="models")
# No --project-packages configured:
#   ✗ cannot verify project package prefix
#   → CANNOT MATCH (relative imports without project-packages config
#     are not matchable against the whitelist)
```

**Algorithm:**

```python
def is_plausible_whitelist_match(
    rel_info: RelativeImportInfo,
    whitelist_entry: str,
    project_packages: tuple[str, ...],
) -> bool:
    # Build the suffix from the relative import
    if rel_info.module:
        suffix = f"{rel_info.module}.{rel_info.name}"
    else:
        suffix = rel_info.name

    # Check if whitelist entry ends with the suffix
    if not whitelist_entry.endswith(suffix):
        return False

    # Check if whitelist entry starts with a project package
    entry_root = whitelist_entry.split(".")[0]
    if entry_root not in project_packages:
        return False

    # Check depth plausibility:
    # The entry without the project package prefix and without the suffix
    # gives us the "middle" segments. These must be ≥ 0.
    entry_parts = whitelist_entry.split(".")
    suffix_parts = suffix.split(".")
    # middle_count = total_parts - 1 (pkg root) - len(suffix_parts)
    middle_count = len(entry_parts) - 1 - len(suffix_parts)
    if middle_count < 0:
        return False

    # The relative level tells us how far up we go. The target is
    # (level - 1) packages above the current package, then descend into
    # module. The middle segments represent the path from package root
    # to the relative target's parent. This must be ≥ 0, which we
    # already checked.
    return True
```

**Key design decisions:**

- **False positives are acceptable**: If `from .models import Base` matches
  both `mypackage.models.Base` and `mypackage.sub.models.Base` in the
  whitelist, we accept the match. The user has explicitly whitelisted these
  names, so a plausible match is treated as intentional.
- **No `--project-packages` = no relative matching**: Without knowing the
  project package, we cannot verify the prefix. Relative imports remain
  flagged. This is documented as a requirement for relative import whitelist
  matching.
- **Level is preserved for future tightening**: Even if we don't use it for
  strict filtering now, storing the level allows future refinements (e.g., if
  flake8 exposes file paths, we could resolve exactly).

**Acceptance criteria:**

- [ ] `is_plausible_whitelist_match()` implemented as a pure function
- [ ] Suffix matching works for single-segment and multi-segment module paths
- [ ] Project package prefix is verified against `--project-packages`
- [ ] Depth plausibility check prevents impossible matches
- [ ] No match attempted when `--project-packages` is not configured
- [ ] `from . import X` (no module) handled correctly (suffix is just `X`)
- [ ] Multiple project packages all checked (any match = plausible)
- [ ] ADR documenting the plausible matching decision created in `doc/adr/`
- [ ] Edge cases: `from ... import X` (level=3), deeply nested modules

**Complexity:** Medium

---

## Ticket 8 — Write plausible suffix matching tests (TDD)

**Description:**
Write tests for the `is_plausible_whitelist_match()` function and the
end-to-end relative import whitelist flow **before** implementing Ticket 7.

**Unit tests for `is_plausible_whitelist_match()`:**

- `from .models import Base` (level=1, module="models") with
  whitelist `"mypackage.models.Base"`, project_packages=`("mypackage",)` → `True`
- `from ..core.models import Base` (level=2, module="core.models") with
  whitelist `"mypackage.core.models.Base"`, project_packages=`("mypackage",)` → `True`
- `from .models import Base` (level=1, module="models") with
  whitelist `"mypackage.utils.Base"` → `False` (suffix mismatch)
- `from .models import Base` (level=1, module="models") with
  whitelist `"mypackage.foo.models.Base"` → `True` (plausible false positive, accepted)
- `from .models import Base` (level=1, module="models") with
  whitelist `"otherpackage.models.Base"`, project_packages=`("mypackage",)` → `False`
  (wrong project package)
- `from .models import Base` with no `--project-packages` configured → `False`
  (cannot verify prefix)
- `from . import utils` (level=1, module=None) with
  whitelist `"mypackage.utils"` → `True` (suffix is just `"utils"`)
- `from ... import deep` (level=3, module=None) with
  whitelist `"mypackage.deep"` → `True` (plausible)
- `from .models import Base` (level=1, module="models") with
  whitelist `"models.Base"` (no project package prefix) → `False`
  (entry root not in project_packages)
- Whitelist entry too short to contain suffix → `False` (depth < 0)
- Multiple project packages: `project_packages=("pkg_a", "pkg_b")`,
  entry `"pkg_b.models.Base"` → `True`

**End-to-end integration tests:**

- Code with `from .models import Base` + `class Child(Base):`
  + whitelist `"mypackage.models.Base"` + `--project-packages=mypackage`
  → no INH001
- Same code without `--project-packages` → INH001 still flagged
  (relative matching requires project-packages)
- Same code with whitelist entry that doesn't suffix-match → INH001 flagged
- Mixed: class with one whitelisted relative base and one non-whitelisted
  → only the non-whitelisted one flagged

**Acceptance criteria:**

- [ ] Unit tests for `is_plausible_whitelist_match()` written and failing
- [ ] Integration tests covering the full flow written and failing
- [ ] Edge cases: level=3, module=None, multiple project packages
- [ ] Tests are in `tests/test_visitors.py` (unit) and
      `tests/test_integration.py` (integration)

**Complexity:** Medium

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

- Title: "Use fully qualified names with plausible suffix matching for base
  class whitelist"
- Context: Users need to exempt specific base classes from INH001 while
  keeping the rule active for other internal inheritance. Relative imports
  cannot be resolved to exact FQNs without file path context.
- Decision:
  - Whitelist entries are fully qualified dotted names
  - Absolute imports are resolved to exact FQNs and matched precisely
  - Relative imports use plausible suffix matching: verify project package
    prefix + suffix match + depth plausibility
  - `--project-packages` is required for relative import whitelist matching
- Consequences:
  - Users must know the fully qualified name of whitelisted bases
  - Relative imports can be matched when `--project-packages` is configured
  - Plausible matching may produce false positives when different subpackages
    have identically-named modules and classes (accepted trade-off)
  - Without `--project-packages`, relative imports cannot match whitelist
    entries and remain flagged

**Acceptance criteria:**

- [ ] ADR created via `decree new "..."` in `doc/adr/`
- [ ] ADR documents the fully qualified name requirement
- [ ] ADR documents the plausible suffix matching algorithm for relative imports
- [ ] ADR documents the `--project-packages` requirement for relative matching
- [ ] ADR documents the accepted false positive trade-off

**Complexity:** Low

---

## Summary

| Ticket | Title | Complexity | Dependencies |
|--------|-------|------------|--------------|
| 1 | Register `--inh001-whitelisted-bases` option | Low | — |
| 2 | Option parsing tests (TDD) | Low | — |
| 3 | Enrich `ImportTracker` + FQN resolution | Medium | 1 |
| 4 | Enriched tracker + FQN resolution tests (TDD) | Medium | — |
| 5 | Integrate whitelist into INH001 checking | Medium | 1, 3 |
| 6 | Whitelist integration tests (TDD) | Medium | — |
| 7 | Plausible suffix matching for relative imports | Medium | 3, 5 |
| 8 | Plausible suffix matching tests (TDD) | Medium | — |
| 9 | Update documentation | Low | 5, 7 |
| 10 | Create ADR | Low | 7 |

**Recommended implementation order (TDD pairs):**

1. Tickets 2 + 1 (option parsing: tests first, then implementation)
2. Tickets 4 + 3 (enriched tracker + FQN: tests first, then implementation)
3. Tickets 6 + 5 (whitelist integration: tests first, then implementation)
4. Tickets 8 + 7 (plausible suffix matching: tests first, then implementation)
5. Tickets 9 + 10 (documentation and ADR)

**Dependency graph:**

```text
Tickets 2,4,6,8 (tests)     Tickets 1,3 (foundation)
        │                          │
        ▼                          ▼
   Ticket 5 (integration) ◄── Tickets 1 + 3
        │
        ▼
   Ticket 7 (plausible suffix matching for relative imports)
        │               uses --project-packages to verify prefix
        │               uses level + module suffix for matching
        │
        ├──► Ticket 9 (docs)
        └──► Ticket 10 (ADR)
```

**Key design insight:** Relative imports cannot be resolved to exact FQNs
without the file's package path, but by combining three pieces of information
we can perform plausible matching:

1. **`--project-packages`** → the whitelist entry must start with a known
   project package (relative imports are always within the project)
2. **Module suffix + name** → the whitelist entry must end with the
   import's module path + class name
3. **Dot level** → preserved for depth plausibility checks and potential
   future tightening if flake8 exposes file paths
