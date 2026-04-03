from __future__ import annotations

from governance.collectors.optimization_review_digest import collect


def test_optimization_review_digest_prioritizes_protected_lane_and_repeated_cause():
    usage = {
        'protected_lane_downgrades': [{'agent': 'praxis', 'current_mode': 'CRUISE'}],
    }
    burn = {
        'recommendations': [{'priority': 'high', 'kind': 'investigate_churn', 'summary': 'Investigate churn.'}],
    }
    causes = {
        'hypotheses': [{'kind': 'retry_or_timeout_waste', 'why': 'Timeouts high.'}],
    }
    lane_memory = {
        'repeated_burn_causes': [{'kind': 'retry_or_timeout_waste', 'count': 3}],
        'durable_lane_candidates': [{'agent': 'herald', 'suggestion': 'review_for_cost_efficiency', 'count': 3}],
    }

    payload = collect(usage, burn, causes, lane_memory)
    assert payload['digest_item_count'] >= 2
    assert payload['digest_items'][0]['kind'] == 'protected_lane_risk'
    assert any(item['kind'] == 'repeated_burn_cause' for item in payload['digest_items'])
