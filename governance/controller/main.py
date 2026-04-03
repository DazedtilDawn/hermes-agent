from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from governance.collectors.error_summary import collect as collect_error_summary
from governance.collectors.health_check import collect as collect_health_check
from governance.collectors.stale_jobs import collect as collect_stale_jobs
from governance.collectors.usage_governance import collect as collect_usage_governance
from governance.collectors.burn_intelligence import collect as collect_burn_intelligence
from governance.collectors.burn_cause_hypotheses import collect as collect_burn_cause_hypotheses
from governance.collectors.lane_recommendation_memory import collect as collect_lane_recommendation_memory
from governance.collectors.optimization_review_digest import collect as collect_optimization_review_digest
from governance.controller.config import build_config
from governance.controller.governance_notifications import GovernanceNotificationManager
from governance.controller.hermes_send_adapter import HermesSendAdapter
from governance.controller.ledgers import GovernanceLedgers
from governance.controller.optimization_proposals import persist_proposal_artifact, format_approval_request_message, send_interactive_approval_request, proposal_is_snoozed
from governance.controller.optimization_approvals import read_recent_messages, parse_approval_commands, apply_proposal_command
from governance.controller.models import (
    ActionClass,
    ExecutionReport,
    ExecutionStatus,
    IncidentReport,
    IncidentStatus,
    VerificationReport,
    VerificationVerdict,
)
from governance.controller.schema_validator import SchemaValidator
from governance.controller.utils import new_id, read_json, utc_now, write_json

STATE_FILE_NAME = 'openclaw_shadow_state.json'
RESTART_PLAYBOOK_ID = 'playbook.restart_dead_gateway'


def main() -> int:
    parser = argparse.ArgumentParser(description='Hermes governance control loop for OpenClaw.')
    sub = parser.add_subparsers(dest='command', required=True)

    shadow = sub.add_parser('shadow-openclaw', help='Run one shadow-mode governance pass against the local OpenClaw runtime')
    shadow.add_argument('--notify-target', default='discord:#approvals', help='Hermes send_message target (default: discord:#approvals)')
    shadow.add_argument('--failure-delta-threshold', type=int, default=5, help='Task failure increase threshold for observation alerts')
    shadow.add_argument('--enable-class1-restart', action='store_true', help='Allow the deterministic restart_dead_gateway class1 lane to execute')
    shadow.add_argument('--restart-cooldown-sec', type=int, default=1800, help='Cooldown window before another gateway restart may be attempted')

    args = parser.parse_args()
    if args.command == 'shadow-openclaw':
        return run_shadow_openclaw(
            args.notify_target,
            args.failure_delta_threshold,
            enable_class1_restart=args.enable_class1_restart,
            restart_cooldown_sec=args.restart_cooldown_sec,
        )
    return 1


