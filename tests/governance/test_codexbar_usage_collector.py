from __future__ import annotations

from governance.collectors.codexbar_usage import _parse_codexbar_output


def test_parse_codexbar_output_uses_first_json_array_only():
    stdout = (
        '[{"provider":"codex","source":"codex-cli","usage":{"updatedAt":"2026-04-03T04:43:49Z","primary":{"usedPercent":11,"windowMinutes":300}}}]\n'
        '[{"provider":"cli","source":"cli","error":{"message":"Error"}}]\n'
    )
    payload = _parse_codexbar_output(stdout)
    assert len(payload) == 1
    assert payload[0]['provider'] == 'codex'
