from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from governance.controller.config import GovernanceConfig, build_config
from governance.controller.ledgers import GovernanceLedgers
from governance.controller.optimization_approvals import is_proposal_snoozed
from governance.controller.utils import artifact_filename, new_id, utc_now, write_json

logger = logging.getLogger(__name__)

# Human-readable reason mapping
REASON_DESCRIPTIONS: dict[str, str] = {
    'downgrade_candidate': (
        'This lane is using an expensive model when a lighter one would suffice, '
        'reducing cost while maintaining coverage.'
    ),
    'review_for_cost_efficiency': (
        'Provider utilization is high — switching to a more cost-effective model could help balance load.'
    ),
    'codex_pressure_relief': (
        'Codex provider usage is elevated; offloading this lane relieves pressure.'
    ),
    'protected_lane_review': (
        'This is a protected lane — the downgrade requires explicit owner approval before it can take effect.'
    ),
}


def persist_proposal_artifact(
    proposals: dict[str, Any],
    *,
    config: GovernanceConfig | None = None,
    ledgers: GovernanceLedgers | None = None,
) -> Path | None:
    proposal_items = proposals.get('proposals', []) or []
    if not proposal_items:
        return None
    cfg = config or build_config()
    payload = {
        'artifact_type': 'optimization_proposal',
        'artifact_id': new_id('optprop'),
        'created_at': utc_now(),
        'mode': proposals.get('mode'),
        'approval_required': proposals.get('approval_required', True),
        'auto_apply_allowed': proposals.get('auto_apply_allowed', False),
        'max_lane_changes': proposals.get('max_lane_changes', 1),
        'proposals': proposal_items,
        'supporting_recommendations': proposals.get('supporting_recommendations', []),
        'supporting_digest_items': proposals.get('supporting_digest_items', []),
    }
    out = cfg.approvals_queue_dir / artifact_filename(payload['created_at'], payload['artifact_type'], payload['artifact_id'])
    write_json(out, payload)
    return out


def _short_artifact_id(artifact_path: Path) -> str:
    """Extract the short artifact ID (e.g. 'optprop-72f4f720a023') from a filename."""
    name = artifact_path.name
    match = re.search(r'(optprop-[a-f0-9]{12})', name)
    if match:
        return match.group(1)
    # Fallback: strip the timestamp prefix and .json suffix
    base = name.replace('.json', '')
    parts = base.split('_optimization_proposal_')
    if len(parts) == 2:
        return parts[1]
    return base


def format_approval_request_message(proposals: dict[str, Any], artifact_path: Path | None = None) -> str:
    """Format a human-readable governance proposal message for Discord."""
    proposal_items = proposals.get('proposals', []) or []
    if not proposal_items:
        return ''
    mode = proposals.get('mode', 'UNKNOWN')
    lines: list[str] = []

    for idx, item in enumerate(proposal_items[:3], start=1):
        if idx == 1:
            lines.append(f"**Model Optimization Proposed [{mode}]**")
            lines.append("")
        else:
            lines.append(f"**Option {idx}:**")

        agent = item.get('agent', 'unknown')
        current = item.get('current_model', '?')
        recommended = item.get('recommended_model', '?')
        lines.append(f"Switch `{agent}` from {current} → {recommended}")
        lines.append("")

        reason_code = item.get('reason', 'review_for_cost_efficiency')
        reason_text = REASON_DESCRIPTIONS.get(reason_code)
        if reason_text:
            lines.append(f"Reason: {reason_text}")
        else:
            # Fallback: make the code readable
            readable = reason_code.replace('_', ' ').capitalize()
            lines.append(f"Reason: {readable}")

        if item.get('rollback_model'):
            lines.append(f"Rollback target: {item['rollback_model']}")

        alternatives = item.get('alternative_models') or []
        if alternatives:
            lines.append(f"Alternatives: {', '.join(alternatives)}")

        if item.get('requires_explicit_owner'):
            lines.append("⚠ Protected lane — explicit owner approval required")

        lines.append("")

    # Supporting context
    support = proposals.get('supporting_recommendations', []) or proposals.get('supporting_digest_items', []) or []
    if support:
        summary = support[0].get('summary') or support[0].get('kind')
        if summary:
            lines.append(f"Supporting context: {summary}")
            lines.append("")

    lines.append(
        "Reply `APPROVE <artifact>`, `ALT <artifact> <model>`, "
        "`ROLLBACK <artifact>`, `REJECT <artifact>`, or `SNOOZE <artifact> <minutes>`"
    )
    return "\n".join(lines)


