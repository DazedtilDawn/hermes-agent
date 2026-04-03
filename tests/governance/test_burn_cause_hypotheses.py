from __future__ import annotations

from governance.collectors.burn_cause_hypotheses import collect


def test_burn_cause_hypotheses_detects_churn_without_recovery():
    usage = {
        'routing_churn': {'high_churn': True},
        'ineffective_deficit_mitigation': {'detected': True},
        'premium_low_value_assignments': [],
        'provider_pressure_watch': {'high_pressure_detected': False},
    }
    burn = {'recommendations': [{'kind': 'investigate_churn'}]}
    errors = {'task_timed_out': 0, 'task_failures_total': 0}

    payload = collect(usage, burn, errors=errors)
    assert payload['hypotheses'][0]['kind'] == 'routing_churn_without_headroom_recovery'


def test_burn_cause_hypotheses_detects_low_value_premium_burn():
    usage = {
        'routing_churn': {'high_churn': False},
        'ineffective_deficit_mitigation': {'detected': False},
        'premium_low_value_assignments': [{'agent': 'crons', 'model': 'openai-codex/gpt-5.4'}],
        'provider_pressure_watch': {'high_pressure_detected': True},
    }
    burn = {'recommendations': []}
    errors = {'task_timed_out': 0, 'task_failures_total': 0}

    payload = collect(usage, burn, errors=errors)
    assert any(h['kind'] == 'low_value_premium_burn' for h in payload['hypotheses'])


def test_burn_cause_hypotheses_detects_retry_or_timeout_waste():
    usage = {
        'routing_churn': {'high_churn': False},
        'ineffective_deficit_mitigation': {'detected': False},
        'premium_low_value_assignments': [],
        'provider_pressure_watch': {'high_pressure_detected': False},
    }
    burn = {'recommendations': []}
    errors = {'task_timed_out': 12, 'task_failures_total': 55}

    payload = collect(usage, burn, errors=errors)
    assert any(h['kind'] == 'retry_or_timeout_waste' for h in payload['hypotheses'])
