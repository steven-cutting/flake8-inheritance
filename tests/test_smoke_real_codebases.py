"""Smoke tests: run the plugin against real-world open-source codebases.

These tests clone well-known projects into a temporary directory and run
``flake8 --select=INH --enable-extensions=INH`` against them.  The goal is
to verify the plugin completes *without unhandled exceptions* — the
violations themselves are expected (these projects use inheritance heavily).

Every test is marked ``@pytest.mark.slow`` so the default ``pytest`` run
skips them.  Execute with::

    uv run pytest -m slow --timeout 300

Results recorded on 2026-02-11
-------------------------------
* **CPython Lib/** — 3 716 violations (3 620 INH001, 96 INH002), 0 crashes
* **requests src/** — 36 violations (all INH001), 0 crashes
* **FastAPI fastapi/** — 54 violations (all INH001), 0 crashes
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

slow = pytest.mark.slow


def _clone(url: str, dest: Path) -> None:
    subprocess.check_call(  # noqa: S603
        ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],  # noqa: S607
    )


def _run_flake8(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "flake8",
            "--select=INH",
            "--enable-extensions=INH",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@slow
@pytest.mark.timeout(300)
def test_cpython_stdlib(tmp_path: Path) -> None:
    repo = tmp_path / "cpython"
    _clone("https://github.com/python/cpython.git", repo)
    result = _run_flake8(repo / "Lib")
    # Exit code 1 = violations found (expected).  Any other non-zero is a crash.
    assert result.returncode in (0, 1), f"flake8 crashed:\n{result.stderr}"
    assert "Traceback" not in result.stderr


@slow
@pytest.mark.timeout(120)
def test_requests(tmp_path: Path) -> None:
    repo = tmp_path / "requests"
    _clone("https://github.com/psf/requests.git", repo)
    result = _run_flake8(repo / "src")
    assert result.returncode in (0, 1), f"flake8 crashed:\n{result.stderr}"
    assert "Traceback" not in result.stderr


@slow
@pytest.mark.timeout(120)
def test_fastapi(tmp_path: Path) -> None:
    repo = tmp_path / "fastapi"
    _clone("https://github.com/fastapi/fastapi.git", repo)
    result = _run_flake8(repo / "fastapi")
    assert result.returncode in (0, 1), f"flake8 crashed:\n{result.stderr}"
    assert "Traceback" not in result.stderr
