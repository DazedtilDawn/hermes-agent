# Approval-Gated Optimization

This layer turns recurring cost-quality evidence into explicit review requests rather than silent routing changes.

## Purpose

The system should help manage token burn across CRUISE, CONSERVE, PROTECT, and EMERGENCY without quietly converting cost pressure into hidden authority. Approval-gated optimization keeps the human in the loop while still making the machine useful.

## Current shape

The optimization proposal layer now produces:
- mode-aware proposals
- recommended lane/model change
- alternative model choices
- supporting recommendation or digest context
- explicit note when a protected lane requires owner approval

## Intended workflow

1. Burn and routing telemetry produce recommendations.
2. Governance condenses those into an optimization proposal artifact.
3. The system sends a human-usable approval request message.
4. The owner can approve the recommended change, choose an alternative, reject, or snooze.
5. Only after approval should a future apply-path mutate routing.

## Guardrail

Proposal generation is not approval. Approval messaging is not execution. This layer exists to package decisions cleanly while preserving explicit human authority over routing changes.
