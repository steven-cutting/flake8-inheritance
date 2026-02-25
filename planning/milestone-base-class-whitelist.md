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

Also define a hint-variant error message in `codes.py` for the case where a
relative import's base class suffix-matches a whitelist entry but cannot be
confirmed due to missing `--project-packages` configuration.

**Implementation details:**

- Register the option in `add_options()` in `checker.py`
  - Type: `str`, default: `""`, `parse_from_config=True`, `comma_separated_list=True`
- Parse into a `tuple[str, ...]` in `parse_options()` and store as a class
  attribute `_inh001_whitelisted_bases` (convert to `frozenset` locally
  where O(1) membership lookups are needed, matching the pattern used by
  `_project_packages` and `_inh002_allowed_dunders`)
- Follow the existing pattern used by `--project-packages` and
  `--inh002-allowed-dunders`
- Add to `codes.py` a hint-variant message for INH001:

```python
INH001_HINT = ErrorCode(
    code="INH001",
    message=(
        "Inheritance from internal class '{base}' is not allowed "
        "(use composition instead). "
        "Note: '{base}' may match whitelisted entry '{entry}'; "
        "configure --project-packages to enable whitelist matching "
        "for relative imports"
    ),
)
```

This keeps the same `INH001` code (so `# noqa: INH001` still suppresses it)
but gives the user actionable guidance. The `{entry}` placeholder names the
specific whitelist entry that suffix-matched.

**Acceptance criteria:**

- [ ] Option registered and parseable from CLI and config files
- [ ] Empty default produces an empty tuple
- [ ] Whitespace around entries is stripped
- [ ] Duplicate entries are deduplicated (at parse time, before storing)
- [ ] `parse_options` stores a `tuple[str, ...]` on the class (consistent
      with `_project_packages` and `_inh002_allowed_dunders`)
- [ ] `INH001_HINT` defined in `codes.py` with `{base}` and `{entry}` placeholders
- [ ] `INH001_HINT.code` is still `"INH001"` (same noqa suppression)

**Complexity:** Low

---

## Ticket 2 — Write option parsing tests (TDD)

**Description:**
Following the project's test-first TDD approach, write tests in
`tests/test_options.py` for the new `--inh001-whitelisted-bases` option
**before** implementing the option in Ticket 1.

**Test cases:**

- Option is registered on the parser (attribute exists after `add_options`)
- Single fully qualified class: `"mypackage.models.Base"` → `("mypackage.models.Base",)`
- Multiple classes: `"a.B,c.D"` → `("a.B", "c.D")`
- Whitespace handling: `" a.B , c.D "` → stripped correctly
- Empty string: `""` → empty tuple `()`
- Duplicates: `"a.B,a.B"` → deduplicated to `("a.B",)`
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
self.full_modules: dict[str, str] = {}
# Maps local_name → the fully qualified name of what that local name
# is BOUND to (not the module it was imported from).
# e.g., "Base" → "mypackage.models.Base" (from `from mypackage.models import Base`)
# e.g., "m"    → "mypackage.models"      (from `import mypackage.models as m`)
# e.g., "mypackage" → "mypackage"        (from `import mypackage.models`)

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
- `import mypackage.models` → `full_modules["mypackage"] = "mypackage"`
  (Python binds the name `mypackage` to the top-level package; the
  submodule `models` is loaded as a side effect but the local name
  refers to the package itself)
- `import mypackage.models as m` → `full_modules["m"] = "mypackage.models"`
  (the alias `m` is bound to the `mypackage.models` module directly)

In `visit_ImportFrom`:
- `from mypackage.models import Base` →
  `full_modules["Base"] = "mypackage.models.Base"` (FQN of what `Base` is bound to)
- `from mypackage.models import Base as B` →
  `full_modules["B"] = "mypackage.models.Base"` (alias resolves to same FQN)
- `from mypackage import models` →
  `full_modules["models"] = "mypackage.models"` (FQN of what `models` is bound to)
- `from .models import Base` (level=1, module="models") →
  `relative_imports["Base"] = RelativeImportInfo(level=1, module="models", name="Base")`
- `from ..core import Mixin` (level=2, module="core") →
  `relative_imports["Mixin"] = RelativeImportInfo(level=2, module="core", name="Mixin")`
- `from . import utils` (level=1, module=None) →
  `relative_imports["utils"] = RelativeImportInfo(level=1, module=None, name="utils")`

