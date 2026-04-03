from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import GovernanceConfig, build_config
from .utils import artifact_filename, ensure_dir, model_to_dict, write_json


class GovernanceLedgers:
    def __init__(self, config: GovernanceConfig | None = None):
        self.config = config or build_config()
        for directory in [
            self.config.incidents_dir,
            self.config.improvements_dir,
            self.config.verifications_dir,
            self.config.approvals_dir,
            self.config.approvals_queue_dir,
            self.config.executions_dir,
            self.config.controller_decisions_dir,
            self.config.governance_incidents_dir,
            self.config.governance_owner_queue_dir,
            self.config.governance_notification_log_dir,
        ]:
            ensure_dir(directory)

    def persist_artifact(self, artifact: Any, directory: Path) -> Path:
        payload = model_to_dict(artifact)
        filename = artifact_filename(payload["created_at"], payload["artifact_type"], payload["artifact_id"])
        return write_json(directory / filename, payload)

    def record_incident(self, artifact: Any) -> Path:
        return self.persist_artifact(artifact, self.config.incidents_dir)

    def record_verification(self, artifact: Any) -> Path:
        return self.persist_artifact(artifact, self.config.verifications_dir)

    def record_approval(self, artifact: Any) -> Path:
        return self.persist_artifact(artifact, self.config.approvals_dir)

    def record_execution(self, artifact: Any) -> Path:
        return self.persist_artifact(artifact, self.config.executions_dir)

    def record_controller_decision(self, payload: dict[str, Any]) -> Path:
        filename = artifact_filename(payload["created_at"], payload["artifact_type"], payload["artifact_id"])
        return write_json(self.config.controller_decisions_dir / filename, payload)

    def record_governance_incident(self, artifact: Any) -> Path:
        return self.persist_artifact(artifact, self.config.governance_incidents_dir)

    def record_queue_item(self, payload: dict[str, Any]) -> Path:
        filename = artifact_filename(payload["created_at"], "governance_queue_item", payload["queue_id"])
        return write_json(self.config.governance_owner_queue_dir / filename, payload)

    def record_notification_log(self, payload: dict[str, Any]) -> Path:
        filename = artifact_filename(payload["created_at"], "governance_notification", payload["event_id"])
        return write_json(self.config.governance_notification_log_dir / filename, payload)
