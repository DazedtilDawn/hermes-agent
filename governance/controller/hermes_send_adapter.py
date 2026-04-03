from __future__ import annotations

from collections.abc import Callable

from .hermes_notifier import HermesNotifier, NotificationResult


class HermesSendAdapter(HermesNotifier):
    def __init__(self, sender: Callable[[str, str], object] | None = None):
        self.sender = sender

    def send(self, target: str, message: str) -> NotificationResult:
        if self.sender is None:
            return NotificationResult(delivered=False, target=target, message=message, error="sender_not_configured")
        try:
            self.sender(target, message)
            return NotificationResult(delivered=True, target=target, message=message, error=None)
        except Exception as exc:  # pragma: no cover - exercised via tests with fake sender if needed
            return NotificationResult(delivered=False, target=target, message=message, error=str(exc))
