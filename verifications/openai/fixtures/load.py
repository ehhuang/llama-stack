from pathlib import Path

import yaml


def load_test_cases(name: str):
    fixture_dir = Path(__file__).parent / "test_cases"
    yaml_path = fixture_dir / f"{name}.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)