def build_discord_components(proposals: dict[str, Any], artifact_path: Path) -> list[dict[str, Any]]:
    """Build Discord API-compatible component JSON with short artifact IDs.

    Returns a list of action rows (type 1) containing buttons (type 2).
    Uses short artifact_id (e.g. optprop-72f4f720a023) in custom_id fields.
    """
    items = proposals.get('proposals') or []
    if not items:
        return []

    item = items[0]
    short_id = _short_artifact_id(artifact_path)

    # Main action row: Approve, Reject, Snooze, (optional Rollback)
    buttons: list[dict[str, Any]] = [
        {"type": 2, "style": 3, "label": "Approve", "custom_id": f"gov_approve_{short_id}"},
        {"type": 2, "style": 4, "label": "Reject", "custom_id": f"gov_reject_{short_id}"},
        {"type": 2, "style": 2, "label": "Snooze 30m", "custom_id": f"gov_snooze_{short_id}_30"},
    ]

    if item.get('rollback_model'):
        buttons.append({"type": 2, "style": 2, "label": "Rollback", "custom_id": f"gov_rollback_{short_id}"})

    action_rows: list[dict[str, Any]] = [
        {"type": 1, "components": buttons}
    ]

    # Alternative models as a second action row with buttons
    alternatives = item.get('alternative_models') or []
    if alternatives:
        alt_buttons = []
        for model in alternatives[:4]:  # Discord allows max 5 buttons per row; 4 leaves room
            short_model = model.split('/')[-1] if '/' in model else model
            alt_buttons.append({
                "type": 2,
                "style": 1,
                "label": f"Alt: {short_model}",
                "custom_id": f"gov_alt_{short_id}_{model}",
            })
        if alt_buttons:
            action_rows.append({"type": 1, "components": alt_buttons})

    return action_rows


def _resolve_channel_id(target: str) -> str | None:
    """Resolve a discord:#channel_name target to a channel ID.

    Checks env vars in order:
    1. DISCORD_APPROVALS_CHANNEL_ID
    2. DISCORD_HOME_CHANNEL
    Falls back to None if no channel ID is configured.
    Logs which channel was resolved or if no channel was found.
    """
    # Parse the target to understand what channel is being requested
    requested_channel = ''
    if ':' in target:
        _, requested_channel = target.split(':', 1)
        requested_channel = requested_channel.strip().lstrip('#')

    channel_id = os.getenv('DISCORD_APPROVALS_CHANNEL_ID')
    if channel_id:
        logger.info(
            'Resolved Discord target %r to approvals channel ID %s (requested: %s)',
            target, channel_id, requested_channel,
        )
        return channel_id

    channel_id = os.getenv('DISCORD_HOME_CHANNEL')
    if channel_id:
        logger.info(
            'Resolved Discord target %r to home channel ID %s (DISCORD_APPROVALS_CHANNEL_ID not set, requested: %s)',
            target, channel_id, requested_channel,
        )
        return channel_id

    logger.warning(
        'Could not resolve Discord target %r: neither DISCORD_APPROVALS_CHANNEL_ID nor DISCORD_HOME_CHANNEL is set',
        target,
    )
    return None


def send_governance_discord_message(channel_id: str, content: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    """Send a governance message with interactive components via Discord REST API.

    Uses httpx (core dependency) for the HTTP call.
    Returns the parsed JSON response from Discord.
    """
    import httpx

    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN not set')

    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    headers = {
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json',
    }
    payload: dict[str, Any] = {'content': content}
    if components:
        payload['components'] = components

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=payload)
        result = response.json()

    if response.status_code >= 400:
        logger.warning('Discord REST API error %s: %s', response.status_code, result)

    return result


def send_interactive_approval_request(target: str, proposals: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    """Send an interactive approval request to Discord.

    Tries the direct Discord REST API first (using DISCORD_BOT_TOKEN),
    falls back to `openclaw message send` if the REST call fails.
    """
    if not target.startswith('discord:'):
        return {'ok': False, 'reason': 'interactive_only_supported_for_discord_target'}

    message = format_approval_request_message(proposals, artifact_path)
    components = build_discord_components(proposals, artifact_path)

    # Try direct Discord REST API first
    channel_id = _resolve_channel_id(target)
    if channel_id and os.getenv('DISCORD_BOT_TOKEN'):
        try:
            result = send_governance_discord_message(channel_id, message, components)
            # Discord returns message data on success (includes 'id' field)
            if 'id' in result:
                return {'ok': True, 'payload': result, 'method': 'discord_rest_api'}
            # If we got here, Discord returned an error response
            logger.warning('Discord REST API returned error, falling back to openclaw: %s', result)
        except Exception as exc:
            logger.warning('Discord REST API call failed, falling back to openclaw: %s', exc)

    # Fallback: use openclaw message send (text-only, no buttons)
    _, destination = target.split(':', 1)
    try:
        result = subprocess.run(
            ['/opt/homebrew/bin/openclaw', 'message', 'send', '--channel', 'discord',
             '--target', destination.strip(), '--message', message, '--json'],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {'ok': False, 'reason': str(exc)}

    stdout = (result.stdout or '').strip()
    json_start = stdout.find('{')
    payload = json.loads(stdout[json_start:]) if json_start >= 0 else {}
    if result.returncode != 0:
        return {'ok': False, 'reason': payload or stdout or result.stderr.strip()}
    return {'ok': True, 'payload': payload, 'method': 'openclaw_fallback'}


def proposal_is_snoozed(config: GovernanceConfig, artifact_name: str) -> bool:
    return is_proposal_snoozed(artifact_name, config=config)
