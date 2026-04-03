# Phase 3 Review Rubric

Use this rubric to review governance changes, tests, playbooks, queue behavior, and operator surfaces during Phase 3.

## Review lens

Do not review only for correctness or implementation neatness. Review for erosion pressure:
- Is low-friction authority expanding?
- Are escalation triggers being downgraded?
- Is the appearance of governance being preserved while real constraint weakens?

## Authority and class boundaries

Questions:
- Does this change widen class1 in practice, even if class definitions are unchanged on paper?
- Is reversibility explicit, testable, and artifact-backed, or merely asserted?
- Can verifier output now function as practical approval?
- Does any operator path gain room for inference, discretion, or trusted improvisation?

Fail signals:
- class1 justified by familiarity or confidence rather than narrow reversible scope
- verifier validation treated as enough to proceed
- temporary authority exceptions left available after the triggering case ends
- approval authority becoming implicit instead of explicit

## Escalation and novelty

Questions:
- Does this change weaken novelty handling to reduce friction or queue load?
- Are ambiguous cases escalated or forced into familiar buckets?
- Are escalation triggers becoming harder to fire without a formal constitutional reason?

Fail signals:
- novelty reclassified downward without a principled boundary
- throughput used as justification for escalation relaxation
- uncertainty routed toward execution instead of owner review

## Protected surfaces and blocking behavior

Questions:
- Do protected surfaces still block, or are they being reframed as incidental, operational, or metadata-only?
- Does this change preserve hard-stop behavior when protected surfaces are touched unexpectedly?

Fail signals:
- protected touches downgraded to warnings
- policy language weakened without explicit constitutional decision
- relabeling used to bypass stronger controls

## Queue and owner review quality

Questions:
- Does the queue still support real judgment, or is it optimized for clearing speed?
- Do queue items carry enough context to support correct decisions?
- Are acknowledge, resolve, dismiss, and requeue still meaningfully distinct?

Fail signals:
- queue health measured mainly by emptiness or speed
- low-context queue items that force guesswork
- owner review becoming procedural acknowledgment instead of judgment

## Incident quality and learning value

Questions:
- Do governance incidents support diagnosis, pattern detection, and policy learning?
- Are recurring incident families causing policy or playbook improvement?
- Is artifact quality improving future control, or only preserving history?

Fail signals:
- repeated incident families with no boundary tightening
- incidents that are durable but not actionable
- more archival completeness than operational usefulness

## Audit versus control

Questions:
- Does this change strengthen pre-action constraint or mostly improve post-action explainability?
- Is the system becoming easier to justify than to control?

Fail signals:
- audit language stronger than control language
- message delivery or notification success treated as evidence of governance success
- narratives compensating for weak constraints

## Review-complete standard

A Phase 3 change is healthy if it makes the system harder to reinterpret under pressure. A change is suspect if it makes the system easier to widen, downgrade, excuse, or bypass while preserving the appearance of discipline.
