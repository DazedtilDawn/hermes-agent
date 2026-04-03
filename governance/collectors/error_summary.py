from __future__ import annotations

from governance.collectors.health_check import collect as collect_health


def collect(status_payload: dict | None = None) -> dict:
    health = status_payload or collect_health()
    tasks = health.get('status', {}).get('tasks', {})
    by_status = tasks.get('byStatus', {})
    failures = int(tasks.get('failures', 0))
    failed = int(by_status.get('failed', 0))
    timed_out = int(by_status.get('timed_out', 0))
    return {
        'collector': 'error_summary',
        'task_failures_total': failures,
        'task_failed': failed,
        'task_timed_out': timed_out,
        'task_active': int(tasks.get('active', 0)),
    }
