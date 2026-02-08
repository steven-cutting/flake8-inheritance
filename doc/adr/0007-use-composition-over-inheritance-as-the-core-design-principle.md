# 7: Use composition-over-inheritance as the core design principle

Date: 2026-02-07
Status: Accepted

## Context

The plugin needs a guiding architectural principle for its internal design and extension
points.

## Decision

Favor composition over inheritance as the core design principle throughout the plugin.

## Consequences

- Components are assembled via small, focused collaborators.
- Subclass hierarchies are minimized to keep behavior explicit and testable.
- Some patterns may require additional wiring code.

## Alternatives considered

- Relying on inheritance hierarchies for extensibility.
