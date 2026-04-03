from __future__ import annotations

import json
from pathlib import Path

from governance.controller.ledgers import GovernanceLedgers
from governance.controller.models import ArtifactStage
from governance.controller.state_machine import assert_transition

from .conftest import build_class1_chain


def test_class1_fixture_chain_can_progress_and_close(config, validator, evaluator):
    incident, verification, execution = build_class1_chain()

    validator.validate("incident_report", incident.model_dump(mode="json"))
    validator.validate("verification_report", verification.model_dump(mode="json"))
    validator.validate("execution_report", execution.model_dump(mode="json"))

    assert_transition(ArtifactStage.INCIDENT, ArtifactStage.VERIFICATION, incident.action_class)
    assert_transition(ArtifactStage.VERIFICATION, ArtifactStage.EXECUTION, incident.action_class)
    assert_transition(ArtifactStage.EXECUTION, ArtifactStage.CLOSED, incident.action_class)

    pre_execution = evaluator.evaluate_execution(incident, verification)
    assert pre_execution.allowed is True
    assert pre_execution.next_stage == ArtifactStage.EXECUTION

    post_execution = evaluator.evaluate_execution(incident, verification, execution=execution)
    assert post_execution.allowed is True
    assert post_execution.next_stage == ArtifactStage.CLOSED


def test_fixture_directories_exist_with_expected_content(governance_root: Path):
    scenario = governance_root / "fixtures" / "scenario_a_class1_stale_scheduler" / "inputs" / "incident.json"
    payload = json.loads(scenario.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "incident_report"
    assert payload["action_class"] == "class1"
