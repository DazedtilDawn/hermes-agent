from pathlib import Path

import yaml


def load_policy(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
