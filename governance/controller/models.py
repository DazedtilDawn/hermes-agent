from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionClass(str, Enum):
    CLASS0 = "class0"
    CLASS1 = "class1"
    CLASS2 = "class2"
    CLASS3 = "class3"


class ArtifactStage(str, Enum):
    INCIDENT = "incident"
    VERIFICATION = "verification"
    APPROVAL = "approval"
    EXECUTION = "execution"
    CLOSED = "closed"


class QueueState(str, Enum):
    QUEUED = "queued"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class GovernanceSeverity(str, Enum):
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationVerdict(str, Enum):
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    LIMITED = "limited"


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    BLOCKED = "blocked"


class IncidentStatus(str, Enum):
    OPEN = "open"
    VERIFIED = "verified"
    APPROVED = "approved"
    EXECUTED = "executed"
    CLOSED = "closed"
    BLOCKED = "blocked"


class BaseArtifact(BaseModel):
    artifact_type: str
    artifact_id: str
    schema_version: str = "1.0"
    created_at: str


class IncidentReport(BaseArtifact):
    artifact_type: str = "incident_report"
    chain_id: str
    title: str
    summary: str
    action_class: ActionClass
    proposed_action: str | None = None
    scope: list[str]
    touched_surfaces: list[str]
    protected_surface_expected: bool = False
    is_novel: bool
    playbook_id: str | None = None
    playbook_preapproved: bool = False
    reversible: bool = False
    evidence: list[str] = Field(default_factory=list)
    status: IncidentStatus = IncidentStatus.OPEN


class VerificationReport(BaseArtifact):
    artifact_type: str = "verification_report"
    chain_id: str
    incident_id: str
    verifier: str
    verdict: VerificationVerdict
    scope_confirmed: list[str]
    risk_notes: list[str] = Field(default_factory=list)
    policy_findings: list[str] = Field(default_factory=list)
    is_novel: bool = False


class ApprovalReport(BaseArtifact):
    artifact_type: str = "approval_report"
    chain_id: str
    incident_id: str
    approver_role: str = "owner"
    approval_status: ApprovalStatus
    approved_scope: list[str]
    allowed_surfaces: list[str]
    notes: list[str] = Field(default_factory=list)


class ExecutionReport(BaseArtifact):
    artifact_type: str = "execution_report"
    chain_id: str
    incident_id: str
    operator: str
    execution_status: ExecutionStatus
    executed_scope: list[str]
    touched_surfaces: list[str]
    playbook_id: str | None = None
    notes: list[str] = Field(default_factory=list)


class GovernanceIncident(BaseArtifact):
    artifact_type: str = "governance_incident"
    updated_at: str | None = None
    chain_id: str | None = None
    source_artifact_id: str | None = None
    failure_type: str
    severity: GovernanceSeverity
    summary: str
    details: dict[str, Any]
    queue_state: QueueState = QueueState.QUEUED
    notification_status: str = "not_attempted"


class GovernanceQueueItem(BaseModel):
    queue_id: str
    governance_incident_id: str
    governance_incident_path: str
    created_at: str
    updated_at: str
    state: QueueState
    reason: str
    notification_attempted: bool = False


class EvaluationDecision(BaseModel):
    allowed: bool
    owner_review_required: bool = False
    next_stage: ArtifactStage | None = None
    reason: str
    governance_failure_type: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
