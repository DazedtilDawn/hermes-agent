from __future__ import annotations

from governance.controller import main as gov_main
from governance.controller.config import build_config


def test_shadow_runner_emits_usage_governance_alert(monkeypatch, governance_root):
    config = build_config(governance_root)
    sent: list[str] = []

    monkeypatch.setattr(gov_main, 'build_config', lambda: config)
    monkeypatch.setattr(gov_main, 'collect_health_check', lambda: {
        'collector': 'health_check',
        'status': {'tasks': {'failures': 1, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 0}}},
        'gateway_probe': {},
        'gateway_reachable': True,
        'gateway_error': None,
    })
    monkeypatch.setattr(gov_main, 'collect_error_summary', lambda _health: {
        'collector': 'error_summary', 'task_failures_total': 1, 'task_failed': 1, 'task_timed_out': 0, 'task_active': 1
    })
    monkeypatch.setattr(gov_main, 'collect_stale_jobs', lambda _health: {
        'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 1, 'task_timed_out': 0, 'stale_jobs_suspected': False
    })
    monkeypatch.setattr(gov_main, 'collect_usage_governance', lambda _config: {
        'collector': 'usage_governance',
        'routing_mode': 'CRUISE',
        'provider_modes': {'claude': 'CRUISE'},
        'provider_composites': {'claude': 22.0},
        'codexbar_usage': {'providers': {}},
        'provider_pressure_watch': {'providers_over_70_pct': [], 'high_pressure_detected': False},
        'lane_burn_insights': [],
        'protected_lane_downgrades': [{'agent': 'axiom', 'current_model': 'openai-codex/gpt-5.4-mini'}],
        'premium_low_value_assignments': [],
        'routing_churn': {'swap_window_minutes': 60, 'recent_swap_count': 0, 'high_churn': False, 'churn_agents': []},
        'ineffective_deficit_mitigation': {'detected': False, 'reason': 'test_default'},
    })

    monkeypatch.setattr(gov_main, '_build_send_message_sender', lambda _target: (lambda _ignored, message: sent.append(message) or {'ok': True}))
    monkeypatch.setattr(gov_main, '_process_optimization_approvals', lambda _config, _target, _state: [])

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=10)
    assert rc == 0
    assert len(sent) >= 1
    assert 'protected-quality lane downgrade detected' in sent[0]
    assert any(config.incidents_dir.glob('*.json'))
    assert any((config.root_dir / 'reports' / 'burn-attribution').glob('*.json'))
