# Telemetry-Governed Quality and Cost Analysis

This note defines the next smart layer for governance-assisted token burn management.

## Core idea

Do not treat routing swaps as the first or only control surface. Use telemetry to answer three different questions:

1. Are we burning premium tokens where the work is low-value or repetitive?
2. Are routing swaps protecting headroom with acceptable quality loss, or just masking bad process behavior?
3. Are protected-quality lanes being downgraded without constitutional justification?

## Governance role

Governance should not replace the headroom engine or the router actuator.

Keep this split:
- headroom engine: measures provider pressure and writes routing proposals
- sovereign-router: enforces routing in-memory at request time
- governance: judges legitimacy, detects waste, flags erosion, and escalates protected-lane or churn cases

## First telemetry signals to govern

### Protected-lane downgrade detection
If a protected-quality lane is routed off its preferred model before its minimum allowed pressure mode, governance should emit an incident or at least a shadow observation.

### Premium burn on low-value lanes
If low-value or repetitive lanes still carry premium models while cheaper lanes have ample headroom, governance should flag likely waste.

### Routing churn
If agents are swapped too frequently in a short window, governance should treat that as a possible quality-loss-without-benefit pattern.

### Ineffective deficit mitigation
If the system remains in PROTECT or EMERGENCY over multiple windows despite swap activity, governance should suspect that the issue is not model routing alone. Likely alternatives include retry storms, cron overfrequency, prompt bloat, or low-value premium assignment.

## Smarter model-selection analysis

The useful next step is not a generic optimizer. It is telemetry-guided lane analysis.

For each lane, estimate:
- task value density
- quality sensitivity
- latency sensitivity
- repetition rate
- failure rate
- token burn rate
- downgrade tolerance

That lets governance support policies such as:
- protected review lanes keep a quality floor
- repetitive observers default cheap
- cheap-first lanes only escalate upward when quality evidence justifies it
- premium lanes require either protected status or demonstrated value

## What would make this say wow

A strong next version would produce lane recommendations like:
- "Praxis is paying premium cost during CRUISE while output quality signals justify it; keep protected."
- "Herald is using premium capacity on repetitive low-value work; downgrade candidate."
- "Scout swap churn is high with no headroom recovery; investigate process waste before further routing changes."
- "CRON observers should stay on cheap/default lanes unless failure-analysis quality drops."

That is better than blind cost-cutting because it couples quality protection to observed lane behavior.

## Guardrail

The system should never silently convert cost pressure into quality collapse. Any downgrade logic for protected lanes or ambiguous-quality work should remain explicit, inspectable, and escalation-capable.