### 3b. FQN resolution for absolute imports

Add a method `resolve_fqn(base_name: str) -> str | None` to `ImportTracker`
(or as a standalone function).

Since `full_modules` stores the FQN of what each local name is bound to,
resolution is a simple formula:

```
FQN(base) = full_modules[root_name] + tail_after_root
```

Where `root_name` is the first segment of the resolved base name (from
`_resolve_base()`) and `tail_after_root` is everything after it (empty
string for bare names, `".attr"` for dotted access).

**Resolution examples:**

- `Base` (ast.Name) where `full_modules["Base"] = "mypackage.models.Base"`
  → FQN = `"mypackage.models.Base"` (direct lookup, no construction needed)
- `m.Base` (ast.Attribute) where `full_modules["m"] = "mypackage.models"`
  → root = `"m"`, tail = `".Base"`
  → FQN = `"mypackage.models" + ".Base"` = `"mypackage.models.Base"`
- `mypackage.models.Base` (ast.Attribute, un-aliased `import mypackage.models`)
  where `full_modules["mypackage"] = "mypackage"`
  → root = `"mypackage"`, tail = `".models.Base"`
  → FQN = `"mypackage" + ".models.Base"` = `"mypackage.models.Base"`
- Same-file class with no import → root not in `full_modules`,
  returns bare name `"Base"` (no FQN available)
- Unresolvable / dynamic base → returns `None`

**Note:** `original_names` is NOT needed for FQN resolution since
`full_modules` already stores the complete binding FQN. The
`original_names` dict is preserved for backward compatibility with
existing `classify()` and `ABCPurityVisitor` logic.

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

- `full_modules` stores the FQN of what the local name is bound to:
  - `from mypackage.models import Base` → `full_modules["Base"] = "mypackage.models.Base"`
  - `from mypackage.models import Base as B` → `full_modules["B"] = "mypackage.models.Base"`
  - `from mypackage import models` → `full_modules["models"] = "mypackage.models"`
  - `import mypackage.models` → `full_modules["mypackage"] = "mypackage"`
  - `import mypackage.models as m` → `full_modules["m"] = "mypackage.models"`
- `relative_imports` populated correctly:
  - `from .models import Base` → `RelativeImportInfo(level=1, module="models", name="Base")`
  - `from ..core.models import Base` → `RelativeImportInfo(level=2, module="core.models", name="Base")`
  - `from . import utils` → `RelativeImportInfo(level=1, module=None, name="utils")`
  - `from ... import deep` → `RelativeImportInfo(level=3, module=None, name="deep")`
- Existing `imports` and `original_names` dicts unchanged (regression tests)

**Test cases for FQN resolution (`resolve_fqn`):**

- `from mypackage.models import Base` → base `Base` resolves to
  `"mypackage.models.Base"` (direct lookup from `full_modules`)
- `from mypackage.models import Base as B` → base `B` resolves to
  `"mypackage.models.Base"` (alias, same direct lookup)
- `from mypackage import models` → base `models.Base` resolves to
  `"mypackage.models" + ".Base"` = `"mypackage.models.Base"`
- `import mypackage.models` → base `mypackage.models.Base` resolves to
  `"mypackage" + ".models.Base"` = `"mypackage.models.Base"`
- `import mypackage.models as m` → base `m.Base` resolves to
  `"mypackage.models" + ".Base"` = `"mypackage.models.Base"`
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
name matches a whitelist entry is silently skipped (no error emitted). For
relative imports where confirmation is not possible, emit INH001 with a hint
when there is a suffix match against a whitelist entry.

**Implementation details:**

- `InheritanceChecker.run()` converts the `_inh001_whitelisted_bases` tuple
  to a `frozenset` for O(1) lookups, then passes it along with
  `_project_packages` to `InheritanceVisitor` (or to a filtering step)
- Before recording an INH001 error, resolve the base to its fully qualified
  name and check membership in the whitelist set
- O(1) lookup via frozenset membership test (converted from the stored tuple)
- If the base is whitelisted, skip it; otherwise, report as before

**Three-way decision for relative imports:**

When a base is from a relative import and the whitelist is non-empty:

1. **Plausible match confirmed** (via `--project-packages` + suffix + depth):
   suppress the error entirely (Ticket 7 logic)
