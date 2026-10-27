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

## DL-015
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: How are spec defects found during G4 step binding resolved, and how are non-automatable scenarios handled?
- decision: Features corrected (SR-004 upstream N-010, tag revision suffix, needs-stage trace example, key-file exception) and G3 re-signed. The SysON load scenario is tagged @manual: it runs skipped, and the G4 gate accepts skipped @manual scenarios, attested by the G4 approvers.
- rationale: Binding exposed wording defects; SysON has no import API to automate. Legacy baseline/G1..G3 tags deleted by the user.
- affected: SR-009, DR-027, SR-020, DR-029

## DL-016
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Manual scenario 'The model is loadable in a graphical modeling tool': does it hold?
- decision: Verified manually by the user on 2026-10-26: the SysML model files load into SysON.
- rationale: Evidence for the @manual scenario that the automated run skips; the G4 approvers attest it.
- affected: SR-009, DR-027

## DL-019
- date: 2026-10-27
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: How are approvals bound to commits?
- decision: All approvals of a revision must be on the same commit; a later-commit signature opens a new revision; --commit signs an earlier commit if the gate scope is unchanged since.
- rationale: Prevents mixing approvals of different states; supports repo moving forward during review.
- affected: DR-012, DR-014

## DL-020
- date: 2026-10-27
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Should signing an earlier commit be refused when the gate scope changed since?
- decision: No: approvers may sign an earlier commit (stable baseline) even if the scope changed; the gate stays closed at HEAD until approved on the newer content.
- rationale: Baselines mark stable versions that can be referenced; the derived gate state still protects HEAD. Supersedes the earlier refusal rule.
- affected: DR-012, SR-008
