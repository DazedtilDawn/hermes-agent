from __future__ import annotations

from pathlib import Path

from .config import GovernanceConfig, build_config
from .governance_notifications import GovernanceNotificationManager


class GovernanceNotificationIntegration:
    def __init__(self, notification_manager: GovernanceNotificationManager, config: GovernanceConfig | None = None):
        self.notification_manager = notification_manager
        self.config = config or build_config()

    def notify_new_incident(self, incident: dict, queue_item: dict | None = None) -> dict | None:
        if not self.config.notify_on_new:
            return None
        body = f"{incident['summary']}\nqueue_state={incident['queue_state']}"
        if queue_item:
            body += f"\nqueue_id={queue_item['queue_id']}"
        return self.notification_manager.notify("governance:new", incident["failure_type"], body)

    def notify_queue_event(self, event_type: str, queue_payload: dict) -> dict | None:
        event_map = {
            "acknowledged": self.config.notify_on_ack,
            "resolved": self.config.notify_on_resolve,
            "dismissed": self.config.notify_on_dismiss,
            "queued": self.config.notify_on_requeue,
        }
        if not event_map.get(event_type, False):
            return None
        body = (
            f"queue_id={queue_payload['queue_id']}\n"
            f"incident_id={queue_payload['governance_incident_id']}\n"
            f"state={queue_payload['state']}"
        )
        return self.notification_manager.notify(f"governance:queue:{event_type}", queue_payload['governance_incident_id'], body)
