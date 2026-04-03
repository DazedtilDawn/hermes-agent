# Phase 3 Builder Checklist

Phase 3 is not about adding more governance-shaped structure. It is about making erosion harder.

Build against these failure modes:

- class1 authority creep
- verifier soft-approval drift
- novelty threshold relaxation
- ceremonial owner review
- archival rather than operational governance artifacts

## Lock class1 boundaries

- Define class1 in narrow, testable terms.
- Require reversibility to be explicit, not assumed.
- Enumerate allowed class1 playbook types explicitly.
- Enumerate disallowed usually-safe expansions.
- Fail closed on ambiguous class1 classification.

## Tighten novelty handling

- Define what counts as novelty in operational terms.
- Separate true novelty from known variants.
- Escalate on boundary uncertainty.
- Prevent threshold tuning that trades caution for throughput.
- Make novelty decisions inspectable after the fact.

## Harden verifier boundaries

- Ensure verifier can assess, reject, and route, but not authorize.
- Block any path where verifier output can function as practical approval.
- Test for nominally non-authorizing, functionally unblocking behavior.
- Keep verifier language and interfaces from implying authority it does not have.

## Strengthen anti-erosion tests

- Add tests for authority blur, not just happy-path lifecycle behavior.
- Add tests for temporary exceptions becoming persistent paths.
- Add tests for protected-surface downgrade attempts.
- Add tests for class1 playbook overreach.
- Add tests for novelty suppression under throughput pressure.

## Make owner review real

- Ensure queue items carry enough context for judgment.
- Keep queue entries concise, comparable, and decision-ready.
- Distinguish acknowledge, resolve, dismiss, and requeue clearly.
- Prevent queue flow from collapsing into procedural clearing.
- Optimize for correct decisions, not fast emptying.

## Make incidents operational

- Ensure governance incidents support diagnosis, not just storage.
- Preserve policy-relevant context in persisted artifacts.
- Make trends visible across incidents.
- Use incidents to refine policy boundaries and escalation rules.
- Avoid artifact formats that are durable but non-actionable.

## Protect the constitutional shape

- Keep governance external to execution.
- Keep protected surfaces blocking.
- Keep persistence upstream of notification.
- Keep notification best-effort and non-authorizing.
- Keep approval authority explicit and scarce.

## Done means

- class1 cannot quietly expand
- verifier cannot quietly approve
- novelty cannot quietly normalize
- owner review cannot quietly become ritual
- incidents cannot quietly become dead records
