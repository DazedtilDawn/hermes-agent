# Operator Runbook: Live Class1 Gateway Restart Lane

This runbook explains what the governance layer does when the live `restart_dead_gateway` class1 lane fires, and what the human operator should check next.

## Scope

This runbook applies only to the narrow live class1 lane for:
- `playbook.restart_dead_gateway`

It does not apply to broader governance incidents, class2+ changes, or protected-surface mutations.

## Trigger condition

The live class1 lane may fire when:
- the governance shadow loop observes OpenClaw gateway unreachable
- the live launch agent has class1 restart enabled
- cooldown allows another restart attempt

The lane remains deterministic. It does not infer new authority beyond the pre-approved gateway restart playbook.

## What the system does

When the trigger condition is met, governance will:
1. emit an incident artifact proposing `restart_dead_gateway`
2. emit a verification artifact for the class1 candidate
3. if class1 restart is enabled and cooldown allows it:
   - attempt `openclaw gateway restart`
   - perform a post-restart health check
4. emit an execution artifact with one of these outcomes:
   - `executed`
   - `blocked`
5. send a notification to the configured owner-review surface

## How to read the outcome

### Outcome: executed
Meaning:
- governance attempted the restart
- post-check showed the gateway reachable afterward

What to do:
- confirm the recovery is stable, not transient
- inspect the latest controller decision and execution artifact
- watch for repeated restart attempts, which may indicate hidden churn rather than a single resolved failure

### Outcome: blocked
Meaning:
- governance attempted the restart and the post-check still failed
- or the restart attempt itself failed

What to do:
- treat this as requiring human review
- inspect the latest execution artifact notes
- inspect the gateway probe and recent OpenClaw logs
- do not assume repeated auto-retries are desirable; the cooldown exists to resist thrash

### Outcome: cooldown block
Meaning:
- the gateway was unreachable again, but governance refused to restart because the cooldown window had not elapsed

What to do:
- treat this as a repeated-failure signal
- review whether the prior restart actually addressed the root cause
- inspect for a persistent gateway failure mode rather than forcing more restarts

## Files to inspect

Primary artifact paths:
- `governance/reports/incidents/`
- `governance/reports/verifications/`
- `governance/reports/executions/`
- `governance/reports/governance-notifications/`
- `governance/reports/controller-decisions/openclaw_shadow_state.json`

Useful runtime logs:
- `governance/reports/controller-decisions/openclaw-shadow.stdout.log`
- `governance/reports/controller-decisions/openclaw-shadow.stderr.log`

## What not to conclude

Do not conclude that:
- a notification means governance succeeded
- a restart means the underlying issue is resolved
- repeated class1 restart attempts are acceptable just because the lane is pre-approved
- blocked execution means governance failed; often it means governance preserved the boundary correctly

## Escalation posture

Escalate beyond class1 when:
- the restart lane fires repeatedly within a short horizon
- blocked outcomes accumulate
- gateway restart restores service only briefly
- evidence suggests identity, configuration, secrets, or other protected surfaces may be implicated

At that point, the correct question is no longer whether the gateway can be restarted. The question is whether the failure mode still belongs inside class1 at all.
