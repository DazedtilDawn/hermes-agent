from __future__ import annotations

import json
from pathlib import Path

from governance.collectors.burn_intelligence import collect
from governance.controller.config import build_config


def _write_snapshot(path: Path, payload: dict):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding='utf-8')


def test_burn_intelligence_detects_churn_without_recovery(governance_root):
    config = build_config(governance_root)
    burn_dir = governance_root / 'reports' / 'burn-attribution'
    burn_dir.mkdir(parents=True, exist_ok=True)

    _write_snapshot(burn_dir / 'a.json', {
        'artifact_id': 'a',
        'provider_composites': {'codex': 40.0, 'claude': 20.0},
        'routing_churn': {'recent_swap_count': 2},
        'lane_burn_insights': [],
        'codexbar_usage': {'providers': {'codex': {'primary_used_percent': 61}, 'claude': {'primary_used_percent': 12}}},
        'protected_lane_downgrades': [],
    })
    _write_snapshot(burn_dir / 'b.json', {
        'artifact_id': 'b',
        'provider_composites': {'codex': 48.0, 'claude': 18.0},
        'routing_churn': {'recent_swap_count': 4},
        'lane_burn_insights': [{'agent': 'crons', 'suggestion': 'downgrade_candidate', 'provider': 'codex'}],
        'codexbar_usage': {'providers': {'codex': {'primary_used_percent': 66}, 'claude': {'primary_used_percent': 15}}},
        'protected_lane_downgrades': [],
    })

    payload = collect(config, ledger_dir=burn_dir)
    assert payload['churn_without_recovery'] is True
    assert any(rec['kind'] == 'investigate_churn' for rec in payload['recommendations'])
    assert any(rec['kind'] == 'codex_pressure_relief' for rec in payload['recommendations'])


def test_burn_intelligence_detects_recurring_lane_candidates(governance_root):
    config = build_config(governance_root)
    burn_dir = governance_root / 'reports' / 'burn-attribution'
    burn_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(3):
        _write_snapshot(burn_dir / f'{idx}.json', {
            'artifact_id': str(idx),
            'provider_composites': {'codex': 30.0},
            'routing_churn': {'recent_swap_count': 0},
            'lane_burn_insights': [{'agent': 'herald', 'suggestion': 'review_for_cost_efficiency', 'provider': 'claude'}],
            'codexbar_usage': {'providers': {'claude': {'primary_used_percent': 20}}},
            'protected_lane_downgrades': [],
        })

    payload = collect(config, ledger_dir=burn_dir)
    assert payload['recurring_lane_candidates'][0]['agent'] == 'herald'
    assert any(rec['kind'] == 'recurring_lane_candidate' for rec in payload['recommendations'])
