from __future__ import annotations

from .config import GovernanceConfig, build_config
from .hermes_notifier import HermesNotifier, format_governance_message
from .ledgers import GovernanceLedgers
from .utils import new_id, utc_now


class GovernanceNotificationManager:
    def __init__(self, notifier: HermesNotifier, config: GovernanceConfig | None = None, ledgers: GovernanceLedgers | None = None):
        self.config = config or build_config()
        self.ledgers = ledgers or GovernanceLedgers(self.config)
        self.notifier = notifier

    def notify(self, event_type: str, title: str, body: str) -> dict:
        message = format_governance_message(event_type, title, body)
        result = self.notifier.send(self.config.notification_target, message)
        log_payload = {
            "event_id": new_id("govnotify"),
            "created_at": utc_now(),
            "event_type": event_type,
            "target": self.config.notification_target,
            "delivered": result.delivered,
            "error": result.error,
            "message": message,
        }
        self.ledgers.record_notification_log(log_payload)
        return log_payload
