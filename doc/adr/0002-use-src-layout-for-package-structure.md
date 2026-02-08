# 2: Use src layout for package structure

Date: 2026-02-07
Status: Accepted

## Context

Flake8 discovers plugins through entry points, which are only available after
installation. If the plugin module is directly importable from the project root
(flat layout), tests can pass by importing the module from the filesystem —
bypassing entry point registration entirely. This means a misconfigured entry
point would be invisible during development and only fail in production. The
Python Packaging Authority recommends the `src` layout for this reason, and it
is the standard used in the `decree` project.

## Decision

We will use the `src` layout with the importable package at
`src/flake8_inheritance/`. All test and development workflows will install the
package (editable install) to exercise entry point registration.

## Consequences

Tests cannot accidentally import uninstalled code. Entry point bugs are caught
during development. The `[tool.setuptools.packages.find]` section in
`pyproject.toml` must specify `where = ["src"]`.
