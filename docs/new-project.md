# Applying the framework to a new project

The workflow is generic (not limited to software), but this repository is a **dogfooding prototype**: some tooling still
assumes the structure of its own model. This guide shows what you set up for a new project, which parts are reusable as they are, and where the
limits are today.

## Two ways to use it

| Approach | When | How |
|---|---|---|
| **External workspace** (recommended) | You want to keep your project repository clean and update the tooling separately | Check out this repository as the tool checkout; point `SPECFLOW_ROOT` at your project repository |
| **Copy into the project** | You want a self-contained repository | Copy `tools/`, `pyproject.toml`, `uv.lock`, `setup.sh`, `.gitignore` entries and the specs harness (`specs/environment.py`) into your repository; run without `SPECFLOW_ROOT` |

In both cases `CODE_ROOT` is where the tools live and `ROOT` (`SPECFLOW_ROOT`, default `CODE_ROOT`) is the workspace that holds `model/`, `specs/`, `approvals/` and `decisions/`.

```bash
git clone <this repository> ~/tools/specflow && cd ~/tools/specflow && ./setup.sh --install
export SPECFLOW_ROOT=~/work/my-project          # a git repository
uv run python tools/specflow.py validate
```

MCP servers use the same variable: register `uv run python tools/mcp_model.py` and `tools/mcp_spec.py` as stdio servers
with `SPECFLOW_ROOT` set in the client configuration.

## Workspace layout to create

```
my-project/
  model/
    00_needs.sysml            needs (N-) and stakeholders (STK-)
    05_sources.sysml          requirement sources (SRC-)
    10_use_cases.sysml        use cases (UC-)
    20_system_requirements.sysml   L1 (SR-)
    30_design_requirements.sysml   L2 (DR-)
    40_architecture.sysml     parts, ports, connections, satisfy allocations
  specs/
    features/*.feature        Gherkin scenarios tagged with model IDs
    steps/ + environment.py   step bindings (project specific)
  approvals/
    gates.json                gates, scope, roles, trace stages
    roles.json                principal -> roles
    keys/<principal>.pub      SSH public keys of the approvers
  decisions/                  decision logs (created by record_decision)
  docs/sources/               input documents, summaries of communication
```

Use the files of this repository as templates; they show the modelling pattern for each level
(`model/00_needs.sysml` … `model/40_architecture.sysml`).

## Step 1: initialise the repository and the governance configuration

1. `git init` the project repository; make it signed-tag capable for the approvers (`git config gpg.format ssh`, `user.signingkey`).
2. Write `approvals/gates.json`. Define the gates, the scope paths of each, the required roles and the trace stages that must be clean:

   ```json
   {
     "allow_single_person": false,
     "gates": {
       "G1": {"scope": ["model/00_needs.sysml", "model/05_sources.sysml"], "roles": ["owner", "reviewer"], "trace": ["needs"]},
       "G2": {"scope": ["model/"], "roles": ["owner", "reviewer", "safety"], "trace": ["needs", "model"]},
       "G3": {"scope": ["specs/features/"], "roles": ["owner", "reviewer", "safety"], "trace": ["needs", "model", "spec"]},
       "G4": {"scope": ["model/", "specs/"], "roles": ["owner", "safety"], "trace": ["needs", "model", "spec"], "scenarios": true}
     }
   }
   ```

   Role names are free kebab-case words; choose them from your stakeholder list. Keep `allow_single_person` off unless one person really holds every role (prototype).
3. Put every approver's SSH public key in `approvals/keys/<principal>.pub` and map the principal to roles in `approvals/roles.json`:

   ```json
   {"alice": ["owner"], "bob": ["reviewer", "safety"]}
   ```
4. Commit this configuration. It is protected from the agent: the MCP servers cannot read or write `approvals/`.
5. On the git host, install `tools/hooks/pre-receive` and the trust-anchor key directory (`SPECFLOW_KEYS_DIR`) so only validly signed approval and waiver tags can be created. See [gates and approvals](gates-and-approvals.md).

