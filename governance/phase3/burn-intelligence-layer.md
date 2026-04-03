# Burn Intelligence Layer

The burn-intelligence layer sits on top of burn-attribution snapshots and turns telemetry into optimization recommendations.

## Purpose

Burn attribution records state. Burn intelligence judges change.

That means it should answer questions like:
- did provider pressure improve after routing churn?
- are the same downgrade candidates appearing repeatedly?
- are we protecting the right lanes while relieving the right providers?
- is the system swapping aggressively without meaningful recovery?

## Current signals

The burn-intelligence collector currently evaluates:
- provider composite pressure deltas between snapshots
- routing churn without pressure recovery
- recurring lane candidates from repeated burn-insight patterns
- protected-lane downgrade recommendations
- provider-specific relief recommendations when pressure is elevated

## What it should eventually support

A mature version should recommend:
- durable routing policies for repeatedly expensive low-value lanes
- protected-lane exceptions only under explicit constitutional conditions
- process fixes when churn does not improve headroom
- quality-preserving downgrade sequences rather than blind provider relief

## Guardrail

If burn intelligence begins recommending quality loss without lane context, it has become a cost-cutting tool rather than a governance tool. The point is to reduce waste, not to normalize indiscriminate degradation.
