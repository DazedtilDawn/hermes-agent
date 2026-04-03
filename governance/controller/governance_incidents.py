from __future__ import annotations

from pathlib import Path

from .config import GovernanceConfig, build_config
from .governance_notification_integration import GovernanceNotificationIntegration
from .governance_queue_lifecycle import GovernanceQueueLifecycle
from .ledgers import GovernanceLedgers
from .models import GovernanceIncident, GovernanceSeverity
from .schema_validator import SchemaValidator
from .utils import new_id, read_json, utc_now, write_json


SEVERITY_BY_FAILURE = {
    "unknown-chain artifact ingestion": GovernanceSeverity.HIGH,
    "illegal state transition": GovernanceSeverity.HIGH,
    "approval scope mismatch": GovernanceSeverity.HIGH,
    "authorization chain failure": GovernanceSeverity.HIGH,
    "unauthorized execution": GovernanceSeverity.CRITICAL,
    "scope violation": GovernanceSeverity.CRITICAL,
    "unexpected protected-surface touch": GovernanceSeverity.CRITICAL,
}


class GovernanceIncidentEmitter:
    def __init__(
        self,
        config: GovernanceConfig | None = None,
        ledgers: GovernanceLedgers | None = None,
        queue: GovernanceQueueLifecycle | None = None,
        validator: SchemaValidator | None = None,
        notification_integration: GovernanceNotificationIntegration | None = None,
    ):
        self.config = config or build_config()
        self.ledgers = ledgers or GovernanceLedgers(self.config)
        self.notification_integration = notification_integration
        self.queue = queue or GovernanceQueueLifecycle(self.config, self.ledgers, self.notification_integration)
        self.validator = validator or SchemaValidator(self.config)

    def emit(
        self,
        failure_type: str,
        summary: str,
        details: dict,
        *,
        source_artifact_id: str | None = None,
        chain_id: str | None = None,
        severity: GovernanceSeverity | None = None,
    ) -> tuple[Path, Path]:
        incident = GovernanceIncident(
            artifact_id=new_id("govinc"),
            created_at=utc_now(),
            chain_id=chain_id,
            source_artifact_id=source_artifact_id,
            failure_type=failure_type,
            severity=severity or SEVERITY_BY_FAILURE[failure_type],
            summary=summary,
            details=details,
        )
        self.validator.validate("governance_incident", incident.model_dump(mode="json"))
        incident_path = self.ledgers.record_governance_incident(incident)
        queue_item, queue_path = self.queue.create(incident, incident_path, reason=summary)

        if self.notification_integration is not None:
            try:
                result = self.notification_integration.notify_new_incident(
                    read_json(incident_path), queue_item.model_dump(mode="json")
                )
            except Exception:
                result = None
            if result is not None:
                payload = read_json(incident_path)
                payload["notification_status"] = "sent" if result["delivered"] else "failed"
                write_json(incident_path, payload)

        return incident_path, queue_path
