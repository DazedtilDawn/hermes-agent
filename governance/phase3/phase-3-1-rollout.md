# Phase 3.1 Rollout Note

Phase 3.1 is the first live operating step after scaffold acceptance. The goal is not broad autonomous governance. The goal is to prove that the governance layer can observe real OpenClaw behavior, emit usable artifacts, and notify a real owner-review surface without expanding authority recklessly.

## Current live state

The OpenClaw shadow monitor is live.

Properties:
- mode: shadow only by default
- cadence: every 15 minutes
- execution authority: none by default
- notification surface: `discord:#approvals`
- artifact root: `governance/reports/`

Current signals:
- gateway reachability
- task failure growth
- stale-jobs observation signal

Current outputs:
- controller shadow run artifacts
- incident artifacts
- verification artifacts for gateway-restart class1 candidates
- governance notification logs
- shadow state file for deduping / recovery detection

## Deterministic class1 promotion path

A deterministic class1 promotion path now exists in code for `restart_dead_gateway`, but it is not enabled in the live launch agent by default.

Enablement conditions:
- explicit `--enable-class1-restart`
- cooldown window enforced
- post-restart health recheck required
- blocked execution artifact emitted if recovery fails
- owner review remains required on unsuccessful restoration

This keeps the first promoted class1 lane narrow, inspectable, and reversible.

## Why this order

This rollout preserves the constitutional asymmetry:
- observation is live
- escalation is live
- persistence is live
- notification is live
- execution remains constrained off by default

That means the system is now learning from real OpenClaw conditions without silently absorbing broad operational authority.

## Promotion gates before enabling the class1 lane live

Do not enable the class1 restart lane in the live launch agent until all of the following are true:

1. Signal quality is acceptable
- shadow alerts are not obviously noisy
- false positives are understood
- owner-review notifications are readable and decision-usable

2. Boundary definitions are explicit
- the trigger condition for gateway-unreachable is stable
- cooldown and retry limits are explicit
- post-check criteria are explicit
- blocked outcomes remain escalatory rather than self-normalizing

3. Anti-erosion protections exist
- tests cover cooldown bypass attempts
- tests cover protected-surface surprise
- tests cover verifier drift and operator improvisation risk
- novelty still routes to owner review rather than bypassing it

4. Owner review remains real
- queue and alert surfaces are being watched
- owner decisions are distinguishable from procedural acknowledgment
- recovery signals are meaningful, not ceremonial

## Recommended first promotion candidate

If a single class1 lane is promoted first, prefer:
- `restart_dead_gateway`

Why:
- narrow operational target
- clearly reversible relative to broader state changes
- naturally tied to an observable health signal
- easy to hard-gate behind cooldown and post-check logic

## What not to do in Phase 3.1

- do not widen class1 while the first live lane is still unproven
- do not normalize verifier output into practical approval
- do not use queue volume reduction as proof of governance quality
- do not treat notifications as governance success
- do not convert temporary operational shortcuts into standing behavior

## Success condition

Phase 3.1 succeeds when the live governance loop becomes trustworthy as an observer and escalator before it becomes trusted as an actor.
