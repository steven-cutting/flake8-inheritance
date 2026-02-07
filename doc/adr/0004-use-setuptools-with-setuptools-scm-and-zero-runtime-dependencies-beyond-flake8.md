# 4: Use setuptools with setuptools-scm and zero runtime dependencies beyond flake8

Date: 2026-02-07
Status: Accepted

## Context

The plugin needs a build system, a version management strategy, and a dependency policy. `setuptools` is the most widely used build backend and has mature support for entry points. `setuptools-scm` derives versions from git tags, eliminating hardcoded version strings and ensuring published packages always correspond to tagged commits. For runtime dependencies, minimalism is a hallmark of well-maintained flake8 plugins — `flake8-bugbear`, the most respected plugin in the ecosystem, depends only on `flake8` and uses stdlib-only logic. Additional runtime dependencies increase the attack surface and risk version conflicts in user environments.

## Decision

We will use `setuptools>=77` as the build backend with `setuptools-scm>=8` for version derivation. The only runtime dependency will be `flake8>=6.0`. All core plugin logic will use only the Python standard library (`ast`, `sys`, `dataclasses`, `importlib.metadata`). Development and test dependencies are declared in `[project.optional-dependencies]` and are not required at runtime.

## Consequences

Versions are derived from git tags — there must never be a hardcoded version string in the source tree. Releases require `git tag vX.Y.Z` before building. The plugin can be installed in any environment where flake8 runs with no additional dependencies to resolve.
