# Retrospective (iteration 1)

The model and specs describe this toolchain itself. This document lists what worked, what did not, and the
candidates for iteration 2. It is input for the next planning round, not a decision.

## State at the end of iteration 1

| Item | Result |
|---|---|
| Model | 5 files, parser reports 0 syntax and 0 semantic errors |
| Architecture | 21 parts, 46 connections, 34 allocations, all 32 DRs allocated |
| Trace | 0 violations on all gates; every L1/L2 requirement has a scenario, every scenario a valid ID tag |
| Specs | 76 scenarios (118 with outlines), run as pending stubs; no step is bound |
| MCP | model and spec servers with workspace guards, confirmation, decision log, prompts; 12 tests |
| Decisions | 4 entries logged (`decisions/`), reviewed by the human |

## What worked

- Text-first `.sysml` in git: reviewable diffs, free parsing, generated diagrams.
- Stable IDs plus scenario tags made coverage a script, not a judgement.
- Dogfooding found real defects early: ports missing on `InputGuard`, dangling elements, inconsistent arrow
  directions, an unreadable single diagram, and module names shadowing `trace`/`coverage`.
- Human confirmation through MCP elicitation fails closed when the client cannot elicit.

## Gaps and findings

| # | Finding | Impact | Iteration-2 candidate |
|---|---|---|---|
| 1 | Approval and gates are not implemented: baselines are plain git tags, unsigned, with no content hash | G1-G4 are conventions, not enforced; SR-012 (approval reset) is untested in practice | ApprovalService, GateEvaluator, signed tags, hash-based drift detection |
| 2 | Trace relations are `dependency` names parsed by our own regex; the validator ignores them | Fragile; a renamed pattern silently drops links | Typed trace metadata in the model |
| 3 | `arch.py` reads the model with regexes, not a parser | Syntax outside our conventions is missed | Use parser output (sysml-mcp symbols) or the OMG API |
| 4 | Validator warns on 38 unsatisfied and 69 unverified requirements | Noise hides real warnings | Model `verify` relations to scenarios, or filter known warnings |
| 5 | Use cases and needs have no acceptance scenarios | Top of the trace chain is only checked structurally | UC acceptance scenarios |
| 6 | Specs are not executable: catch-all pending steps | G4 evidence is missing; the pending stub conflicts with real steps | Bind steps from `docs/step_vocabulary.md`, drop `pending.py` at G4 |
| 7 | Gate coverage covers trace rules only, not spec run results | A failing scenario would not block a gate | Merge `run` results into the gate report |
| 8 | Decision log stages are limited to `model` and `spec`; no stage for requirements/G1 | L1 review had to be logged under `model` | Add stages or a generic scope |
| 9 | Elicitation needs a stateful MCP connection; stateless clients are always refused | Safe, but some clients cannot use state-changing tools | Document client requirements; consider a separate review CLI |
| 10 | No ReviewCli/audit query for approvals and decisions | Auditors read raw files | Implement the audit view |
| 11 | Not cross-checked against the OMG Pilot Implementation; SysON swimlane rendering and REST write access unconfirmed | Conformance risk with the third-party parser | Cross-check; try SysON import |
| 12 | `docs/diagrams.html` is untracked | Viewing file only | Decide: ignore or track |
| 13 | `npm audit`: 2 low advisories in dev tooling | Unreviewed | Review |
| 14 | Threat modeling is out of scope; security constraints are the only security content | Contradicts the original goal of reusable threat input | Decide whether to add a threat package |

## Process observations

- Human review worked best on generated, small diagrams and short feature files.
- Splitting the component diagram by port type kept each view readable and still checkable.
- Q&A before drafting was valuable; the prompts now enforce it, but the enforcement is a convention for the agent,
  backed only by `request_model_draft` refusing without a baseline and a recorded Q&A.

## Iteration 2 findings (G4 preparation)

- Binding scenarios to real steps exposed four wording defects in reviewed specs (wrong upstream ID, tag name without revision, wrong trace stage, over-broad format rule). Executing specs is itself a review.
- Per-scenario throwaway git workspaces with test keys made approval, waiver and hook scenarios testable without touching the real repository; the real suite must never run inside such a workspace (recursion).
- Remaining gaps: pre-receive hook does not check the signer's role; only `read_document` applies the confidentiality filter; decision IDs are count-based; refusal steps match substrings; MCP tool names differ from the scenario wording; SysON import is manual.

## Iteration 2 review findings (code review before G4)

- Code review found that requirements were not traceable to sources or stakeholders; added SRC/STK items, needs-level citation and `source-traceable` rules. Source reconstruction (`docs/sources/project-brief.md`) must be confirmed by the owner.
- Review also found missing edge cases: approvals on different commits, signing an earlier commit, deleting the last element. Gate revisions are now commit-bound.
- Lesson: a trace-gap test fixture must produce exactly one violation; adding rules changed the old fixture's behaviour.
