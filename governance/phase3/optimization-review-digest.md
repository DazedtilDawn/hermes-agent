# Optimization Review Digest

The optimization review digest is the layer that makes the system legible to humans at the right altitude.

## Purpose

Lower layers produce many kinds of evidence:
- burn attribution snapshots
- burn intelligence recommendations
- cause hypotheses
- lane recommendation memory

The digest condenses these into a smaller set of review-worthy items so owner review can focus on repeated, consequential patterns rather than raw telemetry.

## What it should surface

- protected-lane risks
- repeated burn causes
- durable lane candidates
- top optimization recommendations when no stronger repeated pattern exists

## Why it matters

Without a digest, the system can become smart but hard to supervise. With a digest, recurring cost-quality signals become visible enough to drive explicit policy review.

## Guardrail

A digest is a review surface, not an authorization surface. Its job is to summarize recurring evidence, not to silently mutate routing or governance policy.
