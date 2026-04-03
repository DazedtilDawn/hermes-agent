# Continuous Burn Optimization

This note defines how governance should use CodexBar telemetry and routing history to improve token management continuously without collapsing quality.

## Principle

Do not optimize for lower provider usage alone. Optimize for lower waste at acceptable quality.

That means the system should distinguish between:
- justified premium spend
- unjustified premium spend
- legitimate protective downgrades
- churn that hides process waste rather than solving it

## Current telemetry inputs

The governance layer can now observe:
- CodexBar provider usage windows
- routing state from `model-routing.json`
- routing swap history from `swap-log.jsonl`
- pressure history from `headroom-history.jsonl`
- lane classifications from `routing-governance.yaml`

## What should improve over time

### 1. Burn attribution by lane
Track which lanes are consuming scarce provider headroom during each window.

The first useful question is not exact token accounting. It is:
- which lane was routed to which provider/model while provider pressure increased?

That supports decisions such as:
- keep protected review lanes premium
- downgrade repetitive observers sooner
- investigate high-burn lanes with weak output value

### 2. Quality-aware downgrade suggestions
Do not recommend downgrades only because usage is high. Recommend them when all of the following are true:
- the lane is downgrade-eligible
- the work is low-value or repetitive
- premium usage is under pressure
- routing churn is not already indicating instability
- the lane is not constitutionally protected

### 3. Churn-aware optimization
If routing swaps happen frequently without pressure recovery, the system should shift from routing advice to process diagnosis.

Likely causes include:
- cron overfrequency
- retry storms
- repeated failing tasks
- prompt/context bloat
- premium models attached to low-value workflows

### 4. Protected-lane defense
If a protected lane is downgraded before its minimum allowed pressure mode, governance should treat that as a constitutional problem, not a clever optimization.

## What a mature recommendation should look like

The system should eventually be able to say:
- provider pressure is high
- these lanes are the main likely burn contributors in the current window
- these lanes are protected and should not be touched
- these lanes are downgrade candidates with low expected quality loss
- these lanes show churn or weak mitigation effect and need process correction rather than more swaps

That is the difference between token management and token governance.

## Guardrail

A cost-control system becomes dangerous when it silently converts scarcity into quality collapse. Governance should keep downgrade authority explicit, inspectable, and lane-aware.
