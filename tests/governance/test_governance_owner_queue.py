from __future__ import annotations

import json

from governance.controller.models import QueueState

from .conftest import build_runtime


def test_owner_queue_item_is_created_for_governance_incident(governance_root):
    runtime = build_runtime(governance_root, notify_on_new=False)
    incident_path, queue_path = runtime["emitter"].emit(
        "illegal state transition",
        "Execution was attempted directly from incident state",
        {"current": "incident", "next": "execution", "action_class": "class1"},
        source_artifact_id="incident-03",
        chain_id="chain-03",
    )

    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    assert queue_payload["governance_incident_id"]
    assert queue_payload["state"] == QueueState.QUEUED.value
    assert queue_payload["governance_incident_path"] == str(incident_path)


def test_owner_queue_lifecycle_helpers_update_state_and_mirror(governance_root):
    runtime = build_runtime(governance_root, notify_on_new=False)
    incident_path, queue_path = runtime["emitter"].emit(
        "scope violation",
        "Execution exceeded declared scope",
        {"incident_id": "incident-04", "chain_id": "chain-04"},
        source_artifact_id="incident-04",
        chain_id="chain-04",
    )

    runtime["queue"].acknowledge(queue_path)
    runtime["queue"].dismiss(queue_path)

    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    incident_payload = json.loads(incident_path.read_text(encoding="utf-8"))
    assert queue_payload["state"] == QueueState.DISMISSED.value
    assert incident_payload["queue_state"] == QueueState.DISMISSED.value
