# Phase 3 Red-Team Note

Phase 3 failure is unlikely to arrive as open abandonment of governance. It is more likely to arrive disguised as practicality.

Most erosion attacks take one of three forms:
- expand low-friction authority
- downgrade escalation triggers
- preserve the appearance of governance while weakening real constraint

Assume the system will be pressured in the following ways:

## Class1 expansion pressure

Operational users will want more actions routed through class1 because class1 is faster, less burdensome, and easier to operationalize. The most dangerous proposals will sound reasonable:
- this is basically reversible
- we have done this before
- this is low-risk in practice
- this should not need owner review every time

Red-team question:
Can class1 be widened without anyone explicitly deciding to widen it?

## Verifier authority drift

The verifier is supposed to challenge and route, not authorize. In practice, systems drift when verifier outputs become trusted enough that downstream actors treat them as practical approval.

Red-team question:
Can a verifier decision become the functional equivalent of approval even if the formal model says otherwise?

## Novelty suppression pressure

Novelty is one of the last defenses against self-normalization. Under throughput pressure, teams will try to classify more cases as familiar variants rather than genuinely novel events.

Red-team question:
Can novelty be reinterpreted downward to avoid escalation load?

## Queue ritualization

Owner review can remain technically present while becoming operationally empty. This happens when queues become noisy, context-poor, or optimized for clearing speed rather than decision quality.

Red-team question:
Can owner review remain procedurally active while substantively absent?

## Protected-surface softening

Protected surfaces are rarely attacked head-on. More often, they are reframed:
- this is not really a protected change
- this is only metadata
- this is operational, not constitutional
- this touch is incidental

Red-team question:
Can protected-surface blocking be bypassed by relabeling the nature of the touch?

## Exception-path normalization

Temporary exceptions are a common vehicle for erosion. A one-off bypass created under urgency can quietly become precedent.

Red-team question:
Can a temporary governance exception become a stable path without a formal decision to make it one?

## Incident archival drift

A governance incident system can appear healthy while doing very little if incidents are persisted but not used to refine policy, detect patterns, or surface recurring boundary stress.

Red-team question:
Are governance incidents improving future control, or only recording past discomfort?

## Notification illusion

Notifications are secondary by design, but systems sometimes begin treating successful notification as evidence that governance occurred. That is a category error.

Red-team question:
Could messaging success be mistaken for governance success?

## Audit substitution

A common institutional failure mode is replacing prevention with explainability. Once that happens, the system becomes easier to justify after action than to constrain before action.

Red-team question:
Are we preserving pre-action control, or drifting toward post-action storytelling?

## Vocabulary drift

Governance weakens when key terms remain formally unchanged but loosen in practice. Words like reversible, novel, protected, incidental, and pre-approved are all erosion surfaces.

Red-team question:
Can constitutional terms be softened in practice without ever being formally redefined?

## What to attack deliberately in Phase 3 testing

- ambiguous class1 cases
- verifier outputs that strongly imply downstream action
- novelty edge cases under throughput pressure
- queue overload and low-context queue items
- protected-surface relabeling attempts
- emergency exception paths
- repeated governance incidents of the same family
- workflows where audit language appears stronger than control language
- definition drift around core constitutional terms

## Success standard

Phase 3 succeeds if the governance layer remains difficult to reinterpret under pressure. It fails if the system still looks governed while becoming easier to bypass, downgrade, or excuse.

## Bottom line

The red-team objective is not to prove that rules can be broken. Of course they can. The objective is to find where the system invites erosion while still preserving the appearance of discipline. That is the failure mode most worth attacking now.
