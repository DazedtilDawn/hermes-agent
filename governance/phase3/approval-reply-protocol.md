# Approval Reply Protocol

The first real approval path is text-gated, not silent.

## Why this exists

Interactive buttons are desirable, but the critical thing is not the button. It is the explicit owner decision. The reply protocol makes optimization proposals actionable now while preserving clear human authority.

## Supported replies

Use these replies in the owner-review channel after a proposal request appears:

- `APPROVE <artifact>`
- `ALT <artifact> <model>`
- `REJECT <artifact>`
- `SNOOZE <artifact> <minutes>`

Examples:
- `APPROVE 20260403T120000Z_optimization_proposal_optprop-abc123.json`
- `ALT 20260403T120000Z_optimization_proposal_optprop-abc123.json minimax-portal/MiniMax-M2.7`
- `REJECT 20260403T120000Z_optimization_proposal_optprop-abc123.json`
- `SNOOZE 20260403T120000Z_optimization_proposal_optprop-abc123.json 30`

## Current behavior

When an approval reply is detected, governance can:
- apply the recommended model change
- apply an approved alternative model
- record a rejection
- record a snooze

## Guardrail

This reply protocol is still approval-gated governance. It is not a silent optimizer. The system proposes. The owner decides. Routing changes only happen after an explicit command.
