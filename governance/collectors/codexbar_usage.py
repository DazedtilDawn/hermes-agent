from __future__ import annotations

import json
import subprocess
from typing import Any

CODEXBAR_BIN = 'codexbar'
TRACKED_PROVIDERS = ('codex', 'minimax', 'cursor', 'zai')


def collect() -> dict[str, Any]:
    result = subprocess.run(
        [CODEXBAR_BIN, 'usage', '--provider', 'all', '--json'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    payload = _parse_codexbar_output(result.stdout)
    providers: dict[str, Any] = {}
    for entry in payload:
        provider = entry.get('provider')
        if provider not in TRACKED_PROVIDERS:
            continue
        usage = entry.get('usage') or {}
        primary = usage.get('primary') or {}
        secondary = usage.get('secondary') or {}
        tertiary = usage.get('tertiary') or {}
        providers[provider] = {
            'source': entry.get('source'),
            'updated_at': usage.get('updatedAt'),
            'primary_used_percent': primary.get('usedPercent'),
            'primary_window_minutes': primary.get('windowMinutes'),
            'secondary_used_percent': secondary.get('usedPercent'),
            'tertiary_used_percent': tertiary.get('usedPercent'),
            'account': usage.get('accountEmail') or usage.get('identity', {}).get('accountEmail'),
        }
    return {
        'collector': 'codexbar_usage',
        'providers': providers,
        'errors_present': any(bool(entry.get('error')) for entry in payload),
    }


def _parse_codexbar_output(stdout: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    arrays = []
    for line in lines:
        if not line.startswith('['):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            arrays.append(value)
    if not arrays:
        return []
    return arrays[0]
