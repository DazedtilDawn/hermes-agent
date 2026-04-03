from __future__ import annotations

import json

from governance.controller.models import ActionClass, ArtifactStage
from governance.controller.state_machine import assert_transition

from .conftest import build_class1_chain


def test_governance_incident_files_are_emitted_for_failure_paths(evaluator, config, validator):
    incident, verification, execution = build_class1_chain()
    bad_execution = execution.model_copy(update={"executed_scope": ["scheduler:retry", "scheduler:delete"]})
    decision = evaluator.evaluate_execution(incident, verification, execution=bad_execution)
    assert decision.allowed is False

    incident_files = list(config.governance_incidents_dir.glob("*.json"))
    queue_files = list(config.governance_owner_queue_dir.glob("*.json"))
    assert incident_files
    assert queue_files

    payload = json.loads(incident_files[0].read_text(encoding="utf-8"))
    validator.validate("governance_incident", payload)
    assert payload["failure_type"] == "scope violation"


def test_illegal_state_transition_emits_governance_incident(evaluator, config):
    decision = evaluator.validate_transition(ArtifactStage.INCIDENT, ArtifactStage.EXECUTION, ActionClass.CLASS1, source_artifact_id="incident-001")
    assert decision.allowed is False
    assert decision.governance_failure_type == "illegal state transition"
    assert any(config.governance_incidents_dir.glob("*.json"))
    assert any(config.governance_owner_queue_dir.glob("*.json"))
