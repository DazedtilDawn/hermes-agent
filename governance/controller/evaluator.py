from __future__ import annotations

from .config import GovernanceConfig, build_config
from .governance_incidents import GovernanceIncidentEmitter
from .models import (
    ActionClass,
    ApprovalReport,
    ApprovalStatus,
    ArtifactStage,
    EvaluationDecision,
    ExecutionReport,
    IncidentReport,
    VerificationReport,
    VerificationVerdict,
)
from .state_machine import assert_transition
from .utils import read_yaml


class GovernanceEvaluator:
    def __init__(self, config: GovernanceConfig | None = None, emitter: GovernanceIncidentEmitter | None = None):
        self.config = config or build_config()
        self.emitter = emitter
        self.protected_surfaces = set(read_yaml(self.config.policy_dir / "protected-surfaces.yaml")["protected_surfaces"])

    def validate_transition(self, current: ArtifactStage, nxt: ArtifactStage, action_class: ActionClass, source_artifact_id: str | None = None) -> EvaluationDecision:
        try:
            assert_transition(current, nxt, action_class)
        except ValueError as exc:
            if self.emitter is not None:
                self.emitter.emit(
                    "illegal state transition",
                    str(exc),
                    {"current": current.value, "next": nxt.value, "action_class": action_class.value},
                    source_artifact_id=source_artifact_id,
                )
            return EvaluationDecision(allowed=False, reason=str(exc), governance_failure_type="illegal state transition")
        return EvaluationDecision(allowed=True, next_stage=nxt, reason="transition_allowed")

    def evaluate_execution(
        self,
        incident: IncidentReport,
        verification: VerificationReport | None = None,
        approval: ApprovalReport | None = None,
        execution: ExecutionReport | None = None,
        *,
        auto_execution_paused: bool = False,
    ) -> EvaluationDecision:
        if verification is None:
            return self._fail("unauthorized execution", "Execution requires a verification artifact", incident)
        if verification.incident_id != incident.artifact_id or verification.chain_id != incident.chain_id:
            return self._fail("unknown-chain artifact ingestion", "Verification chain does not match incident", incident, verification=verification)
        if verification.verdict != VerificationVerdict.VALIDATED:
            owner_review = verification.verdict == VerificationVerdict.NEEDS_MORE_EVIDENCE
            return EvaluationDecision(
                allowed=False,
                owner_review_required=owner_review,
                reason=f"verification_{verification.verdict.value}",
                details={"verdict": verification.verdict.value},
            )
        if incident.is_novel or verification.is_novel:
            return EvaluationDecision(
                allowed=False,
                owner_review_required=True,
                reason="novelty_requires_owner_review",
                details={"is_novel": True},
            )
        if auto_execution_paused:
            return EvaluationDecision(
                allowed=False,
                owner_review_required=True,
                reason="auto_execution_paused",
            )
        if incident.action_class == ActionClass.CLASS0:
            return EvaluationDecision(allowed=False, reason="class0_is_observe_only")
        if incident.action_class == ActionClass.CLASS1:
            if not incident.playbook_id or not incident.playbook_preapproved or not incident.reversible:
                return self._fail("authorization chain failure", "Class1 execution requires a pre-approved reversible playbook", incident, verification=verification)
        if incident.action_class in {ActionClass.CLASS2, ActionClass.CLASS3}:
            if approval is None:
                return self._fail("authorization chain failure", "Class2+ execution requires owner approval", incident, verification=verification)
            if approval.incident_id != incident.artifact_id or approval.chain_id != incident.chain_id:
                return self._fail("unknown-chain artifact ingestion", "Approval chain does not match incident", incident, approval=approval)
            if approval.approver_role != "owner" or approval.approval_status != ApprovalStatus.APPROVED:
                return self._fail("authorization chain failure", "Verifier cannot authorize class2+ and owner approval must be explicit", incident, approval=approval)
        if execution is None:
            return EvaluationDecision(allowed=True, next_stage=ArtifactStage.EXECUTION, reason="execution_permitted")
        if execution.incident_id != incident.artifact_id or execution.chain_id != incident.chain_id:
            return self._fail("unknown-chain artifact ingestion", "Execution chain does not match incident", incident, execution=execution)
        executed_scope = set(execution.executed_scope)
        incident_scope = set(incident.scope)
        if not executed_scope.issubset(incident_scope):
            return self._fail("scope violation", "Execution scope exceeds incident scope", incident, execution=execution)
        if approval is not None and not executed_scope.issubset(set(approval.approved_scope)):
            return self._fail("approval scope mismatch", "Execution scope exceeds approved scope", incident, approval=approval, execution=execution)
        touched_surfaces = set(execution.touched_surfaces)
        unexpected_protected = touched_surfaces & self.protected_surfaces
        if unexpected_protected and not (approval and unexpected_protected.issubset(set(approval.allowed_surfaces))):
            return self._fail(
                "unexpected protected-surface touch",
                "Execution touched protected surfaces outside explicit owner authorization",
                incident,
                approval=approval,
                execution=execution,
                extra={"unexpected_protected_surfaces": sorted(unexpected_protected)},
            )
        if incident.action_class == ActionClass.CLASS1 and execution.playbook_id != incident.playbook_id:
            return self._fail("authorization chain failure", "Operator must not improvise beyond the approved playbook", incident, execution=execution)
        return EvaluationDecision(allowed=True, next_stage=ArtifactStage.CLOSED, reason="execution_valid")

    def _fail(self, failure_type: str, reason: str, incident: IncidentReport, **context) -> EvaluationDecision:
        details = {"incident_id": incident.artifact_id, "chain_id": incident.chain_id}
        for key, value in context.items():
            if key == "extra":
                details.update(value)
            elif value is not None and hasattr(value, "model_dump"):
                details[key] = value.model_dump(mode="json")
        if self.emitter is not None:
            self.emitter.emit(failure_type, reason, details, source_artifact_id=incident.artifact_id, chain_id=incident.chain_id)
        return EvaluationDecision(allowed=False, reason=reason, governance_failure_type=failure_type, details=details)
