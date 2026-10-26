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

## DL-007
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Approve gate G3?
- decision: baseline/G3 created as signed tag.
- rationale: Signature verified against approvals/keys, signer id_rsa_dl_devops_20250812. Signed tags are the approval record.
- affected: SR-014

## DL-010
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Gate G3 approval by stakeholder roles (supersedes the baseline/G3 tag in DL-005..007)?
- decision: Approved: seven per-role signed tags approval/G3/<role> created; gate G3 open.
- rationale: Verified with approve.py status: all roles valid, no drift. Prototype: one person holds all roles (allow_single_person=true). Old baseline/* tags no longer count.
- affected: SR-014

## DL-013
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Gate G3 re-approval after the rewritten features 06-08 (DL-011)?
- decision: Approved: seven per-role tags approval/G3/<role>.1 created; gate G3 open.
- rationale: Verified with approve.py status: all roles valid, no drift.
- affected: SR-014
