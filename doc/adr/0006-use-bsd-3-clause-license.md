# 6: Use BSD-3-Clause license

Date: 2026-02-07
Status: Accepted

## Context

The plugin will be published as open-source on PyPI. The license choice affects
adoption and contribution. BSD-3-Clause is permissive, well-understood,
compatible with virtually all downstream uses, and is the license used by the
`decree` project. It does not impose copyleft obligations, which makes it
easier for companies to adopt the plugin in proprietary CI pipelines.

## Decision

We will license flake8-inheritance under the BSD-3-Clause license, consistent
with the decree project.

## Consequences

The license file must be included in the repository root. The `license` field
in `pyproject.toml` must be `"BSD-3-Clause"`. The PyPI classifier must be
`"License :: OSI Approved :: BSD License"`.
