# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-02-11

### Added

- **INH001** rule: flag inheritance from concrete internal classes (same-file,
  relative imports, and project-package imports).
- **INH002** rule: flag concrete (non-abstract) methods in abstract base classes
  (`abc.ABC` / `abc.ABCMeta`).
- `--project-packages` option to declare which top-level packages are internal,
  enabling INH001 detection for absolute imports from your own code.
- `--inh002-allowed-dunders` option to allowlist specific dunder methods as
  concrete implementations in ABCs.
- Pre-commit hook support (`.pre-commit-hooks.yaml`) with hook id
  `flake8-inheritance`.
- Off-by-default plugin; enable with `--enable-extensions=INH`.
- Architecture Decision Records using decree.
- Initial project skeleton with flake8 entry point registration.
