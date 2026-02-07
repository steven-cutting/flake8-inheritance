# 9: Use uv for project and dependency management

Date: 2026-02-07
Status: Accepted

## Context

The project needs a fast, reproducible workflow for managing dependencies and tools.

## Decision

Use uv for project and dependency management.

## Consequences

- Dependency resolution and tool installs use uv's workflow.
- Team members standardize on uv for development tasks.
- Documentation must reflect uv commands.

## Alternatives considered

- Using pip/pip-tools for dependency management.
