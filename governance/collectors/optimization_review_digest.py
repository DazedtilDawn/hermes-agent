from __future__ import annotations

from typing import Any


def collect(usage: dict[str, Any], burn: dict[str, Any], causes: dict[str, Any], lane_memory: dict[str, Any]) -> dict[str, Any]:
    protected = usage.get('protected_lane_downgrades', []) or []
    repeated_causes = lane_memory.get('repeated_burn_causes', []) or []
    durable_lanes = lane_memory.get('durable_lane_candidates', []) or []
    burn_recommendations = burn.get('recommendations', []) or []
    cause_hypotheses = causes.get('hypotheses', []) or []

    digest_items: list[dict[str, Any]] = []

    for item in protected[:3]:
        digest_items.append({
            'priority': 'high',
            'kind': 'protected_lane_risk',
            'summary': f"Protected lane {item['agent']} is below its preferred quality floor in mode {item.get('current_mode', 'unknown')}.",
        })

    for cause in repeated_causes[:3]:
        digest_items.append({
            'priority': 'high' if cause['kind'] in {'retry_or_timeout_waste', 'quality_floor_risk'} else 'medium',
            'kind': 'repeated_burn_cause',
            'summary': f"Burn cause {cause['kind']} has repeated {cause['count']} times.",
        })

    for lane in durable_lanes[:3]:
        digest_items.append({
            'priority': 'medium',
            'kind': 'durable_lane_candidate',
            'summary': f"Lane {lane['agent']} repeatedly appears as {lane['suggestion']} ({lane['count']} snapshots).",
        })

    if not digest_items and burn_recommendations:
        top = burn_recommendations[0]
        digest_items.append({
            'priority': top.get('priority', 'medium'),
            'kind': top.get('kind', 'burn_recommendation'),
            'summary': top.get('summary', 'Optimization recommendation available.'),
        })

    if not digest_items and cause_hypotheses:
        top = cause_hypotheses[0]
        digest_items.append({
            'priority': top.get('confidence', 'medium'),
            'kind': top.get('kind', 'burn_cause_hypothesis'),
            'summary': top.get('why', 'Cause hypothesis available.'),
        })

    return {
        'collector': 'optimization_review_digest',
        'digest_item_count': len(digest_items),
        'digest_items': digest_items,
    }
