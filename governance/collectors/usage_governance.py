from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from governance.collectors.codexbar_usage import collect as collect_codexbar_usage
from governance.controller.config import GovernanceConfig, build_config
from governance.controller.utils import read_yaml

ROUTING_FILE = Path('/Users/axiom/clawd/data/model-routing.json')
SWAP_LOG_FILE = Path('/Users/axiom/clawd/data/swap-log.jsonl')
HEADROOM_HISTORY_FILE = Path('/Users/axiom/clawd/data/headroom-history.jsonl')

_MODE_ORDER = {
    'MAXIMIZE': 0,
    'CRUISE': 1,
    'CONSERVE': 2,
    'PROTECT': 3,
    'EMERGENCY': 4,
}


@dataclass(frozen=True)
class RoutingGovernancePolicy:
    protected_quality_lanes: dict[str, dict[str, Any]]
    elastic_lanes: set[str]
    low_value_lanes: set[str]
    premium_models: set[str]
    swap_window_minutes: int
    high_swap_count: int
    repeat_agent_swap_count: int
    ineffective_window_entries: int
    protect_pressure_floor: float
    emergency_pressure_floor: float


def load_policy(config: GovernanceConfig | None = None) -> RoutingGovernancePolicy:
    cfg = config or build_config()
    payload = read_yaml(cfg.policy_dir / 'routing-governance.yaml')['routing_governance']
    churn = payload['churn_thresholds']
    mitigation = payload['mitigation_thresholds']
    return RoutingGovernancePolicy(
        protected_quality_lanes=payload['protected_quality_lanes'],
        elastic_lanes=set(payload['elastic_lanes']),
        low_value_lanes=set(payload['low_value_lanes']),
        premium_models=set(payload['premium_models']),
        swap_window_minutes=int(churn['swap_window_minutes']),
        high_swap_count=int(churn['high_swap_count']),
        repeat_agent_swap_count=int(churn['repeat_agent_swap_count']),
        ineffective_window_entries=int(mitigation['ineffective_window_entries']),
        protect_pressure_floor=float(mitigation['protect_pressure_floor']),
        emergency_pressure_floor=float(mitigation['emergency_pressure_floor']),
    )


