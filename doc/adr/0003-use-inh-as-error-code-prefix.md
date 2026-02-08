# 3: Use INH as error code prefix

Date: 2026-02-07
Status: Accepted

## Context

Flake8 error codes consist of 1–3 uppercase letters followed by 1–3 digits. The
letter prefix acts as a namespace, and the entry point name must be a prefix of
all error codes the plugin produces. Single-letter prefixes have historically
caused conflicts. The prefix must be unique across all published flake8
plugins. A search of the awesome-flake8-extensions list and PyPI found no
existing plugin using the `INH` prefix.

## Decision

We will use `INH` as the error code prefix. The flake8 entry point will be
registered as `INH`. Error codes will be `INH001`, `INH002`, etc. Error code
ranges are reserved: INH0xx for inheritance restrictions, INH1xx for ABC
purity (INH002 retains its number for simplicity in v1), INH2xx reserved for
future use.

## Consequences

All error codes must begin with `INH`. The entry point in `pyproject.toml` must
be `INH = "flake8_inheritance.checker:InheritanceChecker"`. If a prefix
collision is discovered before first release, all codes and the entry point
must be renamed.
