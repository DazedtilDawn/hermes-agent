from __future__ import annotations

import json
import subprocess
from typing import Any


class CommandError(RuntimeError):
    pass


def run_json_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    stdout = (result.stdout or '').strip()
    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout).strip()
        raise CommandError(f"Command failed ({result.returncode}): {' '.join(command)} :: {stderr}")
    return json.loads(result.stdout)
