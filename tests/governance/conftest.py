from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governance.controller.config import build_config
from governance.controller.evaluator import GovernanceEvaluator
from governance.controller.governance_incidents import GovernanceIncidentEmitter
from governance.controller.governance_notification_integration import GovernanceNotificationIntegration
from governance.controller.governance_notifications import GovernanceNotificationManager
from governance.controller.governance_queue_lifecycle import GovernanceQueueLifecycle
from governance.controller.hermes_send_adapter import HermesSendAdapter
from governance.controller.ledgers import GovernanceLedgers
from governance.controller.models import (
    ActionClass,
    ApprovalReport,
    ApprovalStatus,
    ExecutionReport,
    ExecutionStatus,
    IncidentReport,
    VerificationReport,
    VerificationVerdict,
)
from governance.controller.schema_validator import SchemaValidator


@pytest.fixture()
def governance_root(tmp_path: Path) -> Path:
    src = ROOT / "governance"
    dst = tmp_path / "governance"
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if '__pycache__' in rel.parts:
            continue
        if rel.parts and rel.parts[0] == 'reports' and path.is_file() and path.name != '.gitkeep':
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    return dst


@pytest.fixture()
def config(governance_root: Path):
    return build_config(governance_root)


@pytest.fixture()
def ledgers(config):
    return GovernanceLedgers(config)


@pytest.fixture()
def validator(config):
    return SchemaValidator(config)


@pytest.fixture()
def notifier(config, ledgers):
    return GovernanceNotificationManager(HermesSendAdapter(), config, ledgers)


@pytest.fixture()
def notification_integration(config, notifier):
    return GovernanceNotificationIntegration(notifier, config)


@pytest.fixture()
def emitter(config, ledgers, validator, notification_integration):
    queue = GovernanceQueueLifecycle(config, ledgers, notification_integration)
    return GovernanceIncidentEmitter(config, ledgers, queue, validator, notification_integration)


@pytest.fixture()
def evaluator(config, emitter):
    return GovernanceEvaluator(config, emitter)


def build_runtime(governance_root: Path, sender=None, **config_overrides):
    config = replace(build_config(governance_root), **config_overrides)
    ledgers = GovernanceLedgers(config)
    validator = SchemaValidator(config)
    notifier = GovernanceNotificationManager(HermesSendAdapter(sender), config, ledgers)
    notification_integration = GovernanceNotificationIntegration(notifier, config)
    queue = GovernanceQueueLifecycle(config, ledgers, notification_integration)
    emitter = GovernanceIncidentEmitter(config, ledgers, queue, validator, notification_integration)
    evaluator = GovernanceEvaluator(config, emitter)
    return {
        "config": config,
        "ledgers": ledgers,
        "validator": validator,
        "notifier": notifier,
        "notification_integration": notification_integration,
        "queue": queue,
        "emitter": emitter,
        "evaluator": evaluator,
    }


def build_class1_chain():
    incident = IncidentReport(
        artifact_id="incident-001",
        created_at="2026-04-02T00:00:00Z",
        chain_id="chain-001",
        title="Stale scheduler",
        summary="A scheduler heartbeat is stale and safe retry is proposed",
        action_class=ActionClass.CLASS1,
        proposed_action="Retry safe job",
        scope=["scheduler:retry"],
        touched_surfaces=["scheduler_runtime"],
        is_novel=False,
        playbook_id="playbook.retry_safe_job",
        playbook_preapproved=True,
        reversible=True,
        evidence=["heartbeat older than threshold"],
    )
    verification = VerificationReport(
        artifact_id="verification-001",
        created_at="2026-04-02T00:05:00Z",
        chain_id="chain-001",
        incident_id="incident-001",
        verifier="verifier",
        verdict=VerificationVerdict.VALIDATED,
        scope_confirmed=["scheduler:retry"],
        policy_findings=["class1 preapproved playbook confirmed"],
        is_novel=False,
    )
    execution = ExecutionReport(
        artifact_id="execution-001",
        created_at="2026-04-02T00:10:00Z",
        chain_id="chain-001",
        incident_id="incident-001",
        operator="operator",
        execution_status=ExecutionStatus.EXECUTED,
        executed_scope=["scheduler:retry"],
        touched_surfaces=["scheduler_runtime"],
        playbook_id="playbook.retry_safe_job",
        notes=["retry completed"],
    )
    return incident, verification, execution


def build_class2_approval():
    return ApprovalReport(
        artifact_id="approval-001",
        created_at="2026-04-02T00:07:00Z",
        chain_id="chain-002",
        incident_id="incident-002",
        approval_status=ApprovalStatus.APPROVED,
        approved_scope=["config:update"],
        allowed_surfaces=["runtime_config"],
        notes=["owner approved limited config update"],
    )
