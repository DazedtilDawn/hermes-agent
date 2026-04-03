# Hermes Governance Framework

This directory contains the first-pass Hermes-native governance scaffold used to monitor OpenClaw from outside the OpenClaw runtime.

## Boundary

- Hermes is the governing system.
- OpenClaw is the monitored target.
- Governance failures are separate from operational incidents.
- Runtime artifact persistence is primary.
- Notifications are downstream, best-effort side effects.

## Artifact conventions

- Runtime artifacts are JSON.
- Governance owner queue items are JSON.
- Static policy/configuration files are YAML.
- Role prompts are Markdown.
- Filenames are deterministic and lexicographically sortable by creation time.

Default runtime filename format:

`YYYYMMDDTHHMMSSZ_<artifact-type>_<artifact-id>.json`

## Roles

- Operator: executes approved actions only and never improvises.
- Auditor: detects incidents and proposes actions.
- Verifier: challenges Auditor reports and validates policy/risk.
- Owner: human authority for protected or high-risk changes.

## Policy posture

- `class0`: observe only
- `class1`: reversible operational hygiene only with a pre-approved playbook
- `class2+`: owner approval required
- protected surfaces are never auto-written
- novelty requires owner review

## Governance failures

The scaffold treats governance failures as first-class artifacts. The following failures emit governance incidents, enqueue owner review, and may trigger best-effort Hermes notifications:

- unknown-chain artifact ingestion
- illegal state transition
- approval scope mismatch
- authorization chain failure
- unauthorized execution
- scope violation
- unexpected protected-surface touch

## Policy source of truth in this first pass

This scaffold intentionally splits policy authority between YAML and explicit controller code.

YAML policy files currently provide:
- role definitions and intended authority boundaries
- protected surface inventory
- escalation classifications and taxonomy
- static constitutional reference material used by reviewers and future integrations

Controller / evaluator code currently remains the runtime law for:
- authorization-chain integrity checks
- class0/class1/class2+ execution gating
- novelty routing to owner review
- protected-surface blocking during execution
- scope enforcement
- governance incident emission
- queue lifecycle persistence ordering
- notification non-blocking behavior

Why the split exists right now:
- first-pass governance needs readable, deterministic enforcement more than a flexible rules engine
- protected boundaries are easier to audit when the decisive checks are explicit in code
- YAML is present now as stable constitutional input and future migration surface, not yet as a full dynamic policy engine

This means reviewers should not assume every YAML change automatically alters runtime behavior. In this first pass, YAML is partly normative reference and partly runtime input. The clearest runtime input today is `protected-surfaces.yaml`, which is loaded directly by the evaluator.

## Phase 3 packet

The accepted scaffold now includes a packaged Phase 3 operating set under `phase3/`.

Use it as follows:
- `phase3/executive-memo.md` — leadership framing
- `phase3/leadership-brief.md` — short circulation version
- `phase3/builder-checklist.md` — implementation tightening targets
- `phase3/red-team-note.md` — attack posture against erosion
- `phase3/failure-signatures.md` — ongoing monitoring lens
- `phase3/review-rubric.md` — review questions for future changes

## Layout

- `policy/`: constitutional source-of-truth YAML
- `schemas/`: JSON schemas for runtime artifacts
- `prompts/`: role prompts
- `controller/`: explicit file-backed orchestration helpers
- `collectors/`, `validators/`, `playbooks/`: integration surfaces and stubs
- `fixtures/`: deterministic fixture scenarios for tests
- `reports/`: persisted artifacts and ledgers
- `phase3/`: operating packet for preserving the governance shape under pressure

This scaffold intentionally avoids a database, dashboard, or heavyweight rules engine.
