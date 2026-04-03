from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from governance.controller.config import GovernanceConfig, build_config
from governance.controller.utils import utc_now, write_json

ROUTING_FILE = Path('/Users/axiom/clawd/data/model-routing.json')


def read_recent_messages(target: str, limit: int = 20) -> list[dict[str, Any]]:
    if ':' not in target:
        return []
    channel, destination = target.split(':', 1)
    result = subprocess.run(
        [
            '/opt/homebrew/bin/openclaw', 'message', 'read',
            '--channel', channel.strip(),
            '--target', destination.strip(),
            '--limit', str(limit),
            '--json',
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    stdout = (result.stdout or '').strip()
    json_start = stdout.find('{')
    payload = json.loads(stdout[json_start:]) if json_start >= 0 else {}
    return payload.get('payload', {}).get('messages', []) or []


def parse_approval_commands(messages: list[dict[str, Any]], *, after_id: str | None = None) -> list[dict[str, Any]]:
    commands = []
    for message in reversed(messages):
        message_id = message.get('id')
        if after_id and message_id and int(message_id) <= int(after_id):
            continue
        author = message.get('author') or {}
        if author.get('bot'):
            continue
        content = (message.get('content') or '').strip()
        upper = content.upper()
        if upper.startswith('APPROVE '):
            _, artifact = content.split(maxsplit=1)
            commands.append({'action': 'approve', 'artifact': artifact.strip(), 'message_id': message_id, 'raw': content})
        elif upper.startswith('REJECT '):
            _, artifact = content.split(maxsplit=1)
            commands.append({'action': 'reject', 'artifact': artifact.strip(), 'message_id': message_id, 'raw': content})
        elif upper.startswith('ROLLBACK '):
            _, artifact = content.split(maxsplit=1)
            commands.append({'action': 'rollback', 'artifact': artifact.strip(), 'message_id': message_id, 'raw': content})
        elif upper.startswith('SNOOZE '):
            parts = content.split()
            artifact = parts[1] if len(parts) > 1 else ''
            minutes = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30
            commands.append({'action': 'snooze', 'artifact': artifact, 'minutes': minutes, 'message_id': message_id, 'raw': content})
        elif upper.startswith('ALT '):
            parts = content.split(maxsplit=2)
            if len(parts) == 3:
                _, artifact, model = parts
                commands.append({'action': 'alt', 'artifact': artifact.strip(), 'model': model.strip(), 'message_id': message_id, 'raw': content})
    return commands


def apply_proposal_command(command: dict[str, Any], *, config: GovernanceConfig | None = None) -> dict[str, Any]:
    cfg = config or build_config()
    artifact_path = _resolve_artifact(cfg, command.get('artifact', ''))
    if artifact_path is None:
        return {'ok': False, 'reason': 'artifact_not_found'}
    proposal = json.loads(artifact_path.read_text(encoding='utf-8'))
    proposals = proposal.get('proposals', []) or []
    if not proposals:
        return {'ok': False, 'reason': 'proposal_empty'}
    target = proposals[0]

    action = command['action']
    result = {'ok': True, 'action': action, 'artifact': artifact_path.name, 'agent': target.get('agent')}

    if action == 'reject':
        result['status'] = 'rejected'
    elif action == 'snooze':
        result['status'] = 'snoozed'
        result['minutes'] = command.get('minutes', 30)
        _write_snooze(cfg, artifact_path.name, result['minutes'])
    else:
        routing = json.loads(ROUTING_FILE.read_text(encoding='utf-8'))
        routing.setdefault('routing', {})
        current_model = routing['routing'].get(target['agent'], target.get('current_model'))
        if action == 'approve':
            new_model = target['recommended_model']
        elif action == 'alt':
            new_model = command.get('model')
        elif action == 'rollback':
            new_model = target.get('rollback_model') or target.get('current_model')
        else:
            new_model = None
        if not new_model:
            return {'ok': False, 'reason': 'missing_model'}
        routing['routing'][target['agent']] = new_model
        routing['updatedAt'] = utc_now()
        ROUTING_FILE.write_text(json.dumps(routing, indent=2) + "\n", encoding='utf-8')
        result['status'] = 'applied'
        result['new_model'] = new_model
        result['previous_model'] = current_model
        _clear_snooze(cfg, artifact_path.name)

    log_path = cfg.controller_decisions_dir / f"optimization_approval_{artifact_path.stem}_{command['message_id']}.json"
    write_json(log_path, {
        'artifact_type': 'optimization_approval_action',
        'artifact_id': command['message_id'],
        'created_at': utc_now(),
        'command': command,
        'result': result,
    })
    return result


def is_proposal_snoozed(artifact_name: str, *, config: GovernanceConfig | None = None, now: str | None = None) -> bool:
    cfg = config or build_config()
    path = _snooze_path(cfg, artifact_name)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        until = payload.get('snooze_until')
        if not until:
            return False
        now_dt = _parse_ts(now or utc_now())
        until_dt = _parse_ts(until)
        if now_dt is None or until_dt is None:
            return False
        return now_dt < until_dt
    except Exception:
        return False


def _write_snooze(config: GovernanceConfig, artifact_name: str, minutes: int) -> None:
    now_dt = _parse_ts(utc_now()) or datetime.now(timezone.utc)
    until = now_dt + timedelta(minutes=minutes)
    write_json(_snooze_path(config, artifact_name), {
        'artifact_type': 'optimization_proposal_snooze',
        'artifact_id': artifact_name,
        'created_at': utc_now(),
        'minutes': minutes,
        'snooze_until': until.strftime('%Y-%m-%dT%H:%M:%SZ'),
    })


def _clear_snooze(config: GovernanceConfig, artifact_name: str) -> None:
    path = _snooze_path(config, artifact_name)
    if path.exists():
        path.unlink()


def _snooze_path(config: GovernanceConfig, artifact_name: str) -> Path:
    return config.controller_decisions_dir / f'snooze_{artifact_name}'


def _parse_ts(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


def _resolve_artifact(config: GovernanceConfig, artifact_ref: str) -> Path | None:
    if not artifact_ref:
        return None
    queue = config.approvals_queue_dir
    direct = queue / artifact_ref
    if direct.exists():
        return direct
    for candidate in queue.glob('*.json'):
        if artifact_ref in candidate.name:
            return candidate
    return None
