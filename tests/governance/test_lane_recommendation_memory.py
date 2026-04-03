from __future__ import annotations

import json
from pathlib import Path

from governance.collectors.lane_recommendation_memory import collect
from governance.controller.config import build_config


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding='utf-8')


def test_lane_recommendation_memory_detects_durable_lane_candidate(governance_root):
    config = build_config(governance_root)
    burn_dir = governance_root / 'reports' / 'burn-attribution'
    incidents_dir = governance_root / 'reports' / 'incidents'
    burn_dir.mkdir(parents=True, exist_ok=True)
    incidents_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(3):
        _write_json(burn_dir / f'b{idx}.json', {
            'lane_burn_insights': [
                {'agent': 'herald', 'suggestion': 'review_for_cost_efficiency'},
                {'agent': 'crons', 'suggestion': 'downgrade_candidate'},
            ]
        })

    payload = collect(config, burn_dir=burn_dir, incidents_dir=incidents_dir)
    assert any(item['agent'] == 'herald' for item in payload['durable_lane_candidates'])
    assert any(rec['kind'] == 'durable_lane_policy_candidate' for rec in payload['recommendations'])


def test_lane_recommendation_memory_detects_repeated_burn_causes(governance_root):
    config = build_config(governance_root)
    burn_dir = governance_root / 'reports' / 'burn-attribution'
    incidents_dir = governance_root / 'reports' / 'incidents'
    burn_dir.mkdir(parents=True, exist_ok=True)
    incidents_dir.mkdir(parents=True, exist_ok=True)

    _write_json(incidents_dir / 'i1.json', {'title': 'Burn cause hypothesis changed', 'evidence': ['retry_or_timeout_waste']})
    _write_json(incidents_dir / 'i2.json', {'title': 'Burn cause hypothesis changed', 'evidence': ['retry_or_timeout_waste']})

    payload = collect(config, burn_dir=burn_dir, incidents_dir=incidents_dir)
    assert payload['repeated_burn_causes'][0]['kind'] == 'retry_or_timeout_waste'
    assert any(rec['kind'] == 'repeated_burn_cause' for rec in payload['recommendations'])
