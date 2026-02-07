# 8: Use flake8 AST checker plugin architecture

Date: 2026-02-07
Status: Accepted

## Context

The plugin must integrate with flake8 in a supported and maintainable way.

## Decision

Implement the plugin as a flake8 AST checker plugin.

## Consequences

- The checker receives AST nodes and can report findings with precise locations.
- The implementation aligns with flake8's supported extension points.
- The checker must manage AST traversal and state explicitly.

## Alternatives considered

- Implementing a physical line checker instead of an AST checker.
