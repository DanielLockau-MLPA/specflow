# Decision log: spec

Append-only. Entries are never edited or deleted.

## DL-003
- date: 2026-10-26
- type: qa
- participants: DanielLockau-MLPA, AI agent
- question: Which executable spec technology?
- decision: behave (Gherkin) chosen over pytest-bdd.
- rationale: Native --dry-run, hyphenated ID tags without mark warnings, JSON output with tags.
- affected: DR-009

## DL-004
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Are the feature documents acceptable as G3 draft?
- decision: Reviewed by user: readable, relate well to the model, no corrections.
- rationale: User statement in session. Formal G3 approval is not yet recorded (approval tooling not built).
- affected: SR-014
