from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationResult:
    delivered: bool
    target: str
    message: str
    error: str | None = None


class HermesNotifier:
    def send(self, target: str, message: str) -> NotificationResult:  # pragma: no cover - interface
        raise NotImplementedError


def format_governance_message(event_type: str, title: str, body: str) -> str:
    return f"[{event_type}] {title}\n\n{body}"
