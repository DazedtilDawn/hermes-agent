# Burn Cause Hypotheses

Burn intelligence says what pattern is visible. Burn cause hypotheses say what is probably causing it.

## Purpose

This layer exists to keep the system from stopping at generic optimization advice.

Examples:
- routing churn without headroom recovery
- low-value premium burn
- retry or timeout waste
- quality-floor risk on protected lanes
- swap-policy instability

## Why it matters

A system that only recommends cheaper models can become a clever degradation engine. A system that names likely causes can suggest the right class of intervention:
- routing change
- lane downgrade
- cron reduction
- retry cleanup
- queue/process investigation
- quality protection

## Constraint

Cause hypotheses are still observational. They should guide human review and future policy tuning before they are allowed to trigger stronger automation.