def run_shadow_openclaw(
    notify_target: str,
    failure_delta_threshold: int,
    *,
    enable_class1_restart: bool = False,
    restart_cooldown_sec: int = 1800,
) -> int:
    config = build_config()
    ledgers = GovernanceLedgers(config)
    validator = SchemaValidator(config)
    state_path = config.controller_decisions_dir / STATE_FILE_NAME
    state = _load_state(state_path)

    health = collect_health_check()
    errors = collect_error_summary(health)
    stale = collect_stale_jobs(health)
    usage = collect_usage_governance(config)
    burn = collect_burn_intelligence(config)
    causes = collect_burn_cause_hypotheses(usage, burn, errors=errors)
    lane_memory = collect_lane_recommendation_memory(config)
    digest = collect_optimization_review_digest(usage, burn, causes, lane_memory)
    proposals = _collect_optimization_proposals(config, usage, burn, digest)
    now = utc_now()

    controller_decision = {
        'artifact_type': 'controller_shadow_run',
        'artifact_id': new_id('govshadow'),
        'created_at': now,
        'shadow_mode': not enable_class1_restart,
        'gateway_reachable': health['gateway_reachable'],
        'gateway_error': health['gateway_error'],
        'task_failures_total': errors['task_failures_total'],
        'task_failed': errors['task_failed'],
        'task_timed_out': errors['task_timed_out'],
        'task_active': errors['task_active'],
        'stale_jobs_suspected': stale['stale_jobs_suspected'],
        'class1_restart_enabled': enable_class1_restart,
        'restart_cooldown_sec': restart_cooldown_sec,
        'usage_governance': usage,
        'burn_intelligence': burn,
        'burn_cause_hypotheses': causes,
        'lane_recommendation_memory': lane_memory,
        'optimization_review_digest': digest,
        'optimization_proposals': proposals,
    }
    ledgers.record_controller_decision(controller_decision)

    messages: list[str] = []
    approval_messages = _process_optimization_approvals(config, notify_target, state)
    messages.extend(approval_messages)

    if not health['gateway_reachable'] and not state.get('gateway_alert_active', False):
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='OpenClaw gateway unreachable',
            summary='Gateway probe failed; governance proposes restart_dead_gateway playbook.',
            action_class=ActionClass.CLASS1,
            scope=['gateway:probe', 'gateway:restart-candidate'],
            touched_surfaces=['gateway_runtime'],
            playbook_id=RESTART_PLAYBOOK_ID,
            evidence=[f"gateway_error={health['gateway_error']}"] if health['gateway_error'] else ['gateway probe unavailable'],
        )
        verification_path = _emit_shadow_verification(ledgers, validator, incident_path)
        messages.append(
            'OpenClaw governance shadow alert: gateway unreachable. Proposed class1 playbook restart_dead_gateway recorded. '
            f'Incident: {incident_path.name} Verification: {verification_path.name}'
        )
        state['gateway_alert_active'] = True
        state['last_gateway_incident'] = incident_path.name

        if enable_class1_restart:
            restart_message = _maybe_execute_gateway_restart(
                ledgers,
                validator,
                incident_path,
                state,
                restart_cooldown_sec,
            )
            if restart_message:
                messages.append(restart_message)
    elif health['gateway_reachable'] and state.get('gateway_alert_active', False):
        messages.append('OpenClaw governance shadow recovery: gateway probe is reachable again.')
        state['gateway_alert_active'] = False

    last_failures = int(state.get('task_failures_total', 0))
    current_failures = int(errors['task_failures_total'])
    if current_failures - last_failures >= failure_delta_threshold:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='OpenClaw task failure increase observed',
            summary='Task failure count increased materially; governance recorded an observation for review.',
            action_class=ActionClass.CLASS0,
            scope=['tasks:observe'],
            touched_surfaces=['task_ledger'],
            evidence=[f'previous_failures={last_failures}', f'current_failures={current_failures}'],
        )
        messages.append(
            'OpenClaw governance shadow observation: task failure count increased materially. '
            f'Incident: {incident_path.name} total_failures={current_failures}'
        )

    if stale['stale_jobs_suspected'] and not state.get('stale_jobs_alert_active', False):
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='OpenClaw stale jobs suspected',
            summary='No active tasks are running while task failures persist; governance recorded a stale-jobs observation.',
            action_class=ActionClass.CLASS0,
            scope=['tasks:stale-observe'],
            touched_surfaces=['task_ledger'],
            evidence=[
                f"task_active={stale['task_active']}",
                f"task_failures_total={stale['task_failures_total']}",
                f"task_timed_out={stale['task_timed_out']}",
            ],
        )
        messages.append(
            'OpenClaw governance shadow observation: stale jobs suspected. '
            f'Incident: {incident_path.name} active={stale["task_active"]} failures={stale["task_failures_total"]}'
        )
        state['stale_jobs_alert_active'] = True
    elif not stale['stale_jobs_suspected'] and state.get('stale_jobs_alert_active', False):
        messages.append('OpenClaw governance shadow recovery: stale-jobs suspicion cleared.')
        state['stale_jobs_alert_active'] = False


    usage_messages = _evaluate_usage_governance(ledgers, validator, usage, state)
    messages.extend(usage_messages)
    record_burn_attribution_snapshot(config, usage)
    burn_messages = _evaluate_burn_intelligence(ledgers, validator, burn, state)
    messages.extend(burn_messages)
    cause_messages = _evaluate_burn_cause_hypotheses(ledgers, validator, causes, state)
    messages.extend(cause_messages)
    lane_messages = _evaluate_lane_recommendation_memory(ledgers, validator, lane_memory, state)
    messages.extend(lane_messages)
    digest_messages = _evaluate_optimization_review_digest(ledgers, validator, digest, state)
    messages.extend(digest_messages)
    proposal_messages = _evaluate_optimization_proposals(config, ledgers, proposals, state)
    messages.extend(proposal_messages)

    state['task_failures_total'] = current_failures
    state['last_run_at'] = now
    write_json(state_path, state)

    if messages:
        notify_config = replace(config, notification_target=notify_target)
        notifier = GovernanceNotificationManager(HermesSendAdapter(_build_send_message_sender(notify_target)), notify_config, ledgers)
        for message in messages:
            notifier.notify('shadow:openclaw', 'OpenClaw governance shadow', message)
        print("\n".join(messages))
    else:
        print('[SILENT]')
    return 0


