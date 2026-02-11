from pathlib import Path

import yaml


def test_pre_commit_hooks_yaml_has_required_hook_definition() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    hooks_file = repo_root / ".pre-commit-hooks.yaml"

    assert hooks_file.exists()

    hooks = yaml.safe_load(hooks_file.read_text(encoding="utf-8"))

    assert isinstance(hooks, list)
    assert hooks

    hook = next((entry for entry in hooks if entry.get("id") == "flake8-inheritance"), None)
    assert hook is not None

    assert hook["name"] == "flake8-inheritance"
    assert hook["entry"] == "flake8 --select=INH --enable-extensions=INH"
    assert hook["language"] == "python"
    assert hook["types"] == ["python"]
    assert hook["additional_dependencies"] == ["flake8>=6"]
