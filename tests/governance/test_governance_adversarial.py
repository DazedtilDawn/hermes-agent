from __future__ import annotations

import pytest

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
from governance.controller.schema_validator import SchemaValidationError

from .conftest import build_class1_chain


def test_schema_invalid_artifact_fails_validation(validator):
    bad = {
        "artifact_type": "incident_report",
        "artifact_id": "bad-incident",
        "schema_version": "1.0",
        "created_at": "2026-04-02T00:00:00Z",
        "chain_id": "chain-bad",
        "title": "Bad",
        "summary": "Missing required fields",
        "action_class": "class1",
        "scope": ["scheduler:retry"],
        # touched_surfaces omitted intentionally
        "is_novel": False,
        "status": "open",
    }
    with pytest.raises(SchemaValidationError):
        validator.validate("incident_report", bad)


def test_execution_without_chain_is_recorded_as_governance_incident(evaluator, config):
    incident, verification, execution = build_class1_chain()
    bad_verification = verification.model_copy(update={"chain_id": "wrong-chain"})
    decision = evaluator.evaluate_execution(incident, bad_verification, execution=execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "unknown-chain artifact ingestion"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_unauthorized_execution_blocks_chain(evaluator, config):
    incident, _, execution = build_class1_chain()
    decision = evaluator.evaluate_execution(incident, verification=None, execution=execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "unauthorized execution"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_authorization_chain_failure_blocks_non_preapproved_class1(evaluator, config):
    incident, verification, _ = build_class1_chain()
    invalid_incident = incident.model_copy(update={"playbook_preapproved": False})
    decision = evaluator.evaluate_execution(invalid_incident, verification)
    assert decision.allowed is False
    assert decision.governance_failure_type == "authorization chain failure"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_scope_violation_blocks_chain(evaluator, config):
    incident, verification, execution = build_class1_chain()
    bad_execution = execution.model_copy(update={"executed_scope": ["scheduler:retry", "scheduler:delete"]})
    decision = evaluator.evaluate_execution(incident, verification, execution=bad_execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "scope violation"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_approval_scope_mismatch_blocks_chain(evaluator, config):
    incident = IncidentReport(
        artifact_id="incident-appr",
        created_at="2026-04-02T00:00:00Z",
        chain_id="chain-appr",
        title="Config update",
        summary="Controlled config update requested",
        action_class=ActionClass.CLASS2,
        proposed_action="Patch runtime config",
        scope=["config:update", "config:reload"],
        touched_surfaces=["runtime_config"],
        is_novel=False,
        evidence=["approved maintenance window"],
    )
    verification = VerificationReport(
        artifact_id="verification-appr",
        created_at="2026-04-02T00:01:00Z",
        chain_id="chain-appr",
        incident_id="incident-appr",
        verifier="verifier",
        verdict=VerificationVerdict.VALIDATED,
        scope_confirmed=["config:update", "config:reload"],
        is_novel=False,
    )
    approval = ApprovalReport(
        artifact_id="approval-appr",
        created_at="2026-04-02T00:02:00Z",
        chain_id="chain-appr",
        incident_id="incident-appr",
        approval_status=ApprovalStatus.APPROVED,
        approved_scope=["config:update"],
        allowed_surfaces=["runtime_config"],
    )
    execution = ExecutionReport(
        artifact_id="execution-appr",
        created_at="2026-04-02T00:03:00Z",
        chain_id="chain-appr",
        incident_id="incident-appr",
        operator="operator",
        execution_status=ExecutionStatus.EXECUTED,
        executed_scope=["config:update", "config:reload"],
        touched_surfaces=["runtime_config"],
        notes=["performed broader scope than approved"],
    )
    decision = evaluator.evaluate_execution(incident, verification, approval, execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "approval scope mismatch"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_protected_surface_surprise_blocks_chain(evaluator, config):
    incident = IncidentReport(
        artifact_id="incident-ps",
        created_at="2026-04-02T00:00:00Z",
        chain_id="chain-ps",
        title="Config patch",
        summary="Attempt to patch configuration",
        action_class=ActionClass.CLASS2,
        proposed_action="Patch config",
        scope=["config:update"],
        touched_surfaces=["runtime_config"],
        is_novel=False,
        evidence=["drift detected"],
    )
    verification = VerificationReport(
        artifact_id="verification-ps",
        created_at="2026-04-02T00:01:00Z",
        chain_id="chain-ps",
        incident_id="incident-ps",
        verifier="verifier",
        verdict=VerificationVerdict.VALIDATED,
        scope_confirmed=["config:update"],
        is_novel=False,
    )
    approval = ApprovalReport(
        artifact_id="approval-ps",
        created_at="2026-04-02T00:02:00Z",
        chain_id="chain-ps",
        incident_id="incident-ps",
        approval_status=ApprovalStatus.APPROVED,
        approved_scope=["config:update"],
        allowed_surfaces=["runtime_config"],
    )
    execution = ExecutionReport(
        artifact_id="execution-ps",
        created_at="2026-04-02T00:03:00Z",
        chain_id="chain-ps",
        incident_id="incident-ps",
        operator="operator",
        execution_status=ExecutionStatus.EXECUTED,
        executed_scope=["config:update"],
        touched_surfaces=["openclaw.json"],
        notes=["unexpected touch"],
    )
    decision = evaluator.evaluate_execution(incident, verification, approval, execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "unexpected protected-surface touch"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))


def test_novelty_queues_owner(evaluator):
    incident, verification, _ = build_class1_chain()
    incident = incident.model_copy(update={"is_novel": True})
    decision = evaluator.evaluate_execution(incident, verification)
    assert decision.allowed is False
    assert decision.owner_review_required is True
    assert decision.reason == "novelty_requires_owner_review"


def test_auto_execution_pause_routes_to_owner(evaluator):
    incident, verification, _ = build_class1_chain()
    decision = evaluator.evaluate_execution(incident, verification, auto_execution_paused=True)
    assert decision.allowed is False
    assert decision.owner_review_required is True
    assert decision.reason == "auto_execution_paused"
