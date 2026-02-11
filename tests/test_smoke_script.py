"""Tests for the smoke test script functionality."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for importing
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from smoke_test import (  # noqa: E402
    SmokeTestResult,
    count_python_files,
    format_results_markdown,
    parse_flake8_output,
)


def test_parse_flake8_output_with_violations() -> None:
    """Test parsing flake8 output with violations."""
    output = """src/example.py:10:5: INH001 Inheritance from internal class is not allowed
src/example.py:20:5: INH002 Abstract base class contains concrete method
src/other.py:15:5: INH001 Inheritance from internal class is not allowed"""

    violations = parse_flake8_output(output)

    assert violations == {"INH001": 2, "INH002": 1}


def test_parse_flake8_output_no_violations() -> None:
    """Test parsing flake8 output with no violations."""
    output = ""
    violations = parse_flake8_output(output)
    assert violations == {}


def test_parse_flake8_output_ignores_non_violation_lines() -> None:
    """Test that non-violation lines are ignored."""
    output = """Some other output
src/example.py:10:5: INH001 Inheritance from internal class is not allowed
Another line without violation"""

    violations = parse_flake8_output(output)
    assert violations == {"INH001": 1}


def test_count_python_files_in_directory(tmp_path: Path) -> None:
    """Test counting Python files in a directory."""
    # Create test files
    (tmp_path / "file1.py").touch()
    (tmp_path / "file2.py").touch()
    (tmp_path / "not_python.txt").touch()

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file3.py").touch()

    count = count_python_files([tmp_path])
    assert count == 3


def test_count_python_files_single_file(tmp_path: Path) -> None:
    """Test counting a single Python file."""
    test_file = tmp_path / "test.py"
    test_file.touch()

    count = count_python_files([test_file])
    assert count == 1


def test_count_python_files_nonexistent_path() -> None:
    """Test counting files with nonexistent path."""
    count = count_python_files([Path("/nonexistent/path")])
    assert count == 0


def test_format_results_markdown_success() -> None:
    """Test formatting successful smoke test results."""
    results = [
        SmokeTestResult(
            name="Test Project",
            success=True,
            commit_sha="abc123def456",
            files_analyzed=100,
            violations={"INH001": 5, "INH002": 3},
            execution_time=12.5,
            exit_code=1,
            errors=[],
            stdout="",
            stderr="",
        )
    ]

    markdown = format_results_markdown(results)

    assert "# Smoke Test Results" in markdown
    assert "Test Project" in markdown
    assert "abc123def456" in markdown
    assert "Files Analyzed:** 100" in markdown
    assert "Exit Code:** 1" in markdown
    assert "12.5" in markdown
    assert "`INH001`: 5" in markdown
    assert "`INH002`: 3" in markdown
    assert "✅ PASS" in markdown


def test_format_results_markdown_with_errors() -> None:
    """Test formatting smoke test results with errors."""
    results = [
        SmokeTestResult(
            name="Failed Project",
            success=False,
            commit_sha="abc123",
            files_analyzed=50,
            violations={},
            execution_time=5.0,
            exit_code=2,
            errors=["Git clone failed", "Network error"],
            stdout="",
            stderr="Error: could not connect",
        )
    ]

    markdown = format_results_markdown(results)

    assert "Failed Project" in markdown
    assert "❌ FAIL" in markdown
    assert "Git clone failed" in markdown
    assert "Network error" in markdown
    assert "Stderr Output" in markdown


def test_format_results_markdown_multiple_projects() -> None:
    """Test formatting results for multiple projects."""
    results = [
        SmokeTestResult(
            name="Project 1",
            success=True,
            commit_sha="abc123",
            files_analyzed=100,
            violations={"INH001": 5},
            execution_time=10.0,
            exit_code=1,
            errors=[],
            stdout="",
            stderr="",
        ),
        SmokeTestResult(
            name="Project 2",
            success=False,
            commit_sha="def456",
            files_analyzed=0,
            violations={},
            execution_time=1.0,
            exit_code=2,
            errors=["Failed to clone"],
            stdout="",
            stderr="",
        ),
    ]

    markdown = format_results_markdown(results)

    assert "Project 1" in markdown
    assert "Project 2" in markdown
    assert "Projects Tested:** 2" in markdown
    assert "Successful:** 1" in markdown
    assert "Failed:** 1" in markdown
