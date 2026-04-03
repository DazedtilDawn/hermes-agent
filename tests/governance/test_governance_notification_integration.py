from __future__ import annotations

import json

from .conftest import build_runtime


def test_new_incident_notification_attempt_happens_only_when_configured(governance_root):
    sent = []

    def sender(target, message):
        sent.append((target, message))

    runtime = build_runtime(
        governance_root,
        sender=sender,
        notify_on_new=False,
    )
    incident_path, queue_path = runtime["emitter"].emit(
        "scope violation",
        "Execution exceeded declared scope",
        {"incident_id": "incident-01", "chain_id": "chain-01"},
        source_artifact_id="incident-01",
        chain_id="chain-01",
    )

    assert sent == []
    assert incident_path.exists()
    assert queue_path.exists()
    assert list(runtime["config"].governance_notification_log_dir.glob("*.json")) == []


def test_new_incident_notification_failure_is_non_blocking(governance_root):
    def failing_sender(target, message):
        raise RuntimeError("messaging offline")

    runtime = build_runtime(governance_root, sender=failing_sender, notify_on_new=True)
    incident_path, queue_path = runtime["emitter"].emit(
        "authorization chain failure",
        "Class1 execution lacked a pre-approved playbook",
        {"incident_id": "incident-02", "chain_id": "chain-02"},
        source_artifact_id="incident-02",
        chain_id="chain-02",
    )

    assert incident_path.exists()
    assert queue_path.exists()

    incident_payload = json.loads(incident_path.read_text(encoding="utf-8"))
    assert incident_payload["notification_status"] == "failed"

    logs = list(runtime["config"].governance_notification_log_dir.glob("*.json"))
    assert len(logs) == 1
    log_payload = json.loads(logs[0].read_text(encoding="utf-8"))
    assert log_payload["delivered"] is False
    assert log_payload["error"] == "messaging offline"
