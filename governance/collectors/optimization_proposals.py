from __future__ import annotations

from typing import Any

from governance.controller.config import GovernanceConfig, build_config
from governance.controller.utils import read_yaml


def collect(config: GovernanceConfig | None, usage: dict[str, Any], burn: dict[str, Any], digest: dict[str, Any]) -> dict[str, Any]:
    cfg = config or build_config()
    policy = read_yaml(cfg.policy_dir / 'optimization-approval-policy.yaml')['optimization_approval']
    mode = (usage.get('routing_mode') or 'CRUISE').lower()
    mode_policy = policy.get(mode, policy['cruise'])
    option_limit = int(policy.get('option_limit', 3))
    downgrade_prefs = policy.get('downgrade_preferences', {})

    protected = usage.get('protected_lane_downgrades', []) or []
    lane_insights = usage.get('lane_burn_insights', []) or []
    recommendations = burn.get('recommendations', []) or []
    digest_items = digest.get('digest_items', []) or []

    # MiniMax models are already cost-effective; never propose them for downgrade.
    _COST_EFFECTIVE_PROVIDERS = {'minimax'}

    proposals = []
    for item in lane_insights:
        agent = item.get('agent')
        provider = item.get('provider') or 'unknown'
        current_model = item.get('model')
        if provider in _COST_EFFECTIVE_PROVIDERS:
            continue
        alternatives = downgrade_prefs.get(provider, [])[:option_limit]
        if not agent or not current_model or not alternatives:
            continue
        proposals.append({
            'agent': agent,
            'current_model': current_model,
            'recommended_model': alternatives[0],
            'alternative_models': alternatives[1:option_limit],
            'provider': provider,
            'reason': item.get('suggestion', 'review_for_cost_efficiency'),
        })

    protected_agents = {item.get('agent') for item in protected}
    filtered = []
    for proposal in proposals:
        if proposal['agent'] in protected_agents and policy.get('protected_lane_always_requires_explicit_owner', True):
            proposal['requires_explicit_owner'] = True
        else:
            proposal['requires_explicit_owner'] = False
        filtered.append(proposal)

    return {
        'collector': 'optimization_proposals',
        'mode': mode.upper(),
        'approval_required': bool(mode_policy.get('approval_required', True)),
        'auto_apply_allowed': bool(mode_policy.get('auto_apply_allowed', False)),
        'max_lane_changes': int(mode_policy.get('max_lane_changes', 1)),
        'allowed_recommendation_kinds': mode_policy.get('allowed_recommendation_kinds', []),
        'supporting_recommendations': recommendations[:5],
        'supporting_digest_items': digest_items[:5],
        'proposals': filtered[: int(mode_policy.get('max_lane_changes', 1))],
    }
