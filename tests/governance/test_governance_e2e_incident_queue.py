from __future__ import annotations

import json

from .conftest import build_class1_chain, build_runtime


def test_e2e_governance_failure_emits_incident_queue_and_notification_log(governance_root):
    sent = []

    def sender(target, message):
        sent.append((target, message))

    runtime = build_runtime(governance_root, sender=sender, notify_on_new=True)
    incident, verification, execution = build_class1_chain()
    bad_verification = verification.model_copy(update={"chain_id": "wrong-chain"})

    decision = runtime["evaluator"].evaluate_execution(incident, bad_verification, execution=execution)
    assert decision.allowed is False
    assert decision.governance_failure_type == "unknown-chain artifact ingestion"

    incident_files = list(runtime["config"].governance_incidents_dir.glob("*.json"))
    queue_files = list(runtime["config"].governance_owner_queue_dir.glob("*.json"))
    notification_files = list(runtime["config"].governance_notification_log_dir.glob("*.json"))

    assert len(incident_files) == 1
    assert len(queue_files) == 1
    assert len(notification_files) == 1
    assert len(sent) == 1

    incident_payload = json.loads(incident_files[0].read_text(encoding="utf-8"))
    queue_payload = json.loads(queue_files[0].read_text(encoding="utf-8"))
    assert queue_payload["governance_incident_id"] == incident_payload["artifact_id"]
    assert incident_payload["notification_status"] == "sent"
