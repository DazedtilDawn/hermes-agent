from __future__ import annotations

import json

from governance.controller.models import QueueState

from .conftest import build_runtime


def _emit_seed_incident(governance_root, sender=None, **config_overrides):
    runtime = build_runtime(governance_root, sender=sender, **config_overrides)
    incident_path, queue_path = runtime["emitter"].emit(
        "unauthorized execution",
        "Execution attempted without verification",
        {"incident_id": "seed-incident", "chain_id": "seed-chain"},
        source_artifact_id="seed-incident",
        chain_id="seed-chain",
    )
    return runtime, incident_path, queue_path


def test_lifecycle_mutation_persists_without_notification_when_policy_disables_it(governance_root):
    runtime, incident_path, queue_path = _emit_seed_incident(
        governance_root,
        notify_on_new=False,
        notify_on_ack=False,
        notify_on_resolve=False,
        notify_on_dismiss=False,
        notify_on_requeue=False,
    )

    payload = runtime["queue"].acknowledge(queue_path)
    assert payload["state"] == QueueState.ACKNOWLEDGED.value

    incident_payload = json.loads(incident_path.read_text(encoding="utf-8"))
    assert incident_payload["queue_state"] == QueueState.ACKNOWLEDGED.value
    assert list(runtime["config"].governance_notification_log_dir.glob("*.json")) == []


def test_lifecycle_mutation_sends_notification_when_policy_enables_it(governance_root):
    sent = []

    def sender(target, message):
        sent.append((target, message))

    runtime, incident_path, queue_path = _emit_seed_incident(
        governance_root,
        sender=sender,
        notify_on_new=False,
        notify_on_ack=True,
    )

    payload = runtime["queue"].acknowledge(queue_path)
    assert payload["state"] == QueueState.ACKNOWLEDGED.value
    assert len(sent) == 1
    assert "governance:queue:acknowledged" in sent[0][1]

    logs = list(runtime["config"].governance_notification_log_dir.glob("*.json"))
    assert len(logs) == 1
    log_payload = json.loads(logs[0].read_text(encoding="utf-8"))
    assert log_payload["delivered"] is True

    incident_payload = json.loads(incident_path.read_text(encoding="utf-8"))
    assert incident_payload["queue_state"] == QueueState.ACKNOWLEDGED.value


def test_requeue_notification_behavior_follows_policy(governance_root):
    sent = []

    def sender(target, message):
        sent.append((target, message))

    runtime, _, queue_path = _emit_seed_incident(
        governance_root,
        sender=sender,
        notify_on_new=False,
        notify_on_ack=False,
        notify_on_requeue=True,
    )

    runtime["queue"].acknowledge(queue_path)
    assert sent == []

    payload = runtime["queue"].requeue(queue_path, reason="owner requested renewed review")
    assert payload["state"] == QueueState.QUEUED.value
    assert payload["reason"] == "owner requested renewed review"
    assert len(sent) == 1
    assert "governance:queue:queued" in sent[0][1]


def test_notification_failure_remains_non_blocking_for_queue_persistence(governance_root):
    def failing_sender(target, message):
        raise RuntimeError("transport down")

    runtime, incident_path, queue_path = _emit_seed_incident(
        governance_root,
        sender=failing_sender,
        notify_on_new=False,
        notify_on_resolve=True,
    )

    payload = runtime["queue"].resolve(queue_path)
    assert payload["state"] == QueueState.RESOLVED.value

    persisted_queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert persisted_queue["state"] == QueueState.RESOLVED.value

    incident_payload = json.loads(incident_path.read_text(encoding="utf-8"))
    assert incident_payload["queue_state"] == QueueState.RESOLVED.value

    logs = list(runtime["config"].governance_notification_log_dir.glob("*.json"))
    assert len(logs) == 1
    log_payload = json.loads(logs[0].read_text(encoding="utf-8"))
    assert log_payload["delivered"] is False
    assert log_payload["error"] == "transport down"
