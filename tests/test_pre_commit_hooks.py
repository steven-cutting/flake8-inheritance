import importlib
from pathlib import Path
from typing import Any, cast


def test_pre_commit_hooks_yaml_has_required_hook_definition() -> None:
    hooks_file = Path(".pre-commit-hooks.yaml")

    assert hooks_file.exists()

    yaml_module = cast(Any, importlib.import_module("yaml"))
    hooks = yaml_module.safe_load(hooks_file.read_text(encoding="utf-8"))

    assert isinstance(hooks, list)
    assert hooks

    hook = next((entry for entry in hooks if entry.get("id") == "flake8-inheritance"), None)
    assert hook is not None

    assert hook["name"] == "flake8-inheritance"
    assert hook["entry"] == "flake8 --select=INH"
    assert hook["language"] == "python"
    assert hook["types"] == ["python"]
    assert hook["additional_dependencies"] == ["flake8>=6"]