def _maybe_execute_gateway_restart(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    incident_path: Path,
    state: dict[str, Any],
    restart_cooldown_sec: int,
) -> str | None:
    if not _cooldown_elapsed(state.get('last_gateway_restart_at'), restart_cooldown_sec):
        return 'OpenClaw governance class1 lane blocked by cooldown. Gateway restart was not attempted.'

    incident_payload = read_json(incident_path)
    try:
        _restart_gateway_service()
        probe = collect_health_check()
    except Exception as exc:
        execution_path = _emit_execution_artifact(
            ledgers,
            validator,
            incident_payload,
            ExecutionStatus.BLOCKED,
            notes=[f'restart_error={exc}'],
        )
        state['last_gateway_restart_at'] = utc_now()
        state['last_gateway_restart_execution'] = execution_path.name
        return (
            'OpenClaw governance class1 restart attempt failed and was recorded as blocked. '
            f'Execution: {execution_path.name}'
        )

    if probe['gateway_reachable']:
        execution_path = _emit_execution_artifact(
            ledgers,
            validator,
            incident_payload,
            ExecutionStatus.EXECUTED,
            notes=['gateway restart attempted', 'post_check=reachable'],
        )
        state['last_gateway_restart_at'] = utc_now()
        state['last_gateway_restart_execution'] = execution_path.name
        state['gateway_alert_active'] = False
        return (
            'OpenClaw governance class1 restart attempt succeeded. '
            f'Execution: {execution_path.name}'
        )

    execution_path = _emit_execution_artifact(
        ledgers,
        validator,
        incident_payload,
        ExecutionStatus.BLOCKED,
        notes=['gateway restart attempted', 'post_check=still_unreachable'],
    )
    state['last_gateway_restart_at'] = utc_now()
    state['last_gateway_restart_execution'] = execution_path.name
    return (
        'OpenClaw governance class1 restart attempt did not restore gateway reachability; owner review remains required. '
        f'Execution: {execution_path.name}'
    )


