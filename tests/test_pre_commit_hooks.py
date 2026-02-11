from pathlib import Path

import yaml  # type: ignore[import-untyped]


def test_pre_commit_hooks_yaml_has_required_hook_definition() -> None:
    hooks_file = Path('.pre-commit-hooks.yaml')

    assert hooks_file.exists()

    hooks = yaml.safe_load(hooks_file.read_text(encoding='utf-8'))

    assert isinstance(hooks, list)
    assert hooks == [
        {
            'id': 'flake8-inheritance',
            'name': 'flake8-inheritance',
            'entry': 'flake8 --select=INH',
            'language': 'python',
            'types': ['python'],
            'additional_dependencies': ['flake8>=6'],
        }
    ]