## Step 2: needs and sources

Write stakeholders, needs and sources first.

- Stakeholders: `part <'STK-001'> Name : Stakeholder { doc /* … */ }`.
- Sources: `item <'SRC-001'> Name : RequirementSource { … }` with attributes `kind` (`norm`, `communication` or other) and `reference` (document in `docs/sources/` or norm clause); each source is linked to a stakeholder with `dependency 'SRC-001 raisedBy STK-001' from Name to StakeholderName;`.
- Needs: `requirement <'N-001'> …`, each with `cites` links to its sources.
- Link statements are plain dependencies whose name carries the verb: `dependency 'N-001 cites SRC-001' from … to …;`. See [traceability](traceability.md) for the vocabulary.

Run the agent Q&A (prompt `model-qa`) to elicit these from your input documents, then `specflow trace --stage needs` until clean.
Review, then approve G1.

## Step 3: model, then specification

Follow [the workflow guide](workflow.md): use cases and requirements (`UC-`, `SR-`, `DR-`) with `exercises`, `covers`, `derives` links; allocate every design requirement to an architecture element with `satisfy`; then write scenarios tagged with the IDs they verify.

For the specification stage you need executable steps. Gherkin features are generic; the step bindings are not. In this repository they exercise the
toolchain itself. For your system, `specs/steps/*.py` would call your implementation or a test double. Until the implementation exists, an unbound scenario can stay pending: G4 requires all scenarios to have passed (or be attested `@manual`), G3 only requires tags and trace.

## What is reusable and what is not (current state)

| Reusable as is | Project-specific today |
|---|---|
| ID scheme and ID check, trace rules and queries, coverage report | `tools/arch.py` expects `model/40_architecture.sysml` containing `part def Toolchain` and `part def SystemContext`; trace loading fails without them. A minimal file with these two empty definitions is enough |
| Approvals, waivers, gate evaluation, audit and evidence bundle, pre-receive hook | The generated diagrams (`arch.py diagrams`) are built for this toolchain's part names; use your own diagram generation or adapt `VIEWS`/`groups` |
| MCP servers, prompts, guards, decision log | `specs/steps/` and `specs/environment.py` test this toolchain. Replace them with bindings for your system |
| `specflow` CLI, validator wrapper | ID prefixes `N UC SR DR SRC STK` are fixed in `tools/ids.py`, `specflow_core.py` and `gate.py`; `coverage_report.GATES` is hardcoded to G1–G4 |

Gate names beyond G1–G4 therefore need code changes in `coverage_report.py`. Gates are otherwise configuration.

## Verified quickstart

A workspace with `model/00_needs.sysml`, a minimal `model/40_architecture.sysml`, `approvals/gates.json` and an empty `approvals/roles.json` is enough for:

```bash
export SPECFLOW_ROOT=/path/to/workspace
uv run python tools/specflow.py validate
uv run python tools/specflow.py trace --stage needs     # reports need-covered / need-sourced gaps for new needs
uv run python tools/specflow.py gate G1                  # CLOSED: missing approvals and trace gaps listed
uv run python tools/approve.py roles
```

## Adoption checklist

- [ ] Repository initialised, branches `main` and `proposal/*` agreed
- [ ] `approvals/gates.json`, `roles.json` and keys committed; pre-receive hook installed
- [ ] Stakeholders, sources and needs modelled; every need cites a source
- [ ] Agent registered as MCP client with `SPECFLOW_ROOT`; agent identity has no signing key and no credentials for protected refs
- [ ] G1 reviewed and signed per role
- [ ] Model Q&A, model, review, G2
- [ ] Spec Q&A, features, review, G3
- [ ] Step bindings, `specflow run`, `specflow gate G4`, G4 signatures
- [ ] CI runs `specflow validate`, `trace`, `run` and `gate` (exit codes are meaningful)
