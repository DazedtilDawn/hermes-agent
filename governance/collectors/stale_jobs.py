from __future__ import annotations

from governance.collectors.health_check import collect as collect_health


def collect(status_payload: dict | None = None) -> dict:
    health = status_payload or collect_health()
    tasks = health.get('status', {}).get('tasks', {})
    active = int(tasks.get('active', 0))
    failures = int(tasks.get('failures', 0))
    by_status = tasks.get('byStatus', {})
    timed_out = int(by_status.get('timed_out', 0))
    stale_signal = active == 0 and failures > 0
    return {
        'collector': 'stale_jobs',
        'task_active': active,
        'task_failures_total': failures,
        'task_timed_out': timed_out,
        'stale_jobs_suspected': stale_signal,
    }
