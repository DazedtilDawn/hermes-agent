from __future__ import annotations

import json
from pathlib import Path

from governance.controller import main as gov_main
from governance.controller.config import build_config


def _patch_runtime(monkeypatch, governance_root: Path, *, health: dict, errors: dict, stale: dict, sent: list[str], usage: dict | None = None):
    config = build_config(governance_root)
    monkeypatch.setattr(gov_main, 'build_config', lambda: config)
    monkeypatch.setattr(gov_main, 'collect_health_check', lambda: health)
    monkeypatch.setattr(gov_main, 'collect_error_summary', lambda _health: errors)
    monkeypatch.setattr(gov_main, 'collect_stale_jobs', lambda _health: stale)
    monkeypatch.setattr(gov_main, 'collect_usage_governance', lambda _config: usage or {
        'collector': 'usage_governance',
        'routing_mode': 'CRUISE',
        'provider_modes': {},
        'provider_composites': {},
        'codexbar_usage': {'providers': {}},
        'provider_pressure_watch': {'providers_over_70_pct': [], 'high_pressure_detected': False},
        'lane_burn_insights': [],
        'protected_lane_downgrades': [],
        'premium_low_value_assignments': [],
        'routing_churn': {'swap_window_minutes': 60, 'recent_swap_count': 0, 'high_churn': False, 'churn_agents': []},
        'ineffective_deficit_mitigation': {'detected': False, 'reason': 'test_default'},
    })

    def _sender_builder(_target: str):
        def _sender(_ignored: str, message: str):
            sent.append(message)
            return {'ok': True}
        return _sender

    monkeypatch.setattr(gov_main, '_build_send_message_sender', _sender_builder)
    monkeypatch.setattr(gov_main, '_process_optimization_approvals', lambda _config, _target, _state: [])
    return config


def test_shadow_runner_emits_gateway_alert_and_persists_state(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': False,
            'gateway_error': 'timeout',
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5)
    assert rc == 0
    assert len(sent) == 1
    assert 'gateway unreachable' in sent[0]
    assert any(config.incidents_dir.glob('*.json'))
    assert any(config.verifications_dir.glob('*.json'))
    assert (config.controller_decisions_dir / 'openclaw_shadow_state.json').exists()


def test_shadow_runner_is_silent_when_no_new_conditions(monkeypatch, governance_root, capsys):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': True,
            'gateway_error': None,
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )
    state_path = config.controller_decisions_dir / 'openclaw_shadow_state.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"gateway_alert_active": false, "task_failures_total": 2, "stale_jobs_alert_active": false}', encoding='utf-8')

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == '[SILENT]'
    assert sent == []


def test_shadow_runner_dedupes_repeat_gateway_alert(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': False,
            'gateway_error': 'timeout',
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )
    state_path = config.controller_decisions_dir / 'openclaw_shadow_state.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"gateway_alert_active": true, "task_failures_total": 2, "stale_jobs_alert_active": false}', encoding='utf-8')

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5)
    assert rc == 0
    assert sent == []
    incidents = list(config.incidents_dir.glob('*.json'))
    assert incidents == []


def test_shadow_runner_emits_stale_jobs_observation(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 4, 'active': 0, 'byStatus': {'failed': 3, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': True,
            'gateway_error': None,
        },
        errors={'collector': 'error_summary', 'task_failures_total': 4, 'task_failed': 3, 'task_timed_out': 1, 'task_active': 0},
        stale={'collector': 'stale_jobs', 'task_active': 0, 'task_failures_total': 4, 'task_timed_out': 1, 'stale_jobs_suspected': True},
        sent=sent,
    )
    state_path = config.controller_decisions_dir / 'openclaw_shadow_state.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"gateway_alert_active": false, "task_failures_total": 4, "stale_jobs_alert_active": false}', encoding='utf-8')

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=10)
    assert rc == 0
    assert len(sent) == 1
    assert 'stale jobs suspected' in sent[0]
    assert any(config.incidents_dir.glob('*.json'))


def test_class1_restart_executes_when_enabled_and_post_check_recovers(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': False,
            'gateway_error': 'timeout',
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )
    followup = {'collector': 'health_check', 'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}}, 'gateway_probe': {}, 'gateway_reachable': True, 'gateway_error': None}
    health_calls = {'count': 0}

    def health_fn():
        health_calls['count'] += 1
        return followup if health_calls['count'] > 1 else {
            'collector': 'health_check', 'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}}, 'gateway_probe': {}, 'gateway_reachable': False, 'gateway_error': 'timeout'
        }

    monkeypatch.setattr(gov_main, 'collect_health_check', health_fn)
    restarted = []
    monkeypatch.setattr(gov_main, '_restart_gateway_service', lambda: restarted.append('restart'))

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5, enable_class1_restart=True, restart_cooldown_sec=1800)
    assert rc == 0
    assert restarted == ['restart']
    assert any('restart attempt succeeded' in msg for msg in sent)
    assert any(config.executions_dir.glob('*.json'))


def test_class1_restart_respects_cooldown(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': False,
            'gateway_error': 'timeout',
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )
    state_path = config.controller_decisions_dir / 'openclaw_shadow_state.json'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        'gateway_alert_active': False,
        'task_failures_total': 2,
        'stale_jobs_alert_active': False,
        'last_gateway_restart_at': '2026-04-02T23:30:00Z'
    }), encoding='utf-8')
    restarted = []
    monkeypatch.setattr(gov_main, '_restart_gateway_service', lambda: restarted.append('restart'))
    monkeypatch.setattr(gov_main, 'utc_now', lambda: '2026-04-02T23:40:00Z')

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5, enable_class1_restart=True, restart_cooldown_sec=1800)
    assert rc == 0
    assert restarted == []
    assert any('blocked by cooldown' in msg for msg in sent)
    assert list(config.executions_dir.glob('*.json')) == []


def test_class1_restart_records_blocked_when_post_check_fails(monkeypatch, governance_root):
    sent: list[str] = []
    config = _patch_runtime(
        monkeypatch,
        governance_root,
        health={
            'collector': 'health_check',
            'status': {'tasks': {'failures': 2, 'active': 1, 'byStatus': {'failed': 1, 'timed_out': 1}}},
            'gateway_probe': {},
            'gateway_reachable': False,
            'gateway_error': 'timeout',
        },
        errors={'collector': 'error_summary', 'task_failures_total': 2, 'task_failed': 1, 'task_timed_out': 1, 'task_active': 1},
        stale={'collector': 'stale_jobs', 'task_active': 1, 'task_failures_total': 2, 'task_timed_out': 1, 'stale_jobs_suspected': False},
        sent=sent,
    )
    monkeypatch.setattr(gov_main, '_restart_gateway_service', lambda: None)

    rc = gov_main.run_shadow_openclaw('discord:#approvals', failure_delta_threshold=5, enable_class1_restart=True, restart_cooldown_sec=1800)
    assert rc == 0
    assert any('did not restore gateway reachability' in msg for msg in sent)
    execution_files = list(config.executions_dir.glob('*.json'))
    assert len(execution_files) == 1
    payload = json.loads(execution_files[0].read_text(encoding='utf-8'))
    assert payload['execution_status'] == 'blocked'
