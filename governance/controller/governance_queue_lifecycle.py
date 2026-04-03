from __future__ import annotations

from pathlib import Path

from .config import GovernanceConfig, build_config
from .ledgers import GovernanceLedgers
from .models import GovernanceIncident, GovernanceQueueItem, QueueState
from .utils import new_id, read_json, utc_now, write_json


class GovernanceQueueLifecycle:
    def __init__(
        self,
        config: GovernanceConfig | None = None,
        ledgers: GovernanceLedgers | None = None,
        notification_integration=None,
    ):
        self.config = config or build_config()
        self.ledgers = ledgers or GovernanceLedgers(self.config)
        self.notification_integration = notification_integration

    def create(self, incident: GovernanceIncident, incident_path: Path, reason: str) -> tuple[GovernanceQueueItem, Path]:
        now = utc_now()
        item = GovernanceQueueItem(
            queue_id=new_id("govq"),
            governance_incident_id=incident.artifact_id,
            governance_incident_path=str(incident_path),
            created_at=now,
            updated_at=now,
            state=QueueState.QUEUED,
            reason=reason,
        )
        path = self.ledgers.record_queue_item(item.model_dump(mode="json"))
        return item, path

    def acknowledge(self, queue_path: Path) -> dict:
        return self._transition(queue_path, QueueState.ACKNOWLEDGED)

    def resolve(self, queue_path: Path) -> dict:
        return self._transition(queue_path, QueueState.RESOLVED)

    def dismiss(self, queue_path: Path) -> dict:
        return self._transition(queue_path, QueueState.DISMISSED)

    def requeue(self, queue_path: Path, reason: str | None = None) -> dict:
        return self._transition(queue_path, QueueState.QUEUED, reason=reason)

    def _transition(self, queue_path: Path, new_state: QueueState, reason: str | None = None) -> dict:
        payload = read_json(queue_path)
        payload["state"] = new_state.value
        payload["updated_at"] = utc_now()
        if reason is not None:
            payload["reason"] = reason
        write_json(queue_path, payload)
        self._mirror_to_governance_incident(payload)
        self._notify_queue_event(payload)
        return payload

    def _mirror_to_governance_incident(self, queue_payload: dict) -> None:
        try:
            incident_path = Path(queue_payload["governance_incident_path"])
            incident_payload = read_json(incident_path)
            incident_payload["queue_state"] = queue_payload["state"]
            incident_payload["updated_at"] = utc_now()
            write_json(incident_path, incident_payload)
        except Exception:
            return

    def _notify_queue_event(self, queue_payload: dict) -> None:
        if self.notification_integration is None:
            return
        try:
            self.notification_integration.notify_queue_event(queue_payload["state"], queue_payload)
        except Exception:
            return
