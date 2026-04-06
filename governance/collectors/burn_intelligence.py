from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance.controller.config import GovernanceConfig, build_config


DEFAULT_LEDGER_DIRNAME = 'burn-attribution'


def collect(config: GovernanceConfig | None = None, *, ledger_dir: Path | None = None) -> dict[str, Any]:
    cfg = config or build_config()
    burn_dir = ledger_dir or (cfg.root_dir / 'reports' / DEFAULT_LEDGER_DIRNAME)
    snapshots = _load_snapshots(burn_dir)
    if not snapshots:
        return {
            'collector': 'burn_intelligence',
            'snapshot_count': 0,
            'pressure_deltas': {},
            'churn_without_recovery': False,
            'recurring_lane_candidates': [],
            'recommendations': [],
        }

    latest = snapshots[-1]
    previous = snapshots[-2] if len(snapshots) > 1 else None
    pressure_deltas = _pressure_deltas(previous, latest)
    churn_without_recovery = _churn_without_recovery(previous, latest)
    recurring_lane_candidates = _recurring_lane_candidates(snapshots)
    recommendations = _recommendations(latest, pressure_deltas, churn_without_recovery, recurring_lane_candidates)

    return {
        'collector': 'burn_intelligence',
        'snapshot_count': len(snapshots),
        'latest_snapshot_id': latest.get('artifact_id'),
        'pressure_deltas': pressure_deltas,
        'churn_without_recovery': churn_without_recovery,
        'recurring_lane_candidates': recurring_lane_candidates,
        'recommendations': recommendations,
    }


def _load_snapshots(burn_dir: Path) -> list[dict[str, Any]]:
    if not burn_dir.exists():
        return []
    snapshots = []
    for path in sorted(burn_dir.glob('*.json')):
        try:
            snapshots.append(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            continue
    return snapshots


def _pressure_deltas(previous: dict[str, Any] | None, latest: dict[str, Any]) -> dict[str, float]:
    latest_comp = latest.get('provider_composites', {}) or {}
    prev_comp = (previous or {}).get('provider_composites', {}) or {}
    deltas: dict[str, float] = {}
    for provider in sorted(set(latest_comp) | set(prev_comp)):
        latest_v = float(latest_comp.get(provider, 0) or 0)
        prev_v = float(prev_comp.get(provider, 0) or 0)
        deltas[provider] = round(latest_v - prev_v, 2)
    return deltas


def _churn_without_recovery(previous: dict[str, Any] | None, latest: dict[str, Any]) -> bool:
    if previous is None:
        return False
    prev_churn = ((previous.get('routing_churn') or {}).get('recent_swap_count') or 0)
    latest_churn = ((latest.get('routing_churn') or {}).get('recent_swap_count') or 0)
    if latest_churn <= 0:
        return False
    prev_comp = (previous.get('provider_composites') or {})
    latest_comp = (latest.get('provider_composites') or {})
    if not latest_comp:
        return False
    prev_peak = max(float(v or 0) for v in prev_comp.values()) if prev_comp else 0.0
    latest_peak = max(float(v or 0) for v in latest_comp.values()) if latest_comp else 0.0
    return latest_churn >= prev_churn and latest_peak >= prev_peak


def _recurring_lane_candidates(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for snap in snapshots[-12:]:
        for item in snap.get('lane_burn_insights', []) or []:
            agent = item.get('agent')
            suggestion = item.get('suggestion')
            if not agent or not suggestion:
                continue
            key = (agent, suggestion)
            counts[key] = counts.get(key, 0) + 1
    out = [
        {'agent': agent, 'suggestion': suggestion, 'count': count}
        for (agent, suggestion), count in counts.items()
        if count >= 2
    ]
    out.sort(key=lambda x: (-x['count'], x['agent'], x['suggestion']))
    return out


def _recommendations(
    latest: dict[str, Any],
    pressure_deltas: dict[str, float],
    churn_without_recovery: bool,
    recurring_lane_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    usage = latest.get('codexbar_usage', {}).get('providers', {})
    lane_insights = latest.get('lane_burn_insights', []) or []
    protected = latest.get('protected_lane_downgrades', []) or []

    for item in protected:
        recs.append({
            'priority': 'high',
            'kind': 'protect_quality_lane',
            'summary': f"Protected lane {item['agent']} is downgraded below policy allowance.",
        })

    if churn_without_recovery:
        recs.append({
            'priority': 'high',
            'kind': 'investigate_churn',
            'summary': 'Routing churn is occurring without observable pressure recovery. Investigate process waste before more swaps.',
        })

    codex_primary = ((usage.get('codex') or {}).get('primary_used_percent'))
    if codex_primary is not None and float(codex_primary) >= 60:
        hot = [item['agent'] for item in lane_insights if item.get('provider') == 'codex']
        if hot:
            recs.append({
                'priority': 'high',
                'kind': 'codex_pressure_relief',
                'summary': f"Codex primary usage is elevated; review low-value codex lanes first: {', '.join(sorted(hot))}.",
            })

    for item in recurring_lane_candidates[:3]:
        recs.append({
            'priority': 'medium',
            'kind': 'recurring_lane_candidate',
            'summary': f"Lane {item['agent']} repeatedly appears as {item['suggestion']}; consider a durable routing policy rather than ad hoc swaps.",
        })

    for provider, delta in pressure_deltas.items():
        if delta >= 8:
            recs.append({
                'priority': 'medium',
                'kind': 'rising_pressure',
                'summary': f"Provider {provider} composite pressure rose by {delta:.2f} points since the previous snapshot.",
            })

    return recs
