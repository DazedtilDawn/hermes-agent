from __future__ import annotations

import json

from governance.controller.config import build_config
from governance.controller.optimization_proposals import (
    persist_proposal_artifact,
    format_approval_request_message,
    build_discord_components,
    _short_artifact_id,
)


def test_persist_optimization_proposal_artifact(governance_root):
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
        'supporting_recommendations': [{'kind': 'codex_pressure_relief', 'summary': 'Codex pressure high.'}],
        'supporting_digest_items': [],
    }
    path = persist_proposal_artifact(proposals, config=config)
    assert path is not None and path.exists()
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['artifact_type'] == 'optimization_proposal'
    assert payload['proposals'][0]['agent'] == 'crons'


def test_format_approval_request_message_is_human_readable(governance_root):
    proposals = {
        'mode': 'EMERGENCY',
        'proposals': [
            {
                'agent': 'scout',
                'current_model': 'anthropic/claude-sonnet-4-6',
                'recommended_model': 'openai-codex/gpt-5.4-mini',
                'alternative_models': ['minimax-portal/MiniMax-M2.7'],
                'reason': 'downgrade_candidate',
                'requires_explicit_owner': True,
                'rollback_model': 'anthropic/claude-sonnet-4-6',
            }
        ],
        'supporting_recommendations': [{'summary': 'Codex primary usage is elevated; review low-value codex lanes first.'}],
        'supporting_digest_items': [],
    }
    msg = format_approval_request_message(proposals)
    assert 'Model Optimization Proposed [EMERGENCY]' in msg
    assert '`scout`' in msg
    assert 'anthropic/claude-sonnet-4-6' in msg
    assert 'gpt-5.4-mini' in msg
    assert 'lighter one would suffice' in msg
    assert 'Rollback target: anthropic/claude-sonnet-4-6' in msg
    assert 'Alternatives: minimax-portal/MiniMax-M2.7' in msg
    assert 'Protected lane' in msg
    assert 'APPROVE' in msg


def test_format_approval_request_message_with_cost_efficiency_reason():
    proposals = {
        'mode': 'CRUISE',
        'proposals': [
            {
                'agent': 'crons',
                'current_model': 'claude-3.5-sonnet',
                'recommended_model': 'codex-mini',
                'reason': 'review_for_cost_efficiency',
            }
        ],
    }
    msg = format_approval_request_message(proposals)
    assert 'cost-effective model' in msg
    assert 'balance load' in msg


def test_format_approval_request_message_with_unknown_reason():
    proposals = {
        'mode': 'PROTECT',
        'proposals': [
            {
                'agent': 'builder',
                'current_model': 'gpt-4',
                'recommended_model': 'gpt-3.5',
                'reason': 'some_custom_reason',
            }
        ],
    }
    msg = format_approval_request_message(proposals)
    assert 'Some custom reason' in msg


def test_build_discord_components_uses_discord_api_format(governance_root):
    config = build_config(governance_root)
    proposals = {
        'mode': 'PROTECT',
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
    components = build_discord_components(proposals, artifact)

    # Should return a list of action rows (Discord API format)
    assert isinstance(components, list)
    assert len(components) >= 1

    # First action row
    first_row = components[0]
    assert first_row['type'] == 1  # ACTION_ROW
    assert 'components' in first_row
    buttons = first_row['components']

    # Should have Approve, Reject, Snooze, Rollback
    assert len(buttons) == 4
    labels = {b['label'] for b in buttons}
    assert 'Approve' in labels
    assert 'Reject' in labels
    assert 'Snooze 30m' in labels
    assert 'Rollback' in labels

    # All buttons should be type 2 with proper styles
    for button in buttons:
        assert button['type'] == 2
        assert 'style' in button
        assert 'custom_id' in button
        assert button['custom_id'].startswith('gov_')

    # Approve button should be style 3 (green), Reject style 4 (red)
    approve_btn = next(b for b in buttons if b['label'] == 'Approve')
    assert approve_btn['style'] == 3
    reject_btn = next(b for b in buttons if b['label'] == 'Reject')
    assert reject_btn['style'] == 4

    # custom_ids should use short artifact ID
    short_id = _short_artifact_id(artifact)
    assert short_id.startswith('optprop-')
    for button in buttons:
        assert short_id in button['custom_id']

    # Second action row: alternative model buttons
    assert len(components) == 2
    alt_row = components[1]
    assert alt_row['type'] == 1
    alt_buttons = alt_row['components']
    assert len(alt_buttons) == 1
    assert 'Alt: MiniMax-M2.7' == alt_buttons[0]['label']
    assert alt_buttons[0]['style'] == 1  # PRIMARY (blurple)


def test_build_discord_components_no_rollback_no_alternatives(governance_root):
    config = build_config(governance_root)
    proposals = {
        'mode': 'PROTECT',
        'proposals': [
            {
                'agent': 'crons',
                'current_model': 'openai-codex/gpt-5.4',
                'recommended_model': 'openai-codex/gpt-5.4-mini',
                'reason': 'downgrade_candidate',
            }
        ],
    }
    artifact = persist_proposal_artifact(proposals, config=config)
    components = build_discord_components(proposals, artifact)

    # Only one action row, 3 buttons (no rollback, no alternatives)
    assert len(components) == 1
    buttons = components[0]['components']
    assert len(buttons) == 3
    labels = {b['label'] for b in buttons}
    assert 'Rollback' not in labels


def test_short_artifact_id_extracts_optprop():
    path = type('Path', (), {'name': '20260403T110200Z_optimization_proposal_optprop-72f4f720a023.json'})()
    assert _short_artifact_id(path) == 'optprop-72f4f720a023'


def test_short_artifact_id_fallback():
    path = type('Path', (), {'name': 'some_other_file.json'})()
    assert _short_artifact_id(path) == 'some_other_file'