2. **Suffix matches a whitelist entry but can't confirm** (because
   `--project-packages` is not configured or under-specified): emit
   `INH001_HINT` instead of plain `INH001`, naming the matching entry
   and suggesting the user configure `--project-packages`
3. **No suffix match at all**: emit plain `INH001` as usual

The "suffix match" check for the hint case is simpler than plausible matching:
given `RelativeImportInfo(level=1, module="models", name="Base")`, build
suffix `"models.Base"` and check if any whitelist entry ends with
`".models.Base"` or equals `"models.Base"`. This requires no
`--project-packages` knowledge — it's a pure string suffix check. The hint
is only emitted when this suffix matches but full plausible matching failed
(either because `--project-packages` is empty or the prefix check didn't
pass).

**Acceptance criteria:**

- [ ] Whitelisted bases (exact FQN match) produce no INH001 error
- [ ] Non-whitelisted bases still produce INH001 as before
- [ ] Whitelist has no effect on INH002
- [ ] Mixed bases (some whitelisted, some not) correctly report only the
      non-whitelisted violations
- [ ] Empty whitelist preserves existing behavior exactly (no hints emitted)
- [ ] Relative import with suffix match + missing `--project-packages` →
      emits `INH001_HINT` with the matching entry name
- [ ] Relative import with suffix match + `--project-packages` configured
      but entry has wrong prefix → emits plain `INH001` (the project-packages
      is set, the entry just doesn't match this project — it's genuinely
      not whitelisted)
- [ ] Relative import with no suffix match → emits plain `INH001`
- [ ] When multiple whitelist entries suffix-match, the hint names the first
      (or most specific) match

**Complexity:** Medium

---

## Ticket 6 — Write whitelist integration tests (TDD)

**Description:**
Write end-to-end tests that exercise the full whitelist flow from option
parsing through AST analysis, including the hint behavior for relative
imports.

**Test cases — absolute imports (exact FQN matching):**

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

**Test cases — relative imports with hint behavior:**

- `from .models import Base` + whitelist `"mypackage.models.Base"` +
  NO `--project-packages`: emits `INH001` **with hint** mentioning
  `"mypackage.models.Base"` and suggesting `--project-packages`
- `from .models import Base` + whitelist `"mypackage.models.Base"` +
  `--project-packages=mypackage`: emits **no error** (plausible match,
  handled by Ticket 7)
- `from .models import Base` + whitelist `"otherpackage.utils.Thing"` +
  NO `--project-packages`: emits plain `INH001` (no suffix match at all)
