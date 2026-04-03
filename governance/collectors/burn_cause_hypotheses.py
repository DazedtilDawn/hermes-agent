from __future__ import annotations

from typing import Any


def collect(usage: dict[str, Any], burn: dict[str, Any], *, errors: dict[str, Any] | None = None) -> dict[str, Any]:
    hypotheses: list[dict[str, Any]] = []

    churn = usage.get('routing_churn', {})
    ineffective = usage.get('ineffective_deficit_mitigation', {})
    low_value = usage.get('premium_low_value_assignments', [])
    provider_watch = usage.get('provider_pressure_watch', {})
    recommendations = burn.get('recommendations', []) or []
    task_errors = errors or {}

    if churn.get('high_churn') and ineffective.get('detected'):
        hypotheses.append({
            'kind': 'routing_churn_without_headroom_recovery',
            'confidence': 'high',
            'why': 'Routing churn is high and deficit mitigation is still ineffective across the current window.',
            'suggested_action': 'Investigate process waste before adding more routing swaps.',
        })

    if low_value and provider_watch.get('high_pressure_detected'):
        hypotheses.append({
            'kind': 'low_value_premium_burn',
            'confidence': 'high',
            'why': 'Low-value lanes are still attached to premium models while provider pressure is elevated.',
            'suggested_action': 'Downgrade low-value lanes first and preserve protected-quality lanes.',
        })

    if task_errors.get('task_timed_out', 0) >= 10 or task_errors.get('task_failures_total', 0) >= 50:
        hypotheses.append({
            'kind': 'retry_or_timeout_waste',
            'confidence': 'medium',
            'why': 'Task timeout or failure counts are high enough to plausibly consume burn without producing useful work.',
            'suggested_action': 'Inspect retries, cron frequency, and failing work loops before further model downgrades.',
        })

    if any(rec.get('kind') == 'protect_quality_lane' for rec in recommendations):
        hypotheses.append({
            'kind': 'quality_floor_risk',
            'confidence': 'high',
            'why': 'A protected-quality lane appears to be downgraded below policy allowance.',
            'suggested_action': 'Restore the protected lane or require explicit emergency-level justification.',
        })

    if churn.get('high_churn') and not low_value and not provider_watch.get('high_pressure_detected'):
        hypotheses.append({
            'kind': 'swap_policy_instability',
            'confidence': 'medium',
            'why': 'Swap activity is elevated even though low-value premium pressure is not the obvious primary driver.',
            'suggested_action': 'Review routing policy thresholds for over-sensitivity or oscillation.',
        })

    return {
        'collector': 'burn_cause_hypotheses',
        'hypothesis_count': len(hypotheses),
        'hypotheses': hypotheses,
    }
