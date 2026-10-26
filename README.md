# MBSE to executable specification (prototype)

Tooling for a human-gated, AI-assisted workflow:
needs → SysML v2 model → executable specification → implementation gate, with traceability throughout.
The repository dogfoods itself: `model/` and `specs/` describe this toolchain. Status: **draft, thin slice**.

## Layout

| Path | Content |
|---|---|
| `model/` | SysML v2 text model: needs, use cases, L1 system requirements, L2 design requirements, architecture |
| `specs/features/` | Gherkin scenarios tagged with model IDs (`@SR-004 @DR-002`) |
| `specs/steps/` | Step bindings (currently a pending stub; real steps come at G4) |
| `tools/` | Setup, validation, architecture/diagram generation, trace check |
| `docs/` | Generated diagrams (`diagrams.md`, `diagrams/`) and step vocabulary |
| `tests/` | Tests of the tooling |

Trace chain: Need → Use case → L1 requirement (`SR-`) → L2 requirement (`DR-`) → design element (`satisfy`) → scenario (tag).
Trace links in the model are `dependency 'X derives|covers|exercises Y'` statements.

## Setup

```bash
./setup.sh              # check and list dependencies (changes nothing)
./setup.sh --install    # install Python (uv) and Node packages, plus the headless browser for diagrams
```

Further options: `--syson` (pull the SysON images), `--install-system` (apt packages for git, node, java; asks for sudo),
`--yes` (no prompts). Required: git, uv, Python ≥ 3.14, Node ≥ 20. Optional: Java ≥ 17, Docker.

## Daily commands

```bash
uv run python tools/validate_model.py          # syntax and semantic check of model/*.sysml (non-zero exit on errors)
uv run python tools/arch.py check              # architecture consistency: ports, connections, allocation of all DRs
uv run python tools/arch.py diagrams --render  # regenerate docs/diagrams/*.mmd, .svg, .png and docs/diagrams.md
uv run python tools/tracecheck.py check             # trace completeness: needs, model and spec stages (--stage, --json)
uv run python tools/coverage_report.py                # coverage report per level and gate (--format json|markdown, --out FILE)
uv run behave specs/features --dry-run         # parse the specs and bind steps
uv run behave specs/features                   # run the specs (all skipped until the system exists)
uv run python tools/steps_vocab.py             # regenerate docs/step_vocabulary.md
uv run pytest tests                            # tests of the tooling
```

Validator warnings about unsatisfied or unverified requirements are expected for needs and L1 requirements,
because only L2 requirements are allocated to design elements.

## Viewing the diagrams

Open `docs/diagrams.md` (embeds pre-rendered SVGs). Sources are `docs/diagrams/*.mmd` (Mermaid); to render them yourself
paste one into <https://mermaid.live>, use a VS Code Mermaid extension, or run
`tools/node/node_modules/.bin/mmdc -p tools/node/puppeteer.json -i docs/diagrams/00_overview_layers.mmd -o out.svg`.
Arrows point from the sender of a request to its receiver.

## Waivers

Trace gaps can be waived in `trace/waivers.json` (optional), a list of
`{"rule", "element", "rationale", "approver", "expiry": "YYYY-MM-DD"}`. A waiver without rationale, human approver
or a future expiry is ignored and reported.

## Optional: SysON (graphical model review)

`docker compose -f tools/syson/docker-compose.yml up -d`, then open <http://localhost:8080>.
The `.sysml` files in git remain the source of truth.

## Conventions

- IDs are SysML short names: `N-` need, `UC-` use case, `SR-` L1, `DR-` L2. They are never reused.
- Agents propose changes on `proposal/*` branches only; commits made with AI assistance carry a `Co-authored-by` trailer.
- Generated files (`docs/diagrams*`, `docs/step_vocabulary.md`) are not edited by hand.

## MCP servers (stdio)

- `uv run python tools/mcp_model.py`: `list_elements`, `read_element`, `search`, `trace`, `validate`, `render`, `request_model_draft`.
- `uv run python tools/mcp_spec.py`: `list_specs`, `draft_scenarios`, `run`, `coverage`.
- Both also offer prompts `model_qa`, `spec_qa`, `review` (ask first, log outcomes, never claim approval), and `read_document` (content labelled untrusted), `list_decisions`, `record_decision` and `propose_edit`.

Register them in any MCP client as stdio commands, with the repository as working directory. Guards:
paths are confined to the workspace (`.git` is protected), `propose_edit` writes only to `proposal/*` branches and
never to files in a `baseline/*` tag, and `record_decision` / `propose_edit` need a human "approve" through the
client's elicitation prompt. If the client cannot elicit, the call is refused. Decisions are appended to
`decisions/<stage>.md`. Set `SPECFLOW_ROOT` to use another workspace.

## Not yet built

Approval and gate tooling (signed baselines), step bindings. See `docs/retrospective.md` for findings.