- `from .models import Base` + whitelist `"mypackage.models.Base"` +
  `--project-packages=otherpkg` (configured but wrong prefix): emits
  plain `INH001` (project-packages IS set, entry just doesn't match)
- `from .models import Base` + empty whitelist: emits plain `INH001`
  (no hint when whitelist is empty)
- Hint message contains the matching whitelist entry name
- Hint message is suppressible with `# noqa: INH001`

**Acceptance criteria:**

- [ ] All test cases written and initially failing
- [ ] Tests cover both `InheritanceVisitor` directly and via
      `InheritanceChecker.run()`
- [ ] Tests verify exact error message text for hint vs plain INH001
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
3. **Structural validity**: The whitelist entry has enough segments to
   contain both the project package root and the full suffix (i.e., the
   entry is not malformed)

**Worked examples:**

```python
# --project-packages=mypackage

# Example 1: from .models import Base  (level=1, module="models")
# Suffix = "models.Base"
# Whitelist entry "mypackage.models.Base":
#   ✓ starts with "mypackage"
#   ✓ ends with "models.Base"
#   ✓ structural: entry has 3 segments, suffix has 2, pkg root has 1 →
#     middle_count = 3 - 1 - 2 = 0 ≥ 0, so structurally valid
#   → PLAUSIBLE MATCH

# Example 2: from ..core.models import Base  (level=2, module="core.models")
# Suffix = "core.models.Base"
# Whitelist entry "mypackage.core.models.Base":
#   ✓ starts with "mypackage"
#   ✓ ends with "core.models.Base"
#   ✓ structural: 4 segments total, suffix=3, pkg root=1 →
#     middle_count = 4 - 1 - 3 = 0 ≥ 0, structurally valid
#     (level=2 is stored but not used for filtering — we lack the
#     current file's package depth to validate it)
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
#   ✓ structurally valid (middle_count = 4 - 1 - 2 = 1 ≥ 0)
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

    # Check if whitelist entry ends with the suffix at a dot boundary.
    # Bare endswith() would let "othermodels.Base" match suffix "models.Base".
    if not (
        whitelist_entry.endswith(suffix)
        and (whitelist_entry == suffix or whitelist_entry[-(len(suffix) + 1)] == ".")
    ):
        return False

    # Check if whitelist entry starts with a project package
    entry_root = whitelist_entry.split(".")[0]
    if entry_root not in project_packages:
        return False

    # Structural validity: the entry must have enough segments to
    # contain the project package root + the suffix. The "middle"
    # segments between root and suffix must be ≥ 0.
    entry_parts = whitelist_entry.split(".")
    suffix_parts = suffix.split(".")
    # middle_count = total_parts - 1 (pkg root) - len(suffix_parts)
    middle_count = len(entry_parts) - 1 - len(suffix_parts)
    if middle_count < 0:
        return False

    # NOTE: rel_info.level is stored but NOT used for filtering here.
    # To use it, we'd need to know the current file's depth within the
    # package tree (e.g., mypackage/sub/mod.py is depth 2). Without
    # that, we cannot validate whether the level is consistent with
    # the middle_count. The level is preserved for potential future
    # tightening if flake8 exposes file path information.
    return True
```

**Three-outcome decision flow for relative imports:**

When a relative import base would normally trigger INH001 and the whitelist
is non-empty, the following logic runs:

```python
def check_relative_import_against_whitelist(
    rel_info: RelativeImportInfo,
    whitelist: frozenset[str],
    project_packages: tuple[str, ...],
) -> Literal["suppress", "hint", "flag"]:
    """Determine how to handle a relative import base vs the whitelist.

    Returns:
        "suppress" — plausible match confirmed, emit no error
        "hint"     — suffix matches but can't confirm, emit INH001 with hint
        "flag"     — no match at all, emit plain INH001
    """
    # First, check if any whitelist entry is a plausible match
    # (is_plausible_whitelist_match already enforces dot-boundary suffix
    # matching, project package prefix, and structural validity)
    if project_packages:
        for entry in whitelist:
            if is_plausible_whitelist_match(rel_info, entry, project_packages):
                return "suppress"

    # No plausible match found (or project_packages not configured).
    # Check if any entry has a suffix match — if so, we can hint.
    # Build the suffix from the relative import.
    if rel_info.module:
        suffix = f"{rel_info.module}.{rel_info.name}"
    else:
        suffix = rel_info.name

    suffix_matches = [
        entry for entry in whitelist
        if entry.endswith(suffix)
        and (entry == suffix or entry[-(len(suffix) + 1)] == ".")
    ]

    if not suffix_matches:
        return "flag"  # No suffix match at all → plain INH001

    if not project_packages:
        # Suffix matches exist but we can't verify the prefix.
        # Emit INH001 with a hint naming the matching entry.
        return "hint"

    # project_packages IS configured and no plausible match found.
    # The entry prefix doesn't match any project package, or the
    # entry is structurally invalid. Flag plainly — the user has
    # configured project-packages, so the tool has done its best.
    return "flag"
```

**Key design decisions:**

- **False positives are acceptable**: If `from .models import Base` plausibly
  matches both `mypackage.models.Base` and `mypackage.sub.models.Base` in the
  whitelist, we accept the match. The user has explicitly whitelisted these
  names, so a plausible match is treated as intentional.
- **No `--project-packages` + suffix match = hint, not silence**: When we
  can't confirm a match, we still flag the violation but give the user
  actionable guidance: "this might be whitelisted entry X — configure
  `--project-packages` to let us verify." This is better than silently
  flagging (user doesn't understand why their whitelist didn't work) and
  better than silently suppressing (false negatives).
- **`--project-packages` configured + no plausible match = plain INH001**:
  The user has given us enough info to check and the check failed. No hint
  needed — the entry genuinely doesn't match.
- **Level is stored but not used for filtering**: Without knowing the current
  file's depth in the package tree, we cannot validate whether `level` is
  consistent with `middle_count`. We store it for future tightening if flake8
  exposes file path information, or if we add a `--source-root` option.
- **Hint names the specific whitelist entry**: When multiple entries
  suffix-match, the hint names the most specific (shortest) one. If a user
  sees `"may match whitelisted entry 'mypackage.models.Base'"` they know
  exactly which config entry is relevant.

**Acceptance criteria:**

- [ ] `is_plausible_whitelist_match()` implemented as a pure function
- [ ] `check_relative_import_against_whitelist()` returns `"suppress"`,
      `"hint"`, or `"flag"`
- [ ] Suffix matching works for single-segment and multi-segment module paths
- [ ] Project package prefix is verified against `--project-packages`
- [ ] Structural validity check rejects malformed entries (middle_count < 0)
- [ ] No `--project-packages` + suffix match → `"hint"` (not `"flag"`)
- [ ] `--project-packages` configured + no plausible match → `"flag"`
- [ ] `from . import X` (no module) handled correctly (suffix is just `X`)
- [ ] Multiple project packages all checked (any match = plausible)
- [ ] Suffix match check is exact at segment boundaries (e.g., `"odels.Base"`
      does NOT match suffix `"models.Base"`)
- [ ] ADR documenting the three-outcome decision created in `doc/adr/`
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

**Unit tests for `check_relative_import_against_whitelist()`:**

- Suffix matches + no project_packages → returns `"hint"`
- Suffix matches + project_packages configured + plausible → returns `"suppress"`
- Suffix matches + project_packages configured + no plausible match (wrong
  prefix) → returns `"flag"`
- No suffix match at all → returns `"flag"` regardless of project_packages
- Empty whitelist → returns `"flag"` (vacuously no suffix match)
- Multiple suffix matches, one plausible → returns `"suppress"`
- Multiple suffix matches, none plausible, no project_packages → returns
  `"hint"` (hint names the most specific match)

**End-to-end integration tests:**

- Code with `from .models import Base` + `class Child(Base):`
  + whitelist `"mypackage.models.Base"` + `--project-packages=mypackage`
  → no INH001 (suppressed)
- Same code without `--project-packages` → INH001 **with hint** mentioning
  `"mypackage.models.Base"` and `--project-packages`
- Same code with whitelist entry that doesn't suffix-match → plain INH001
  (no hint)
- Same code with `--project-packages=otherpkg` → plain INH001 (project
  packages configured, just doesn't match this entry's prefix)
- Mixed: class with one whitelisted relative base and one non-whitelisted
  → only the non-whitelisted one flagged
- Hint message text verified: contains the matching entry name and the
  `--project-packages` suggestion
- `# noqa: INH001` suppresses both plain and hint variants

**Acceptance criteria:**

- [ ] Unit tests for `is_plausible_whitelist_match()` written and failing
- [ ] Unit tests for `check_relative_import_against_whitelist()` written
      and failing
- [ ] Integration tests covering all three outcomes (suppress/hint/flag)
      written and failing
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
- Section on relative imports explaining the three outcomes:
  1. With `--project-packages`: plausible matches are automatically suppressed
  2. Without `--project-packages`: a helpful hint tells you the base *might*
     match a whitelisted entry and suggests configuring `--project-packages`
  3. No suffix match: plain INH001 as usual
- Example showing the hint message and how to resolve it
- Example showing a whitelisted base producing no error

**Acceptance criteria:**

- [ ] README updated with option reference and examples
- [ ] README documents the hint behavior for relative imports
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
    prefix + suffix match + structural validity
  - `--project-packages` is required for relative import whitelist matching
- Consequences:
  - Users must know the fully qualified name of whitelisted bases
  - Relative imports can be matched when `--project-packages` is configured
  - Plausible matching may produce false positives when different subpackages
    have identically-named modules and classes (accepted trade-off)
  - Without `--project-packages`, relative imports that suffix-match a
    whitelist entry produce INH001 with a helpful hint (not silent, not
    opaque — the user knows exactly what to do)
  - The three-outcome model (suppress / hint / flag) provides graduated
    feedback based on how much configuration the user has provided

**Acceptance criteria:**

- [ ] ADR created via `decree new "..."` in `doc/adr/`
- [ ] ADR documents the fully qualified name requirement
- [ ] ADR documents the plausible suffix matching algorithm for relative imports
- [ ] ADR documents the `--project-packages` requirement for relative matching
- [ ] ADR documents the accepted false positive trade-off
- [ ] ADR documents the three-outcome model (suppress / hint / flag) and the
      rationale for providing actionable hints instead of silent failures

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
3. **Dot level** → stored for future tightening (not currently used for
   filtering since we lack the file's package depth, but preserved for
   when flake8 exposes file paths or a `--source-root` option is added)
