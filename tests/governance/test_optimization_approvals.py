from __future__ import annotations

import json
from pathlib import Path

from governance.controller.config import build_config
from governance.controller.optimization_approvals import parse_approval_commands, apply_proposal_command, is_proposal_snoozed
from governance.controller.optimization_proposals import persist_proposal_artifact


def test_parse_approval_commands_reads_text_replies():
    messages = [
        {'id': '100', 'content': 'APPROVE optimization_proposal_test.json', 'author': {'bot': False}},
        {'id': '101', 'content': 'ALT optimization_proposal_test.json minimax-portal/MiniMax-M2.7', 'author': {'bot': False}},
        {'id': '102', 'content': 'SNOOZE optimization_proposal_test.json 45', 'author': {'bot': False}},
        {'id': '103', 'content': 'REJECT optimization_proposal_test.json', 'author': {'bot': False}},
    ]
    commands = parse_approval_commands(messages)
    assert [c['action'] for c in commands] == ['approve', 'alt', 'snooze', 'reject'][::-1]


def test_apply_proposal_command_updates_routing_file(governance_root, monkeypatch, tmp_path):
    config = build_config(governance_root)
    proposals = {
        'mode': 'PROTECT',
        'approval_required': True,
        'auto_apply_allowed': False,
        'max_lane_changes': 1,
        'proposals': [
            {
                'agent': 'crons',
                'current_model': 'openai-codex/gpt-5.4',
                'recommended_model': 'openai-codex/gpt-5.4-mini',
                'alternative_models': ['minimax-portal/MiniMax-M2.7'],
                'rollback_model': 'openai-codex/gpt-5.4',
                'reason': 'downgrade_candidate',
                'requires_explicit_owner': False,
            }
        ],
        'supporting_recommendations': [],
        'supporting_digest_items': [],
    }
    artifact = persist_proposal_artifact(proposals, config=config)
    routing_file = tmp_path / 'model-routing.json'
    routing_file.write_text(json.dumps({'routing': {'crons': 'openai-codex/gpt-5.4'}}, indent=2), encoding='utf-8')
    import governance.controller.optimization_approvals as approvals
    monkeypatch.setattr(approvals, 'ROUTING_FILE', routing_file)

    result = apply_proposal_command({'action': 'approve', 'artifact': artifact.name, 'message_id': '999'}, config=config)
    assert result['ok'] is True
    payload = json.loads(routing_file.read_text(encoding='utf-8'))
    assert payload['routing']['crons'] == 'openai-codex/gpt-5.4-mini'

    rollback = apply_proposal_command({'action': 'rollback', 'artifact': artifact.name, 'message_id': '1000'}, config=config)
    assert rollback['ok'] is True
    payload = json.loads(routing_file.read_text(encoding='utf-8'))
    assert payload['routing']['crons'] == 'openai-codex/gpt-5.4'

    snooze = apply_proposal_command({'action': 'snooze', 'artifact': artifact.name, 'message_id': '1001', 'minutes': 30}, config=config)
    assert snooze['status'] == 'snoozed'
    assert is_proposal_snoozed(artifact.name, config=config) is True