def collect(
    config: GovernanceConfig | None = None,
    *,
    routing_file: Path = ROUTING_FILE,
    swap_log_file: Path = SWAP_LOG_FILE,
    headroom_history_file: Path = HEADROOM_HISTORY_FILE,
    codexbar_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = load_policy(config)
    routing = _read_json_file(routing_file)
    swaps = _read_jsonl(swap_log_file)
    history = _read_jsonl(headroom_history_file)
    codexbar = codexbar_payload if codexbar_payload is not None else _safe_collect_codexbar_usage()

    current_mode = routing.get('_headroom', {}).get('headroom_v2', {}).get('mode') or routing.get('profile', 'CRUISE')
    routing_map = routing.get('routing', {})
    provider_modes = routing.get('_headroom', {}).get('headroom_v2', {}).get('provider_modes', {})
    primary_pressure = routing.get('_headroom', {}).get('headroom_v2', {}).get('composites', {})

    protected_lane_downgrades = []
    for agent, rule in policy.protected_quality_lanes.items():
        current_model = routing_map.get(agent)
        preferred = set(rule.get('preferred_models', []))
        minimum_mode = rule.get('minimum_mode_for_downgrade', 'EMERGENCY')
        if current_model and current_model not in preferred and _mode_rank(current_mode) < _mode_rank(minimum_mode):
            protected_lane_downgrades.append({
                'agent': agent,
                'current_model': current_model,
                'preferred_models': sorted(preferred),
                'current_mode': current_mode,
                'minimum_mode_for_downgrade': minimum_mode,
            })

    premium_low_value_assignments = []
    for agent in policy.low_value_lanes:
        current_model = routing_map.get(agent)
        if current_model in policy.premium_models:
            premium_low_value_assignments.append({'agent': agent, 'model': current_model})

    recent_swaps = _recent_swaps(swaps, policy.swap_window_minutes)
    swap_counts = Counter(event.get('agent') for event in recent_swaps if event.get('event') == 'routing_swap')
    churn_agents = [
        {'agent': agent, 'swap_count': count}
        for agent, count in sorted(swap_counts.items())
        if count >= policy.repeat_agent_swap_count
    ]
    routing_churn = {
        'swap_window_minutes': policy.swap_window_minutes,
        'recent_swap_count': sum(swap_counts.values()),
        'high_churn': sum(swap_counts.values()) >= policy.high_swap_count,
        'churn_agents': churn_agents,
    }

    ineffective_mitigation = _ineffective_mitigation(policy, history)
    provider_pressure_watch = _provider_pressure_watch(codexbar)
    lane_burn_insights = _lane_burn_insights(policy, routing_map, codexbar)

    return {
        'collector': 'usage_governance',
        'routing_mode': current_mode,
        'provider_modes': provider_modes,
        'provider_composites': primary_pressure,
        'codexbar_usage': codexbar,
        'provider_pressure_watch': provider_pressure_watch,
        'lane_burn_insights': lane_burn_insights,
        'protected_lane_downgrades': protected_lane_downgrades,
        'premium_low_value_assignments': premium_low_value_assignments,
        'routing_churn': routing_churn,
        'ineffective_deficit_mitigation': ineffective_mitigation,
    }


def _ineffective_mitigation(policy: RoutingGovernancePolicy, history: list[dict[str, Any]]) -> dict[str, Any]:
    recent = history[-policy.ineffective_window_entries :]
    if len(recent) < policy.ineffective_window_entries:
        return {'detected': False, 'reason': 'insufficient_history'}

    protect_or_emergency = [entry for entry in recent if entry.get('mode') in {'PROTECT', 'EMERGENCY'}]
    if not protect_or_emergency:
        return {'detected': False, 'reason': 'no_recent_protect_or_emergency'}

    mode = protect_or_emergency[-1].get('mode')
    floor = policy.emergency_pressure_floor if mode == 'EMERGENCY' else policy.protect_pressure_floor
    still_high = all(float(entry.get('primary_pressure', 0) or 0) >= floor for entry in protect_or_emergency)
    detected = still_high and len(protect_or_emergency) == len(recent)
    return {
        'detected': detected,
        'mode': mode,
        'window_entries': len(recent),
        'reason': 'pressure_not_recovering' if detected else 'pressure_recovered_or_mixed',
    }


def _provider_pressure_watch(codexbar: dict[str, Any]) -> dict[str, Any]:
    providers = codexbar.get('providers', {}) if isinstance(codexbar, dict) else {}
    watched = []
    for provider, payload in providers.items():
        primary = payload.get('primary_used_percent')
        if primary is None:
            continue
        if float(primary) >= 70:
            watched.append({'provider': provider, 'primary_used_percent': primary})
    return {
        'providers_over_70_pct': watched,
        'high_pressure_detected': bool(watched),
    }


def _lane_burn_insights(policy: RoutingGovernancePolicy, routing_map: dict[str, Any], codexbar: dict[str, Any]) -> list[dict[str, Any]]:
    providers = codexbar.get('providers', {}) if isinstance(codexbar, dict) else {}
    insights = []
    codex_primary = (providers.get('codex') or {}).get('primary_used_percent')

    for agent, model in routing_map.items():
        if model not in policy.premium_models:
            continue
        provider = _provider_from_model(model)
        # MiniMax models are cost-effective (effectively free capacity);
        # never flag them as downgrade candidates regardless of premium_models membership.
        if provider == 'minimax':
            continue
        if agent in policy.low_value_lanes:
            provider_pressure = None
            if provider == 'codex':
                provider_pressure = codex_primary
            insights.append({
                'agent': agent,
                'model': model,
                'provider': provider,
                'provider_primary_used_percent': provider_pressure,
                'suggestion': 'downgrade_candidate' if provider_pressure is None or float(provider_pressure) >= 40 else 'review_for_cost_efficiency',
            })
    return insights


def _recent_swaps(events: list[dict[str, Any]], window_minutes: int) -> list[dict[str, Any]]:
    if not events:
        return []
    now = _parse_ts(events[-1].get('ts'))
    if now is None:
        return []
    cutoff = now - timedelta(minutes=window_minutes)
    return [event for event in events if (ts := _parse_ts(event.get('ts'))) is not None and ts >= cutoff]


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _parse_ts(raw: str | None):
    if not raw:
        return None
    try:
        if raw.endswith('Z'):
            return datetime.strptime(raw, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _safe_collect_codexbar_usage() -> dict[str, Any]:
    try:
        return collect_codexbar_usage()
    except Exception as exc:
        return {
            'collector': 'codexbar_usage',
            'providers': {},
            'errors_present': True,
            'error': str(exc),
        }


def _provider_from_model(model: str) -> str:
    lowered = model.lower()
    if 'openai-codex/' in lowered or 'gpt-5.4' in lowered or 'codex' in lowered:
        return 'codex'
    if 'minimax' in lowered:
        return 'minimax'
    if 'zai/' in lowered or 'glm' in lowered:
        return 'zai'
    return 'unknown'


def _mode_rank(mode: str | None) -> int:
    return _MODE_ORDER.get((mode or 'CRUISE').upper(), _MODE_ORDER['CRUISE'])
