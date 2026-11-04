<!-- SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH -->
<!-- SPDX-License-Identifier: MIT -->

# Waivers

A waiver is a recorded, time-limited human decision to accept one trace gap (SR-015, DR-015, DR-018). It lets a gate open
although a trace rule reports a violation. Nothing else can be waived: missing approvals, stale approvals, failed
scenarios and unreviewed AI-authored content always keep a gate closed.

## When to use one

A trace check (`uv run python tools/specflow.py trace`) reports violations such as `need-covered N-003`. Normally you fix the
model or the specification. Waive only when the gap is known and accepted for a limited time, for example a need that a
later iteration will cover. The rationale must say why, the expiry says until when.

## Create a waiver

Waivers are signed by a person with their own SSH key (`git config gpg.format ssh`, `user.signingkey`), outside any agent session:

```bash
uv run python tools/approve.py waive need-covered N-003 \
  --rationale "Covered by a use case in iteration 3" --expiry 2027-03-31
```

This creates the signed tag `waiver/need-covered/N-003.1`. Running it again for the same rule and element creates `.2`,
`.3`, ...; the newest revision supersedes older ones, which stay in history. The element in the tag name has every
character outside letters, digits, `.`, `_` and `-` replaced by `_` (`file.feature:12` becomes `file.feature_12`).
The tag message holds the two fields the tools read:

```
rationale: <text>
expiry: YYYY-MM-DD
```

## When a waiver counts

All of these must hold, otherwise the waiver is reported as invalid (with the reason) and the gap stays open:

- the tag signature verifies against a public key in `approvals/keys/` (registered principal);
- the signer is not an agent identity (principal names starting with `agent`);
- the rationale is not empty;
- the expiry is a date in the future (an expired waiver stops counting automatically; renew it with a new revision).

The signer does not need a gate role. The waived rule and element must match the violation exactly.

## Where waivers show up

- `tracecheck.py`, `coverage_report.py` and `gate` list waived violations and valid and invalid waivers in every report.
- `uv run python tools/specflow.py audit G2 waivers` lists all waivers for a gate; the evidence bundle includes them.

## Ending a waiver

Fix the gap; the waiver then has no effect. Tags are retained as audit evidence. Deleting a tag is only possible on the
git host's admin side and is rejected by `tools/hooks/pre-receive`.
