from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_NOTIFICATION_TARGET = "telegram"
DEFAULT_NOTIFY_ON_NEW = True
DEFAULT_NOTIFY_ON_ACK = False
DEFAULT_NOTIFY_ON_RESOLVE = False
DEFAULT_NOTIFY_ON_DISMISS = False
DEFAULT_NOTIFY_ON_REQUEUE = True


@dataclass(frozen=True)
class GovernanceConfig:
    root_dir: Path
    reports_dir: Path
    incidents_dir: Path
    improvements_dir: Path
    verifications_dir: Path
    approvals_dir: Path
    approvals_queue_dir: Path
    executions_dir: Path
    controller_decisions_dir: Path
    governance_incidents_dir: Path
    governance_owner_queue_dir: Path
    governance_notification_log_dir: Path
    schema_dir: Path
    policy_dir: Path
    prompt_dir: Path
    fixtures_dir: Path
    notification_target: str = DEFAULT_NOTIFICATION_TARGET
    notify_on_new: bool = DEFAULT_NOTIFY_ON_NEW
    notify_on_ack: bool = DEFAULT_NOTIFY_ON_ACK
    notify_on_resolve: bool = DEFAULT_NOTIFY_ON_RESOLVE
    notify_on_dismiss: bool = DEFAULT_NOTIFY_ON_DISMISS
    notify_on_requeue: bool = DEFAULT_NOTIFY_ON_REQUEUE


def build_config(governance_root: Path | None = None) -> GovernanceConfig:
    base = (governance_root or Path(__file__).resolve().parents[1]).resolve()
    reports = base / "reports"
    return GovernanceConfig(
        root_dir=base,
        reports_dir=reports,
        incidents_dir=reports / "incidents",
        improvements_dir=reports / "improvements",
        verifications_dir=reports / "verifications",
        approvals_dir=reports / "approvals",
        approvals_queue_dir=reports / "approvals" / "queue",
        executions_dir=reports / "executions",
        controller_decisions_dir=reports / "controller-decisions",
        governance_incidents_dir=reports / "governance-incidents",
        governance_owner_queue_dir=reports / "governance-owner-queue",
        governance_notification_log_dir=reports / "governance-notifications",
        schema_dir=base / "schemas",
        policy_dir=base / "policy",
        prompt_dir=base / "prompts",
        fixtures_dir=base / "fixtures",
    )
