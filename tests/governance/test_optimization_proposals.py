from __future__ import annotations

from governance.collectors.optimization_proposals import collect
from governance.controller.config import build_config


def test_optimization_proposals_are_mode_aware(governance_root):
    config = build_config(governance_root)
    usage = {
        'routing_mode': 'PROTECT',
        'protected_lane_downgrades': [],
        'lane_burn_insights': [
            {
                'agent': 'crons',
                'model': 'openai-codex/gpt-5.4',
                'provider': 'codex',
                'suggestion': 'downgrade_candidate',
            }
        ],
    }
    burn = {'recommendations': [{'kind': 'codex_pressure_relief', 'summary': 'Codex pressure high.'}]}
    digest = {'digest_items': [{'kind': 'durable_lane_candidate', 'summary': 'Lane crons repeatedly appears as downgrade candidate.'}]}

    payload = collect(config, usage, burn, digest)
    assert payload['mode'] == 'PROTECT'
    assert payload['approval_required'] is True
    assert payload['auto_apply_allowed'] is False
    assert payload['proposals'][0]['recommended_model'] == 'openai-codex/gpt-5.4-mini'
    assert payload['proposals'][0]['alternative_models'] == ['minimax-portal/MiniMax-M2.7']


def test_optimization_proposals_mark_protected_lanes(governance_root):
    config = build_config(governance_root)
    usage = {
        'routing_mode': 'EMERGENCY',
        'protected_lane_downgrades': [{'agent': 'praxis'}],
        'lane_burn_insights': [
            {
                'agent': 'praxis',
                'model': 'anthropic/claude-sonnet-4-6',
                'provider': 'claude',
                'suggestion': 'review_for_cost_efficiency',
            }
        ],
    }
    burn = {'recommendations': []}
    digest = {'digest_items': []}

    payload = collect(config, usage, burn, digest)
    assert payload['proposals'][0]['requires_explicit_owner'] is True
