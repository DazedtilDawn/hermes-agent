from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance.controller.config import GovernanceConfig, build_config


def collect(config: GovernanceConfig | None = None, *, burn_dir: Path | None = None, incidents_dir: Path | None = None) -> dict[str, Any]:
    cfg = config or build_config()
    burn_path = burn_dir or (cfg.root_dir / 'reports' / 'burn-attribution')
    incident_path = incidents_dir or cfg.incidents_dir

    burn_snapshots = _load_json_files(burn_path)
    incidents = _load_json_files(incident_path)

    lane_counts: dict[str, dict[str, int]] = {}
    cause_counts: dict[str, int] = {}

    for snap in burn_snapshots[-24:]:
        for item in snap.get('lane_burn_insights', []) or []:
            agent = item.get('agent')
            suggestion = item.get('suggestion')
            if not agent or not suggestion:
                continue
            lane_counts.setdefault(agent, {})
            lane_counts[agent][suggestion] = lane_counts[agent].get(suggestion, 0) + 1

    for incident in incidents[-50:]:
        title = (incident.get('title') or '').lower()
        evidence = incident.get('evidence', []) or []
        text = ' '.join(str(x) for x in evidence).lower() + ' ' + title
        for kind in [
            'retry_or_timeout_waste',
            'routing_churn_without_headroom_recovery',
            'low_value_premium_burn',
            'quality_floor_risk',
            'swap_policy_instability',
        ]:
            if kind in text:
                cause_counts[kind] = cause_counts.get(kind, 0) + 1

    durable_candidates = []
    for agent, suggestions in sorted(lane_counts.items()):
        top_suggestion, top_count = sorted(suggestions.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if top_count >= 2:
            durable_candidates.append({
                'agent': agent,
                'suggestion': top_suggestion,
                'count': top_count,
                'all_suggestions': suggestions,
            })

    repeated_causes = [
        {'kind': kind, 'count': count}
        for kind, count in sorted(cause_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if count >= 2
    ]

    recommendations = []
    for candidate in durable_candidates[:5]:
        recommendations.append({
            'kind': 'durable_lane_policy_candidate',
            'agent': candidate['agent'],
            'summary': f"Lane {candidate['agent']} repeatedly appears as {candidate['suggestion']} across burn snapshots.",
        })
    for cause in repeated_causes[:5]:
        recommendations.append({
            'kind': 'repeated_burn_cause',
            'cause': cause['kind'],
            'summary': f"Burn cause {cause['kind']} has recurred {cause['count']} times and may justify policy or process changes.",
        })

    return {
        'collector': 'lane_recommendation_memory',
        'durable_lane_candidates': durable_candidates,
        'repeated_burn_causes': repeated_causes,
        'recommendations': recommendations,
    }


def _load_json_files(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for file in sorted(path.glob('*.json')):
        try:
            out.append(json.loads(file.read_text(encoding='utf-8')))
        except Exception:
            continue
    return out
