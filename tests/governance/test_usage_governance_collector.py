from __future__ import annotations

import json
from pathlib import Path

from governance.collectors.usage_governance import collect
from governance.controller.config import build_config


def _write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding='utf-8')


def _write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding='utf-8')


def test_usage_governance_detects_protected_lane_downgrade(governance_root):
    config = build_config(governance_root)
    routing_file = governance_root / 'fixtures' / 'routing.json'
    swap_file = governance_root / 'fixtures' / 'swap.jsonl'
    history_file = governance_root / 'fixtures' / 'history.jsonl'
    routing_file.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        routing_file,
        {
            'profile': 'CRUISE',
            'routing': {
                'axiom': 'openai-codex/gpt-5.4-mini',
                'praxis': 'zai/glm-5.1',
                'crons': 'minimax-portal/MiniMax-M2.7',
            },
            '_headroom': {'headroom_v2': {'mode': 'CRUISE', 'provider_modes': {'codex': 'CRUISE'}, 'composites': {'codex': 44.0, 'zai': 22.0}}},
        },
    )
    _write_jsonl(swap_file, [])
    _write_jsonl(history_file, [])

    payload = collect(
        config,
        routing_file=routing_file,
        swap_log_file=swap_file,
        headroom_history_file=history_file,
        codexbar_payload={'providers': {'codex': {'primary_used_percent': 11}, 'zai': {'primary_used_percent': 23}}},
    )
    assert len(payload['protected_lane_downgrades']) == 1
    assert payload['protected_lane_downgrades'][0]['agent'] == 'axiom'


def test_usage_governance_detects_routing_churn(governance_root):
    config = build_config(governance_root)
    routing_file = governance_root / 'fixtures' / 'routing.json'
    swap_file = governance_root / 'fixtures' / 'swap.jsonl'
    history_file = governance_root / 'fixtures' / 'history.jsonl'
    routing_file.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        routing_file,
        {
            'profile': 'CRUISE',
            'routing': {'scout': 'openai-codex/gpt-5.4', 'crons': 'minimax-portal/MiniMax-M2.7'},
            '_headroom': {'headroom_v2': {'mode': 'CRUISE', 'provider_modes': {'codex': 'CRUISE'}, 'composites': {'codex': 41.0, 'zai': 20.0}}},
        },
    )
    _write_jsonl(
        swap_file,
        [
            {'event': 'routing_swap', 'agent': 'scout', 'ts': '2026-04-03T03:00:00Z'},
            {'event': 'routing_swap', 'agent': 'scout', 'ts': '2026-04-03T03:10:00Z'},
            {'event': 'routing_swap', 'agent': 'forge', 'ts': '2026-04-03T03:20:00Z'},
            {'event': 'routing_swap', 'agent': 'forge', 'ts': '2026-04-03T03:30:00Z'},
        ],
    )
    _write_jsonl(history_file, [])

    payload = collect(
        config,
        routing_file=routing_file,
        swap_log_file=swap_file,
        headroom_history_file=history_file,
        codexbar_payload={'providers': {'codex': {'primary_used_percent': 11}, 'zai': {'primary_used_percent': 23}}},
    )
    assert payload['routing_churn']['high_churn'] is True
    assert {entry['agent'] for entry in payload['routing_churn']['churn_agents']} == {'scout', 'forge'}


def test_usage_governance_detects_ineffective_deficit_mitigation(governance_root):
    config = build_config(governance_root)
    routing_file = governance_root / 'fixtures' / 'routing.json'
    swap_file = governance_root / 'fixtures' / 'swap.jsonl'
    history_file = governance_root / 'fixtures' / 'history.jsonl'
    routing_file.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        routing_file,
        {
            'profile': 'PROTECT',
            'routing': {'praxis': 'openai-codex/gpt-5.4-mini', 'crons': 'zai/glm-5.1'},
            '_headroom': {'headroom_v2': {'mode': 'PROTECT', 'provider_modes': {'codex': 'PROTECT'}, 'composites': {'codex': 72.0, 'zai': 50.0}}},
        },
    )
    _write_jsonl(swap_file, [])
    _write_jsonl(
        history_file,
        [
            {'ts': '2026-04-03T03:00:00Z', 'mode': 'PROTECT', 'primary_pressure': 70.0},
            {'ts': '2026-04-03T03:15:00Z', 'mode': 'PROTECT', 'primary_pressure': 71.0},
            {'ts': '2026-04-03T03:30:00Z', 'mode': 'PROTECT', 'primary_pressure': 72.0},
            {'ts': '2026-04-03T03:45:00Z', 'mode': 'PROTECT', 'primary_pressure': 73.0},
        ],
    )

    payload = collect(
        config,
        routing_file=routing_file,
        swap_log_file=swap_file,
        headroom_history_file=history_file,
        codexbar_payload={'providers': {'codex': {'primary_used_percent': 73}, 'zai': {'primary_used_percent': 52}}},
    )
    assert payload['ineffective_deficit_mitigation']['detected'] is True
    assert payload['provider_pressure_watch']['high_pressure_detected'] is True


def test_usage_governance_detects_premium_low_value_assignment(governance_root):
    config = build_config(governance_root)
    routing_file = governance_root / 'fixtures' / 'routing.json'
    swap_file = governance_root / 'fixtures' / 'swap.jsonl'
    history_file = governance_root / 'fixtures' / 'history.jsonl'
    routing_file.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        routing_file,
        {
            'profile': 'CRUISE',
            'routing': {'crons': 'openai-codex/gpt-5.4', 'batch': 'minimax-portal/MiniMax-M2.7'},
            '_headroom': {'headroom_v2': {'mode': 'CRUISE', 'provider_modes': {'codex': 'CRUISE'}, 'composites': {'codex': 40.0, 'zai': 10.0}}},
        },
    )
    _write_jsonl(swap_file, [])
    _write_jsonl(history_file, [])

    payload = collect(
        config,
        routing_file=routing_file,
        swap_log_file=swap_file,
        headroom_history_file=history_file,
        codexbar_payload={'providers': {'codex': {'primary_used_percent': 68}, 'zai': {'primary_used_percent': 21}}},
    )
    assert payload['premium_low_value_assignments'] == [{'agent': 'crons', 'model': 'openai-codex/gpt-5.4'}]
    assert payload['lane_burn_insights'][0]['agent'] == 'crons'
    assert payload['lane_burn_insights'][0]['suggestion'] == 'downgrade_candidate'
