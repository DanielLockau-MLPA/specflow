# Decision log: model

Append-only. Entries are never edited or deleted.

## DL-001
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Is the L1 requirement set complete?
- decision: L1 review finished, no gaps found.
- rationale: User statement in session: content comprehensible, no gaps.
- affected: SR-001, SR-045

## DL-002
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Is the architecture model (with human confirmation and no dangling elements) acceptable?
- decision: Accepted after fixes: InputGuard ports, ConfirmationChannel, arrow direction convention (sender to receiver).
- rationale: Reviewed via generated diagrams; user said 'Looks good'.
- affected: DR-032, DR-024

## DL-005
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Approve gate G1?
- decision: baseline/G1 created as signed tag.
- rationale: Signature verified against approvals/keys, signer id_rsa_dl_devops_20250812. Signed tags are the approval record.
- affected: N-001

## DL-006
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Approve gate G2?
- decision: baseline/G2 created as signed tag.
- rationale: Signature verified against approvals/keys, signer id_rsa_dl_devops_20250812. Signed tags are the approval record.
- affected: DR-001

## DL-008
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Gate G1 approval by stakeholder roles (supersedes the baseline/G1 tag in DL-005..007)?
- decision: Approved: seven per-role signed tags approval/G1/<role> created; gate G1 open.
- rationale: Verified with approve.py status: all roles valid, no drift. Prototype: one person holds all roles (allow_single_person=true). Old baseline/* tags no longer count.
- affected: N-001

## DL-009
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Gate G2 approval by stakeholder roles (supersedes the baseline/G2 tag in DL-005..007)?
- decision: Approved: seven per-role signed tags approval/G2/<role> created; gate G2 open.
- rationale: Verified with approve.py status: all roles valid, no drift. Prototype: one person holds all roles (allow_single_person=true). Old baseline/* tags no longer count.
- affected: DR-001

## DL-011
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Adapt approved model and specs to the per-role signed-tag approval design?
- decision: Approvals are signed tags approval/<gate>/<role> (newer supersedes older); waivers are signed tags waiver/<rule>/<element>; the gate state is derived (no baseline tag); invalidation is at gate-scope level with impact analysis naming affected elements; evidence bundle per gate; G4 roles implementation-team, quality-management, information-security plus passing scenarios. Features 06-08 rewritten (08 renamed approval_integrity). Re-approval of G2 and G3 required.
- rationale: Implementation had diverged from element-level records in DR-012..DR-020; tags give tamper evidence and history with git alone and need no extra store.
- affected: DR-012, DR-014, DR-016, DR-018, SR-012

## DL-012
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA
- question: Gate G2 re-approval after the change to per-role signed tags (DL-011)?
- decision: Approved: seven per-role tags approval/G2/<role>.1 created; gate G2 open. Older unversioned tags are revision 0 and superseded.
- rationale: Verified with approve.py status after the model changes of DL-011: all roles valid, no drift. Prototype: one person holds all roles (allow_single_person=true).
- affected: DR-014

## DL-014
- date: 2026-10-26
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: How are approvals re-signed when content changes?
- decision: Approval tags are named approval/<gate>/<role>.<n>; an unversioned tag is revision 0; the newest valid revision per role counts; older revisions stay as history.
- rationale: A fixed tag name could not be re-signed without deleting evidence; the dot suffix avoids a git ref file/directory conflict with unversioned tags.
- affected: DR-012

## DL-017
- date: 2026-10-27
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: How are requirements traced to their sources?
- decision: Sources are SRC-nnn items (model/05_sources.sysml) raised by STK-nnn stakeholders; needs cite sources directly (tracing as high as possible), UC/SR/DR inherit via the trace chain. Rules need-sourced, source-stakeholder, source-cited, source-traceable.
- rationale: Requirements may have several sources; tracing at need level avoids duplication. docs/sources/project-brief.md needs owner confirmation at G1.
- affected: SR-017, DR-033, DR-034, N-005, N-008

## DL-018
- date: 2026-10-27
- type: review
- participants: DanielLockau-MLPA, AI agent
- question: Review findings: YAML remnant, drafts, waiver docs
- decision: YAML removed from DR-029 and specs (origin: early design); DRAFT markers removed from model docs; waivers documented in docs/waivers.md; delete of last element covered by a scenario.
- rationale: User review comments on the step implementation.
- affected: DR-029, SR-022, DR-028
