from __future__ import annotations

from governance.controller.hermes_notifier import format_governance_message
from governance.controller.hermes_send_adapter import HermesSendAdapter


def test_hermes_send_adapter_reports_delivery_success():
    sent = []

    def sender(target, message):
        sent.append((target, message))

    adapter = HermesSendAdapter(sender)
    result = adapter.send("telegram", "hello")

    assert result.delivered is True
    assert result.error is None
    assert sent == [("telegram", "hello")]


def test_hermes_send_adapter_reports_delivery_failure_without_raising():
    def sender(target, message):
        raise RuntimeError("send failed")

    adapter = HermesSendAdapter(sender)
    result = adapter.send("telegram", "hello")

    assert result.delivered is False
    assert result.error == "send failed"


def test_format_governance_message_is_stable():
    message = format_governance_message("governance:new", "scope violation", "body")
    assert message == "[governance:new] scope violation\n\nbody"
