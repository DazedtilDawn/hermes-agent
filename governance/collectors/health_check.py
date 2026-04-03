from __future__ import annotations

from governance.controller.runtime_wrappers import run_json_command


OPENCLAW_BIN = '/opt/homebrew/bin/openclaw'


def collect() -> dict:
    status = run_json_command([OPENCLAW_BIN, 'status', '--json'], timeout=45)
    probe = run_json_command([OPENCLAW_BIN, 'gateway', 'probe', '--json'], timeout=45)
    probe_target = None
    for target in probe.get('targets', []):
        if target.get('id') == 'localLoopback':
            probe_target = target
            break
    return {
        'collector': 'health_check',
        'status': status,
        'gateway_probe': probe,
        'gateway_reachable': bool(probe_target and probe_target.get('connect', {}).get('ok')),
        'gateway_error': None if probe_target is None else probe_target.get('connect', {}).get('error'),
    }
