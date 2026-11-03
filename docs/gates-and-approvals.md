# Gates and approvals

Approvals are **signed git tags**, one per required role. A gate has no stored state; it is derived each time from tags,
the scope content, the trace rules and, for G4, the recorded spec run.

## Configuration (protected from agents)

- `approvals/gates.json`: per gate the `scope` paths, the required `roles`, the `trace` stages and (G4) `scenarios: true`. `allow_single_person` lets one person hold all roles (prototype only).
- `approvals/roles.json`: principal (key file name) → roles.
- `approvals/keys/<principal>.pub`: the principal's SSH public key.

Agents cannot read or write `approvals/`. Files of an approved scope cannot be changed through `propose_edit` unless the operator unlocks the proposal branch ([how](agent-and-mcp.md#unlocking-a-proposal-branch)); the change then needs re-approval.

## Role names

`uv run python tools/approve.py roles` lists the exact names (kebab-case, for example `requirements-owner`, not the model's `RequirementsOwner`) and who holds them. Type them exactly as listed.

## Signing an approval

Each approver signs with their own key, outside any agent session. Setup once: `git config gpg.format ssh` and `git config user.signingkey <key>`.

```bash
uv run python tools/approve.py approve G2 --role reviewer -m "Reviewed model, findings in DL-012"
uv run python tools/approve.py status          # per role: valid, signer, revision, stale; problems; exit 1 if a gate is not open
```

- The tag is named `approval/<gate>/<role>.<n>`. `approve` creates the next revision `n`; an unversioned tag counts as revision 0.
- The scope must be committed first; the tag covers the scope content at the signed commit.
- The tool deletes a tag it created if the signature does not verify or the signer does not hold the role.
- Tag message = rationale. Signature = identity and date.

## When is a gate open?

All of these hold:

1. Every required role has a valid, newest-revision tag from a principal holding that role.
2. All tags cover the same scope content **and are on the same commit** (a gate revision).
3. The scope has not changed since that commit (no stale approvals).
4. The configured trace stages report no unwaived violation.
5. G4 only: a fresh spec run exists for the current state, and every scenario passed (`@manual` scenarios are skipped and attested by the approvers).
6. No unreviewed AI-authored commit touches the scope (commits with `AI-Authored-By:` or `Co-authored-by: Copilot` that are not covered by an approved commit).

Check: `uv run python tools/specflow.py gate G2 [--run] [--json]`; the report lists every problem.

## Railguard: functions no scenario executed (G4)

The spec says what must be in the implementation; the railguard (SR-018) finds what is in it without being specified.
`specrun` starts behave with `SPECFLOW_TRACE_DIR`; `tools/exectrace.py` (standard-library `sys.monitoring`, started by one import
in every entry point) records each function of `tools/` that is entered, in the behave process and in every subprocess,
and the merged list is stored in `.specflow/results/last_run.json`. This file is the recorded run evidence and is committed to the
repository (it is outside the model/specs fingerprint, so committing it does not invalidate the run). The G4 check compares it with a static inventory of all
functions in `tools/`; each function that was never entered keeps G4 closed unless `specs/railguard_allowlist.json`
lists it with a reason:

```json
{"entries": [{"function": "tools/approve.py:main", "reason": "interactive signing, covered by the manual scenario"}]}
```

The allowlist lies in the gated `specs/` scope, so the approvers review every exception. Entries without a reason are ignored,
entries for functions that no longer exist are reported as stale. Functions entered only by `pytest` do not count.
Enable the check with `"railguard": true` in the G4 entry of `approvals/gates.json`. Report on a trace directory:
`uv run python tools/exectrace.py report DIR [--json]`.

## Revisions and commits

- If approvers sign different commits, the gate stays closed: "approvals are on different commits; the newest revision X still needs: …". An approval on a later commit starts a new revision that every role must sign again.
- `approve --commit <sha>` signs an earlier commit of the current history, for example to join a stable baseline although work has continued. The earlier commit may have a different scope than HEAD; the gate then stays closed on the newer content until it is approved there.
- Re-approving after a change is simply the next `approve` call; old tags stay as history. You do not delete tags.

## Stale approvals and change control

When a scope changes, every approval of that gate reports `scope changed since approval`. Use `specflow impact <ID>` before changing an approved element to see which gates are affected. Scope commits should carry `Change-Reason:` (and `Approved-By:` when applicable) trailers; the audit query `changes` lists commits without them.

## Waivers

A waiver is a signed tag `waiver/<rule>/<element>.<n>` that accepts one trace gap until a date. See [waivers](waivers.md). Missing approvals, stale approvals, failing scenarios and unreviewed AI content cannot be waived.

## Enforcement outside the tooling

Tags are mutable in a local clone. On the git host install `tools/hooks/pre-receive` (bare repository, `hooks/pre-receive`) with a trust-anchor key directory (`SPECFLOW_KEYS_DIR`): `approval/*` and `waiver/*` tags can then only be created as annotated tags with a valid signature from a trusted key, and never moved or deleted. The hook does not yet check the signer's role; the gate evaluation does. The agent identity must have no credentials for these refs.

## Audit

```bash
uv run python tools/specflow.py audit G3 approvals      # tags, signers, revisions
uv run python tools/specflow.py audit G3 waivers
uv run python tools/specflow.py audit G3 changes        # commits and their trailers
uv run python tools/specflow.py audit G3 test-evidence  # recorded spec run per requirement
uv run python tools/specflow.py audit G3 integrity      # tampering and signature problems (exit 1 if not ok)
uv run python tools/specflow.py audit G3 bundle --out evidence-G3.json
```

The evidence bundle contains scope content hashes, approvals, waivers, spec results, trace status and tool versions. All audit queries run without the agent.