def _cooldown_elapsed(last_restart_at: str | None, cooldown_sec: int) -> bool:
    if not last_restart_at:
        return True
    from datetime import datetime, timezone

    try:
        last_dt = datetime.strptime(last_restart_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        now_dt = datetime.strptime(utc_now(), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return (now_dt - last_dt).total_seconds() >= cooldown_sec


def _restart_gateway_service() -> None:
    result = subprocess.run(
        ['/opt/homebrew/bin/openclaw', 'gateway', 'restart'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or 'gateway restart failed')


def _emit_shadow_incident(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    *,
    title: str,
    summary: str,
    action_class: ActionClass,
    scope: list[str],
    touched_surfaces: list[str],
    evidence: list[str],
    playbook_id: str | None = None,
) -> Path:
    incident = IncidentReport(
        artifact_id=new_id('incident'),
        created_at=utc_now(),
        chain_id=new_id('chain'),
        title=title,
        summary=summary,
        action_class=action_class,
        proposed_action=playbook_id,
        scope=scope,
        touched_surfaces=touched_surfaces,
        is_novel=False,
        playbook_id=playbook_id,
        playbook_preapproved=bool(playbook_id),
        reversible=bool(playbook_id),
        evidence=evidence,
        status=IncidentStatus.OPEN,
    )
    validator.validate('incident_report', incident.model_dump(mode='json'))
    return ledgers.record_incident(incident)


def _emit_shadow_verification(ledgers: GovernanceLedgers, validator: SchemaValidator, incident_path: Path) -> Path:
    payload = read_json(incident_path)
    verification = VerificationReport(
        artifact_id=new_id('verification'),
        created_at=utc_now(),
        chain_id=payload['chain_id'],
        incident_id=payload['artifact_id'],
        verifier='governance-shadow',
        verdict=VerificationVerdict.VALIDATED,
        scope_confirmed=payload['scope'],
        policy_findings=['shadow mode only; no execution performed unless explicit class1 flag is enabled'],
        is_novel=False,
    )
    validator.validate('verification_report', verification.model_dump(mode='json'))
    return ledgers.record_verification(verification)


def _emit_execution_artifact(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    incident_payload: dict[str, Any],
    execution_status: ExecutionStatus,
    *,
    notes: list[str],
) -> Path:
    execution = ExecutionReport(
        artifact_id=new_id('execution'),
        created_at=utc_now(),
        chain_id=incident_payload['chain_id'],
        incident_id=incident_payload['artifact_id'],
        operator='governance-class1',
        execution_status=execution_status,
        executed_scope=['gateway:restart-candidate'],
        touched_surfaces=['gateway_runtime'],
        playbook_id=RESTART_PLAYBOOK_ID,
        notes=notes,
    )
    validator.validate('execution_report', execution.model_dump(mode='json'))
    return ledgers.record_execution(execution)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _build_send_message_sender(target: str):
    if ':' not in target:
        raise ValueError('notify-target must use platform:target format for live OpenClaw delivery')
    channel, destination = target.split(':', 1)
    channel = channel.strip()
    destination = destination.strip()

    def _sender(_ignored_target: str, message: str):
        result = subprocess.run(
            [
                '/opt/homebrew/bin/openclaw',
                'message',
                'send',
                '--channel',
                channel,
                '--target',
                destination,
                '--message',
                message,
                '--json',
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        stdout = (result.stdout or '').strip()
        json_start = stdout.find('{')
        payload = json.loads(stdout[json_start:]) if json_start >= 0 else {}
        if result.returncode != 0:
            raise RuntimeError(payload or stdout or result.stderr.strip())
        if payload.get('payload', {}).get('ok') is not True:
            raise RuntimeError(payload)
        return payload

    return _sender










def _process_optimization_approvals(config: GovernanceConfig, notify_target: str, state: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    if not notify_target.startswith('discord:'):
        return messages
    try:
        recent = read_recent_messages(notify_target, limit=20)
    except Exception:
        return messages
    commands = parse_approval_commands(recent, after_id=state.get('last_approval_message_id'))
    if not commands:
        return messages
    last_id = state.get('last_approval_message_id')
    for command in commands:
        result = apply_proposal_command(command, config=config)
        if result.get('ok'):
            if result.get('status') == 'applied':
                messages.append(f"Optimization approval applied: {result.get('agent')} -> {result.get('new_model')} from {result.get('artifact')}")
            elif result.get('status') == 'rejected':
                messages.append(f"Optimization approval rejected: {result.get('artifact')}")
            elif result.get('status') == 'snoozed':
                messages.append(f"Optimization approval snoozed for {result.get('minutes')} minutes: {result.get('artifact')}")
        else:
            messages.append(f"Optimization approval command failed: {command.get('raw')} reason={result.get('reason')}")
        last_id = command.get('message_id', last_id)
    if last_id:
        state['last_approval_message_id'] = last_id
    return messages

def _collect_optimization_proposals(config: GovernanceConfig, usage: dict[str, Any], burn: dict[str, Any], digest: dict[str, Any]) -> dict[str, Any]:
    from governance.collectors.optimization_proposals import collect as collect_optimization_proposals

    return collect_optimization_proposals(config, usage, burn, digest)


def _evaluate_optimization_proposals(
    config: GovernanceConfig,
    ledgers: GovernanceLedgers,
    proposals: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    items = proposals.get('proposals', []) or []
    if not items:
        state['optimization_proposal_key'] = ''
        return messages

    key = '|'.join(f"{item['agent']}:{item['current_model']}->{item['recommended_model']}" for item in items)
    if state.get('optimization_proposal_key') == key:
        return messages

    artifact_path = persist_proposal_artifact(proposals, config=config, ledgers=ledgers)
    if artifact_path is None:
        state['optimization_proposal_key'] = ''
        return messages
    if proposal_is_snoozed(config, artifact_path.name):
        state['optimization_proposal_key'] = key
        return messages
    interactive = send_interactive_approval_request(config.notification_target, proposals, artifact_path)
    if interactive.get('ok'):
        messages.append(f"Optimization approval request posted interactively: {artifact_path.name}")
    else:
        message = format_approval_request_message(proposals, artifact_path)
        if message:
            messages.append(message)
    state['optimization_proposal_key'] = key
    return messages

def _evaluate_optimization_review_digest(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    digest: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    items = digest.get('digest_items', []) or []
    if not items:
        state['optimization_digest_key'] = ''
        return messages

    key = '|'.join(item.get('kind', '') + ':' + item.get('summary', '') for item in items[:5])
    if state.get('optimization_digest_key') == key:
        return messages

    top = items[0]
    incident_path = _emit_shadow_incident(
        ledgers,
        validator,
        title='Optimization review digest updated',
        summary='Recurring cost and quality signals have been condensed into a review digest.',
        action_class=ActionClass.CLASS0,
        scope=['burn:review-digest'],
        touched_surfaces=['provider_usage', 'model_routing'],
        evidence=[json.dumps(item, sort_keys=True) for item in items[:5]],
    )
    messages.append(
        'Optimization review digest alert: recurring cost-quality pattern condensed for review. '
        f'Incident: {incident_path.name} top={top.get("kind")}: {top.get("summary")}'
    )
    state['optimization_digest_key'] = key
    return messages

def _evaluate_lane_recommendation_memory(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    lane_memory: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    recommendations = lane_memory.get('recommendations', []) or []
    if not recommendations:
        state['lane_memory_key'] = ''
        return messages

    key = '|'.join(rec.get('kind', '') + ':' + rec.get('summary', '') for rec in recommendations[:5])
    if state.get('lane_memory_key') == key:
        return messages

    top = recommendations[0]
    incident_path = _emit_shadow_incident(
        ledgers,
        validator,
        title='Lane recommendation memory updated',
        summary='Repeated burn patterns suggest a durable lane policy or process change candidate.',
        action_class=ActionClass.CLASS0,
        scope=['burn:lane-memory-observe'],
        touched_surfaces=['provider_usage', 'model_routing'],
        evidence=[json.dumps(rec, sort_keys=True) for rec in recommendations[:5]],
    )
    messages.append(
        'Lane recommendation memory alert: recurring optimization pattern detected. '
        f'Incident: {incident_path.name} top={top.get("kind")}: {top.get("summary")}'
    )
    state['lane_memory_key'] = key
    return messages

def _evaluate_burn_cause_hypotheses(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    causes: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    hypotheses = causes.get('hypotheses', []) or []
    if not hypotheses:
        state['burn_cause_key'] = ''
        return messages

    key = '|'.join(h.get('kind', '') + ':' + h.get('confidence', '') for h in hypotheses[:5])
    if state.get('burn_cause_key') == key:
        return messages

    top = hypotheses[0]
    incident_path = _emit_shadow_incident(
        ledgers,
        validator,
        title='Burn cause hypothesis changed',
        summary='Burn telemetry and routing evidence suggest a likely source of waste or quality-risk pressure.',
        action_class=ActionClass.CLASS0,
        scope=['burn:cause-observe'],
        touched_surfaces=['provider_usage', 'model_routing', 'task_ledger'],
        evidence=[json.dumps(h, sort_keys=True) for h in hypotheses[:5]],
    )
    messages.append(
        'Burn cause hypothesis alert: likely waste source identified. '
        f'Incident: {incident_path.name} top={top.get("kind")}: {top.get("why")}'
    )
    state['burn_cause_key'] = key
    return messages

def _evaluate_burn_intelligence(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    burn: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    recommendations = burn.get('recommendations', []) or []
    if not recommendations:
        state['burn_recommendation_key'] = ''
        return messages

    key = '|'.join(rec.get('kind', '') + ':' + rec.get('summary', '') for rec in recommendations[:5])
    if state.get('burn_recommendation_key') == key:
        return messages

    incident_path = _emit_shadow_incident(
        ledgers,
        validator,
        title='Burn intelligence recommendation set changed',
        summary='Burn attribution trends produced new optimization recommendations.',
        action_class=ActionClass.CLASS0,
        scope=['burn:optimize-observe'],
        touched_surfaces=['provider_usage', 'model_routing'],
        evidence=[json.dumps(rec, sort_keys=True) for rec in recommendations[:5]],
    )
    top = recommendations[0]
    messages.append(
        'Burn intelligence alert: new optimization signal detected. '
        f'Incident: {incident_path.name} top={top.get("kind")}: {top.get("summary")}'
    )
    state['burn_recommendation_key'] = key
    return messages

def _evaluate_usage_governance(
    ledgers: GovernanceLedgers,
    validator: SchemaValidator,
    usage: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    messages: list[str] = []

    protected = usage.get('protected_lane_downgrades', [])
    protected_key = '|'.join(sorted(item['agent'] for item in protected))
    if protected and state.get('usage_protected_key') != protected_key:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='Protected-quality lane downgrade detected',
            summary='Routing telemetry shows a protected lane downgraded before its minimum allowed pressure mode.',
            action_class=ActionClass.CLASS0,
            scope=['routing:observe', 'quality:protect'],
            touched_surfaces=['model_routing'],
            evidence=[json.dumps(item, sort_keys=True) for item in protected],
        )
        messages.append(
            'Usage governance alert: protected-quality lane downgrade detected. '
            f'Incident: {incident_path.name} agents={",".join(item["agent"] for item in protected)}'
        )
        state['usage_protected_key'] = protected_key
    elif not protected:
        state['usage_protected_key'] = ''

    churn = usage.get('routing_churn', {})
    churn_key = f"{churn.get('recent_swap_count', 0)}:{','.join(sorted(item['agent'] for item in churn.get('churn_agents', [])))}"
    if churn.get('high_churn') and state.get('usage_churn_key') != churn_key:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='Routing churn detected',
            summary='Routing telemetry shows high swap activity in a short window.',
            action_class=ActionClass.CLASS0,
            scope=['routing:churn-observe'],
            touched_surfaces=['model_routing'],
            evidence=[json.dumps(churn, sort_keys=True)],
        )
        messages.append(
            'Usage governance alert: routing churn detected. '
            f'Incident: {incident_path.name} swaps={churn.get("recent_swap_count", 0)}'
        )
        state['usage_churn_key'] = churn_key
    elif not churn.get('high_churn'):
        state['usage_churn_key'] = ''

    ineffective = usage.get('ineffective_deficit_mitigation', {})
    ineffective_key = f"{ineffective.get('mode')}:{ineffective.get('window_entries')}:{ineffective.get('reason')}"
    if ineffective.get('detected') and state.get('usage_ineffective_key') != ineffective_key:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='Ineffective deficit mitigation detected',
            summary='Provider pressure stayed elevated across multiple windows despite routing mitigation activity.',
            action_class=ActionClass.CLASS0,
            scope=['routing:mitigation-observe'],
            touched_surfaces=['model_routing'],
            evidence=[json.dumps(ineffective, sort_keys=True)],
        )
        messages.append(
            'Usage governance alert: deficit mitigation appears ineffective. '
            f'Incident: {incident_path.name} mode={ineffective.get("mode")}'
        )
        state['usage_ineffective_key'] = ineffective_key
    elif not ineffective.get('detected'):
        state['usage_ineffective_key'] = ''

    low_value = usage.get('premium_low_value_assignments', [])
    low_value_key = '|'.join(sorted(f"{item['agent']}:{item['model']}" for item in low_value))
    if low_value and state.get('usage_low_value_key') != low_value_key:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='Premium model assigned to low-value lane',
            summary='Routing telemetry shows premium models attached to low-value or repetitive work lanes.',
            action_class=ActionClass.CLASS0,
            scope=['routing:cost-observe'],
            touched_surfaces=['model_routing'],
            evidence=[json.dumps(item, sort_keys=True) for item in usage.get('lane_burn_insights', [])],
        )
        messages.append(
            'Usage governance alert: premium burn on low-value lane detected. '
            f'Incident: {incident_path.name} lanes={",".join(item["agent"] for item in low_value)}'
        )
        state['usage_low_value_key'] = low_value_key
    elif not low_value:
        state['usage_low_value_key'] = ''

    pressure = usage.get('provider_pressure_watch', {})
    pressure_key = '|'.join(sorted(f"{item['provider']}:{item['primary_used_percent']}" for item in pressure.get('providers_over_70_pct', [])))
    if pressure.get('high_pressure_detected') and state.get('usage_pressure_key') != pressure_key:
        incident_path = _emit_shadow_incident(
            ledgers,
            validator,
            title='High provider pressure detected',
            summary='CodexBar telemetry shows provider primary-window usage above the high-pressure threshold.',
            action_class=ActionClass.CLASS0,
            scope=['provider:pressure-observe'],
            touched_surfaces=['provider_usage'],
            evidence=[json.dumps(item, sort_keys=True) for item in pressure.get('providers_over_70_pct', [])],
        )
        messages.append(
            'Usage governance alert: high provider pressure detected. '
            f'Incident: {incident_path.name} providers={",".join(item["provider"] for item in pressure.get("providers_over_70_pct", []))}'
        )
        state['usage_pressure_key'] = pressure_key
    elif not pressure.get('high_pressure_detected'):
        state['usage_pressure_key'] = ''

    return messages


def record_burn_attribution_snapshot(config: GovernanceConfig, usage: dict[str, Any]) -> Path:
    from governance.controller.utils import artifact_filename

    ledger_dir = config.root_dir / 'reports' / 'burn-attribution'
    ledger_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'artifact_type': 'burn_attribution_snapshot',
        'artifact_id': new_id('burnsnap'),
        'created_at': utc_now(),
        'routing_mode': usage.get('routing_mode'),
        'provider_modes': usage.get('provider_modes', {}),
        'provider_composites': usage.get('provider_composites', {}),
        'codexbar_usage': usage.get('codexbar_usage', {}),
        'lane_burn_insights': usage.get('lane_burn_insights', []),
        'routing_churn': usage.get('routing_churn', {}),
        'ineffective_deficit_mitigation': usage.get('ineffective_deficit_mitigation', {}),
    }
    out = ledger_dir / artifact_filename(payload['created_at'], payload['artifact_type'], payload['artifact_id'])
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding='utf-8')
    return out

if __name__ == '__main__':
    raise SystemExit(main())
