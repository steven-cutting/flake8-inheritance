#!/usr/bin/env python3
"""Smoke test script for flake8-inheritance plugin.

This script clones well-known open-source projects and runs the
flake8-inheritance plugin against them to validate stability and catch
false positives.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --output results.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SmokeTestConfig:
    """Configuration for a smoke test target."""

    name: str
    repo_url: str
    commit_sha: str | None
    paths_to_test: list[str]


@dataclass
class SmokeTestResult:
    """Results from running smoke test against a project."""

    name: str
    success: bool
    commit_sha: str
    files_analyzed: int
    violations: dict[str, int]
    execution_time: float
    exit_code: int
    errors: list[str]
    stdout: str
    stderr: str


# Define test targets
SMOKE_TEST_TARGETS = [
    SmokeTestConfig(
        name="CPython stdlib",
        repo_url="https://github.com/python/cpython.git",
        commit_sha=None,  # Use latest from default branch
        paths_to_test=["Lib/"],
    ),
    SmokeTestConfig(
        name="requests",
        repo_url="https://github.com/psf/requests.git",
        commit_sha=None,
        paths_to_test=["src/requests/"],
    ),
    SmokeTestConfig(
        name="FastAPI",
        repo_url="https://github.com/tiangolo/fastapi.git",
        commit_sha=None,
        paths_to_test=["fastapi/"],
    ),
]


def clone_repository(config: SmokeTestConfig, temp_dir: Path) -> tuple[Path, str]:
    """Clone a repository to a temporary directory.

    Args:
        config: Smoke test configuration
        temp_dir: Temporary directory to clone into

    Returns:
        Tuple of (clone_path, commit_sha)

    Raises:
        subprocess.CalledProcessError: If git clone fails

    """
    clone_path = temp_dir / config.name.replace(" ", "_")
    clone_path.mkdir(parents=True, exist_ok=True)

    print(f"Cloning {config.name} from {config.repo_url}...")

    # Clone with depth=1 for faster cloning
    subprocess.run(
        ["git", "clone", "--depth=1", config.repo_url, str(clone_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Get the commit SHA
    result = subprocess.run(
        ["git", "-C", str(clone_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = result.stdout.strip()

    print(f"  Cloned at commit {commit_sha[:8]}")

    return clone_path, commit_sha


def count_python_files(paths: list[Path]) -> int:
    """Count Python files in the given paths.

    Args:
        paths: List of paths to search

    Returns:
        Number of Python files found

    """
    count = 0
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            count += 1
        elif path.is_dir():
            count += len(list(path.rglob("*.py")))
    return count


def parse_flake8_output(output: str) -> dict[str, int]:
    """Parse flake8 output to count violations by error code.

    Args:
        output: Raw flake8 output

    Returns:
        Dictionary mapping error codes to counts

    """
    violations: dict[str, int] = {}

    for line in output.splitlines():
        # Flake8 output format: path:line:col: CODE message
        parts = line.split(":")
        if len(parts) >= 4:
            # Extract error code (e.g., "INH001")
            error_part = parts[3].strip()
            if " " in error_part:
                code = error_part.split()[0]
                violations[code] = violations.get(code, 0) + 1

    return violations


def run_smoke_test(config: SmokeTestConfig, temp_dir: Path) -> SmokeTestResult:
    """Run smoke test against a single project.

    Args:
        config: Smoke test configuration
        temp_dir: Temporary directory for cloning

    Returns:
        SmokeTestResult with test outcomes

    """
    errors = []
    stdout = ""
    stderr = ""
    commit_sha = "unknown"
    files_analyzed = 0
    violations: dict[str, int] = {}
    exit_code = -1

    start_time = time.time()

    try:
        # Clone the repository
        clone_path, commit_sha = clone_repository(config, temp_dir)

        # Build full paths to test
        test_paths = [clone_path / path for path in config.paths_to_test]
        existing_paths = [p for p in test_paths if p.exists()]

        if not existing_paths:
            errors.append(f"None of the test paths exist: {config.paths_to_test}")
            execution_time = time.time() - start_time
            return SmokeTestResult(
                name=config.name,
                success=False,
                commit_sha=commit_sha,
                files_analyzed=0,
                violations={},
                execution_time=execution_time,
                exit_code=-1,
                errors=errors,
                stdout="",
                stderr="",
            )

        # Count Python files
        files_analyzed = count_python_files(existing_paths)

        # Run flake8 with the plugin enabled
        print(f"Running flake8 on {config.name} ({files_analyzed} Python files)...")

        # Run flake8 with INH rules enabled
        cmd = [
            "flake8",
            "--enable-extensions=INH",
            "--select=INH",
            *[str(p) for p in existing_paths],
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr

        # Parse violations
        violations = parse_flake8_output(stdout)

        # Check for crashes (exit code > 1 typically indicates an error, not just violations)
        if exit_code > 1:
            errors.append(f"Flake8 exited with code {exit_code}")

        # Check for errors in stderr
        if stderr and "Error" in stderr:
            errors.append(f"Stderr contains errors: {stderr[:200]}")

        success = exit_code <= 1 and not errors

    except subprocess.CalledProcessError as e:
        errors.append(f"Git/subprocess error: {e}")
        if e.stderr:
            errors.append(f"Stderr: {e.stderr[:200]}")
        success = False
    except Exception as e:  # noqa: BLE001
        errors.append(f"Unexpected error: {e!s}")
        success = False

    execution_time = time.time() - start_time

    return SmokeTestResult(
        name=config.name,
        success=success,
        commit_sha=commit_sha,
        files_analyzed=files_analyzed,
        violations=violations,
        execution_time=execution_time,
        exit_code=exit_code,
        errors=errors,
        stdout=stdout[:500],  # Keep first 500 chars for reference
        stderr=stderr[:500],
    )


def format_results_markdown(results: list[SmokeTestResult]) -> str:
    """Format smoke test results as Markdown.

    Args:
        results: List of smoke test results

    Returns:
        Markdown-formatted results

    """
    lines = [
        "# Smoke Test Results",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "## Summary",
        "",
    ]

    total_success = sum(1 for r in results if r.success)
    total_projects = len(results)

    lines.append(
        f"**Overall Status:** {'✅ PASS' if total_success == total_projects else '❌ FAIL'}"
    )
    lines.append(f"**Projects Tested:** {total_projects}")
    lines.append(f"**Successful:** {total_success}")
    lines.append(f"**Failed:** {total_projects - total_success}")
    lines.append("")

    # Per-project results
    lines.append("## Project Results")
    lines.append("")

    for result in results:
        status_icon = "✅" if result.success else "❌"
        lines.append(f"### {status_icon} {result.name}")
        lines.append("")
        lines.append(f"- **Commit SHA:** `{result.commit_sha}`")
        lines.append(f"- **Files Analyzed:** {result.files_analyzed}")
        lines.append(f"- **Exit Code:** {result.exit_code}")
        lines.append(f"- **Execution Time:** {result.execution_time:.2f}s")
        lines.append("")

        if result.violations:
            lines.append("**Violations Found:**")
            lines.append("")
            for code, count in sorted(result.violations.items()):
                lines.append(f"- `{code}`: {count}")
            lines.append("")
        else:
            lines.append("**No violations found.**")
            lines.append("")

        if result.errors:
            lines.append("**Errors/Issues:**")
            lines.append("")
            lines.extend(f"- {error}" for error in result.errors)
            lines.append("")

        if result.stderr and result.errors:
            lines.append("<details>")
            lines.append("<summary>Stderr Output (first 500 chars)</summary>")
            lines.append("")
            lines.append("```")
            lines.append(result.stderr)
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    # Notes section
    lines.append("## Notes")
    lines.append("")
    lines.append("- Exit code 0 = no violations found")
    lines.append("- Exit code 1 = violations found (expected behavior)")
    lines.append("- Exit code > 1 = error/crash (indicates a problem)")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Run smoke tests and generate report.

    Returns:
        Exit code (0 if all tests completed without crashes, 1 otherwise)

    """
    parser = argparse.ArgumentParser(description="Run smoke tests for flake8-inheritance")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("SMOKE_TEST_RESULTS.md"),
        help="Output file for results (default: SMOKE_TEST_RESULTS.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output results as JSON",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Smoke Testing flake8-inheritance Plugin")
    print("=" * 70)
    print()

    # Create temporary directory for cloning
    with tempfile.TemporaryDirectory(prefix="smoke_test_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        print(f"Using temporary directory: {temp_dir}")
        print()

        # Run tests on all targets
        results = []
        for config in SMOKE_TEST_TARGETS:
            print(f"\n{'=' * 70}")
            print(f"Testing: {config.name}")
            print(f"{'=' * 70}")

            result = run_smoke_test(config, temp_dir)
            results.append(result)

            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            print(f"\n{status}: {result.name}")
            print(f"  Files: {result.files_analyzed}")
            print(f"  Time: {result.execution_time:.2f}s")
            if result.violations:
                print(f"  Violations: {sum(result.violations.values())}")
            if result.errors:
                print(f"  Errors: {len(result.errors)}")

    # Generate report
    print()
    print("=" * 70)
    print("Generating Report")
    print("=" * 70)

    markdown_report = format_results_markdown(results)

    # Write markdown report
    args.output.write_text(markdown_report, encoding="utf-8")
    print(f"\n✅ Results written to: {args.output}")

    # Optionally write JSON report
    if args.json:
        json_output = args.output.with_suffix(".json")
        json_data = [
            {
                "name": r.name,
                "success": r.success,
                "commit_sha": r.commit_sha,
                "files_analyzed": r.files_analyzed,
                "violations": r.violations,
                "execution_time": r.execution_time,
                "exit_code": r.exit_code,
                "errors": r.errors,
            }
            for r in results
        ]
        json_output.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        print(f"✅ JSON results written to: {json_output}")

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    all_successful = all(r.success for r in results)
    any_crashes = any(r.exit_code > 1 for r in results)

    total_files = sum(r.files_analyzed for r in results)
    total_violations = sum(sum(r.violations.values()) for r in results)

    print(f"Projects tested: {len(results)}")
    print(f"Total files analyzed: {total_files}")
    print(f"Total violations found: {total_violations}")
    print(f"Any crashes/errors: {'Yes ❌' if any_crashes else 'No ✅'}")

    if all_successful:
        print("\n✅ All smoke tests completed successfully!")
        return 0
    print("\n❌ Some smoke tests failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
