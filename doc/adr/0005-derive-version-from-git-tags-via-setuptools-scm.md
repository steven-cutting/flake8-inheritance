# 5: Derive version from git tags via setuptools-scm

Date: 2026-02-07
Status: Accepted

## Context

Hardcoded version strings in source code create a maintenance burden and a category of release errors — forgetting to bump the version, or bumping it inconsistently across files. The plugin's version appears in `flake8 --version` output, so it must be accurate. `setuptools-scm` derives the version from git tags at build time, and `importlib.metadata.version()` reads it at runtime from the installed package metadata.

## Decision

We will use `setuptools-scm` for version derivation with `dynamic = ["version"]` in `pyproject.toml`. The checker class will read the version at import time via `importlib.metadata.version("flake8-inheritance")`. There will be no hardcoded version string anywhere in the source tree.

## Consequences

Every release requires a git tag (`vX.Y.Z`) before building. Development installs show a dev version with the git hash. CI must use `fetch-depth: 0` when checking out the repository so that setuptools-scm can read the full tag history.
