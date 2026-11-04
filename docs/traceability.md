<!-- SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH -->
<!-- SPDX-License-Identifier: MIT -->

# Traceability
Traceability connects requirement sources to executable evidence. It is computed from the model text and the feature
files; nothing is stored separately.

## Chain

```
Source (SRC) ── cites ──▶ Need (N) ◀── covers ── Use case (UC) ── exercises ──▶ L1 requirement (SR)
                                                                  SR ── derives ──▶ N
L2 requirement (DR) ── derives ──▶ SR        DR ◀── satisfy ── design element (part)
Scenario ── tag @SR-nnn @DR-nnn ──▶ requirement it verifies
Source ── raisedBy ──▶ Stakeholder (STK)
```

Tracing happens **as high as possible**: needs cite sources directly; use cases, SRs and DRs inherit their sources by
following `covers`, `derives` and `cites` links. A requirement may have several sources.

## IDs

| Prefix | Element | Defined in |
|---|---|---|
| `STK-nnn` | stakeholder | `model/00_needs.sysml` |
| `N-nnn` | need | `model/00_needs.sysml` |
| `SRC-nnn` | requirement source | `model/05_sources.sysml` |
| `UC-nn` | use case | `model/10_use_cases.sysml` |
| `SR-nnn` | system (L1) requirement | `model/20_system_requirements.sysml` |
| `DR-nnn` | design (L2) requirement | `model/30_design_requirements.sysml` |

IDs are SysML short names (`<'SR-004'>`), never reused and never renumbered. `uv run python tools/specflow.py id check SR-100` tells whether a new ID is acceptable (right format, unused). Deleted IDs stay retired.

## Link statements

Links are plain SysML dependencies whose name carries the relation: `dependency 'DR-012 derives SR-008' from <DR name> to <SR name>;`.
Verbs: `cites`, `raisedBy`, `covers`, `exercises`, `derives`. Allocation uses SysML `satisfy <requirement> by <part path>;`. The validator does not interpret the verbs; the trace service does.

## Rules

Violations are reported per stage by `uv run python tools/specflow.py trace --stage <stage>`.

| Stage | Rule | Violation when |
|---|---|---|
| needs | `need-covered` | no use case covers the need |
| needs | `need-sourced` | a need cites no source |
| needs | `source-stakeholder` | a source names no stakeholder |
| needs | `source-cited` | no need cites a source |
| model | `usecase-exercises` | a use case exercises no requirement |
| model | `l1-derives-need` | an SR derives from no need |
| model | `l2-derives-l1` | a DR derives from no SR |
| model | `l2-allocated` | a DR is satisfied by no design element |
| model | `source-traceable` | a UC, SR or DR reaches no source through covers/derives/cites |
| model | `link-target-exists` | a link names an unknown ID |
| spec | `scenario-tagged` | a scenario has no ID tag |
| spec | `tag-valid` | a tag names an unknown ID |
| spec | `requirement-verified` | an SR or DR has no scenario |
| refs | `link-dangling`, `link-stale` | a link target is missing, or changed since the gate approval (not part of `all`) |

A gate evaluates the stages in its configuration. A violation can be waived by a human with a signed, time-limited waiver ([waivers](waivers.md)); it then stays visible in reports.

## Queries and reports

- `uv run python tools/specflow.py coverage --format markdown` shows per level how many elements are covered, plus scenario counts.
- `uv run python tools/specflow.py impact SR-004` lists upstream and downstream elements, scenarios and gates whose approvals would become stale.
- The MCP tool `trace(element_id)` (model server) answers "what does this element trace to?" in both directions, and prefix targets work (`DR-002` → `SRC`, `SRC-002` → `STK`).
- `docs/diagrams.md` contains generated views of the chain (need → UC, need → L1, UC → L1, L1 → L2, allocation).
