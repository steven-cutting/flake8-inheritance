# 11: Decision on off_by_default for INH checker

Date: 2026-02-11
Status: Accepted

## Context

Flake8 loads installed plugins automatically, but plugins can choose whether
rules are active by default. The INH ruleset is opinionated and can produce a
large first-run findings set on existing codebases. We need to decide if users
should explicitly opt in when they are ready, or if rules should start running
as soon as the package is installed.

## Decision

Set `InheritanceChecker.off_by_default = True`.

This keeps the plugin discoverable via installation while requiring explicit
activation with Flake8's extension-enabling mechanism.

Users must enable the checker with:

```bash
flake8 --enable-extensions=INH
```

Equivalent configuration can be added in Flake8 config files:

```ini
[flake8]
enable-extensions = INH
```

## Consequences

- Installing `flake8-inheritance` no longer changes lint output unless the
  project explicitly enables `INH` extensions.
- Adoption is safer for existing codebases and better aligned with common
  patterns for opt-in Flake8 plugins.
- Documentation must clearly call out `--enable-extensions=INH` in quickstart
  and configuration examples.

## Alternatives considered

- Keep plugin on by default: rejected because it introduces immediate behavior
  changes on install and can be noisy for teams that have not planned rollout.
