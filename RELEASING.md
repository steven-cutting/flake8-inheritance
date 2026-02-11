# Release Guide

This document describes how to create and publish a new release of
flake8-inheritance to PyPI.

## Overview

Releases are automated through GitHub Actions. When you create a GitHub
release (either through the web UI or CLI), the workflow automatically:

1. Builds the package using `uv build` (version is determined from the git tag via `setuptools_scm`)
2. Publishes to PyPI using trusted publishing (no API tokens required)
3. Creates distribution artifacts attached to the release

**Important:** This project uses `setuptools_scm` for versioning, which means
the package version is automatically derived from git tags. The git tag you
create becomes the published version.

## Prerequisites

Before creating a release, ensure you have:

- [ ] Maintainer access to the GitHub repository
- [ ] All changes merged to the main branch
- [ ] Tests passing on the main branch (check CI status)

## Pre-release Checklist

1. **Determine the version number**:

   This project uses `setuptools_scm`, which automatically derives the version
   from git tags. You don't need to manually update version numbers in code.
   
   Follow [Semantic Versioning](https://semver.org/) when choosing the tag:
   - **Major** (X.0.0): breaking changes
   - **Minor** (0.Y.0): new features, backward compatible
   - **Patch** (0.0.Z): bug fixes, backward compatible

2. **Update CHANGELOG.md**:

   - Move changes from `[Unreleased]` to a new `[X.Y.Z] - YYYY-MM-DD` section
   - Use categories: Added, Changed, Deprecated, Removed, Fixed, Security
   - Keep the `[Unreleased]` section at the top for future changes

3. **Commit and push changelog changes**:

   ```bash
   git add CHANGELOG.md
   git commit -m "Prepare release X.Y.Z"
   git push origin main
   ```

4. **Wait for CI to pass** on the main branch:

   Check the [Actions tab](https://github.com/steven-cutting/flake8-inheritance/actions)
   to ensure all tests pass before proceeding.

## Release Methods

Choose either the GitHub UI workflow (easier) or the CLI workflow (faster for
experienced users).

### Method 1: GitHub UI Workflow

1. **Navigate to the Releases page**:

   Go to https://github.com/steven-cutting/flake8-inheritance/releases

2. **Click "Draft a new release"**

3. **Create a new tag**:

   - Click "Choose a tag"
   - Type the version with `v` prefix: `vX.Y.Z` (e.g., `v0.2.0`)
   - Click "Create new tag: vX.Y.Z on publish"

4. **Set the release title**:

   Use the format: `vX.Y.Z` (same as the tag)

5. **Write release notes**:

   Copy the relevant section from CHANGELOG.md. Example:

   ```markdown
   ## Added

   - New feature description
   - Another new feature

   ## Fixed

   - Bug fix description
   ```

6. **Verify target branch**:

   Ensure "Target: main" is selected

7. **Publish the release**:

   - For pre-releases: check "Set as a pre-release"
   - For stable releases: check "Set as the latest release"
   - Click "Publish release"

8. **Monitor the workflow**:

   The publish workflow will start automatically. Monitor it at:
   https://github.com/steven-cutting/flake8-inheritance/actions/workflows/publish.yml

### Method 2: CLI Workflow (using `gh`)

Requires the [GitHub CLI](https://cli.github.com/) installed and authenticated.

1. **Create the release** with notes from CHANGELOG.md:

   ```bash
   # Extract release notes from CHANGELOG.md for the version
   VERSION="X.Y.Z"
   
   # Create release with notes
   gh release create "v${VERSION}" \
     --title "v${VERSION}" \
     --notes "$(sed -n '/^## \['"${VERSION}"'\]/,/^## \[/p' CHANGELOG.md | sed '$d')"
   ```

   Or with a simplified one-liner (replace X.Y.Z with your version):

   ```bash
   gh release create v0.2.0 --title "v0.2.0" --notes-file - <<< "$(sed -n '/^## \[0.2.0\]/,/^## \[/p' CHANGELOG.md | sed '$d')"
   ```

2. **Monitor the workflow**:

   ```bash
   gh run watch
   ```

   Or view all runs:

   ```bash
   gh run list --workflow=publish.yml
   ```

## Post-release Verification

After the workflow completes successfully:

1. **Verify PyPI publication**:

   Check https://pypi.org/project/flake8-inheritance/ to ensure the new
   version appears

2. **Test installation**:

   ```bash
   # In a fresh virtual environment
   python -m venv /tmp/test-install
   source /tmp/test-install/bin/activate
   pip install flake8-inheritance==X.Y.Z
   flake8 --version  # Should show flake8-inheritance: X.Y.Z
   deactivate
   ```

3. **Verify GitHub Release**:

   - Check that the release appears at
     https://github.com/steven-cutting/flake8-inheritance/releases
   - Verify that distribution artifacts are attached (`.tar.gz` and `.whl`)

## Manual Publishing (Emergency Only)

If the automated workflow fails and manual intervention is required:

1. **Build the package locally**:

   ```bash
   uv build
   ```

2. **Verify the build**:

   ```bash
   ls -lh dist/
   # Should show: flake8_inheritance-X.Y.Z.tar.gz and flake8_inheritance-X.Y.Z-py3-none-any.whl
   ```

3. **Publish using `twine`** (requires PyPI credentials):

   ```bash
   uv run twine upload dist/*
   ```

   **Note:** This method requires PyPI API tokens. The automated workflow uses
   trusted publishing, which is the recommended approach.

## Troubleshooting

### CI Tests Failing

**Problem:** Tests fail on the main branch before release.

**Solution:** Do not create a release until CI is green. Fix failing tests first.

### Workflow Fails to Publish

**Problem:** The `pypi-publish` job fails in GitHub Actions.

**Solution:**

1. Check the workflow logs for the specific error
2. Common causes:
   - Version already exists on PyPI (you cannot republish the same version)
   - PyPI trusted publishing not configured correctly
   - Build artifacts not generated properly

### Wrong Version Published

**Problem:** You published the wrong version to PyPI.

**Solution:**

- You cannot delete or replace a version on PyPI
- Create a new patch release with the correct changes
- Document the mistake in CHANGELOG.md under the new version

### Tag Already Exists

**Problem:** Trying to create a tag that already exists.

**Solution:**

```bash
# Delete the local tag
git tag -d vX.Y.Z

# Delete the remote tag (if it was pushed)
git push origin :refs/tags/vX.Y.Z

# Delete the GitHub release if it was created
gh release delete vX.Y.Z --yes

# Now create the correct release
```

## Version Numbering Guidelines

- **0.Y.Z** (pre-1.0): API is not yet stable
  - Breaking changes can be made in minor versions
  - Reserve for the first stable release: 1.0.0

- **1.Y.Z** (post-1.0): API is stable
  - Major version for breaking changes
  - Minor version for backward-compatible features
  - Patch version for backward-compatible bug fixes

## Related Documentation

- [CHANGELOG.md](./CHANGELOG.md) — Version history
- [CONTRIBUTING.md](./CONTRIBUTING.md) — Development workflow
- [.github/workflows/publish.yml](./.github/workflows/publish.yml) — Automation implementation
