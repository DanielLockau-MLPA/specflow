"""Lightweight reader for the project's SysML v2 text files.

Prototype helper: extracts IDs, trace dependencies, part structure and
connections with regular expressions, and offers an architecture check and
diagram generation. It is not a SysML parser; syntax validation is done by the
parser backend (tools/validate_model.py).

Usage:
    python tools/arch.py check                 # architecture consistency check
    python tools/arch.py diagrams              # write docs/diagrams/*.mmd and docs/diagrams.md
    python tools/arch.py diagrams --render     # additionally pre-render .svg and .png (needs ./setup.sh --install)
"""
import glob
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_root():
    """Workspace holding model/ and specs/; the code checkout unless SPECFLOW_ROOT is set."""
    return Path(os.environ.get("SPECFLOW_ROOT", ROOT)).resolve()


OUT_DIR = ROOT / "docs/diagrams"
MMDC = ROOT / "tools/node/node_modules/.bin/mmdc"
MMDC_CONFIG = ROOT / "tools/node/mermaid-config.json"
PUPPETEER_CONFIG = ROOT / "tools/node/puppeteer.json"


def read_model(root=None):
    base = Path(root) if root else data_root()
    return {f: open(f, encoding="utf-8").read() for f in sorted(glob.glob(str(base / "model/*.sysml")))}


def block(src, start):
    """Return the text between the braces opening at or after `start`."""
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j]
    raise ValueError("unbalanced braces")


def strip_docs(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def ids_and_names(model):
    """Map element name -> short-name ID, and ID -> (name, first doc line)."""
    name_to_id, id_info = {}, {}
    for src in model.values():
        for m in re.finditer(r"(requirement|use case|item|part)\s+<'([A-Z]+-\d+)'>\s+(\w+)", src):
            _kind, eid, name = m.groups()
            name_to_id[name] = eid
            doc = re.search(r"doc\s*/\*\s*(.*?)\s*\*/", block(src, m.end()), re.DOTALL)
            id_info[eid] = (name, doc.group(1) if doc else "")
    return name_to_id, id_info


def trace_links(model, name_to_id):
    links = []
    for src in model.values():
        for m in re.finditer(r"dependency\s+'([^']*)'\s+from\s+([\w:]+)\s+to\s+([\w:]+);", src):
            label, a, b = m.groups()
            verb = label.split()[1]
            a, b = a.split("::")[-1], b.split("::")[-1]
            if a in name_to_id and b in name_to_id:
                links.append((name_to_id[a], verb, name_to_id[b]))
    return links


def architecture(model):
    src = next(s for f, s in model.items() if f.endswith("40_architecture.sysml"))
    defs = {}
    for m in re.finditer(r"part def (\w+)", src):
        name = m.group(1)
        body = strip_docs(block(src, m.end()))
        defs[name] = re.findall(r"port (\w+)\s*:\s*(\w+)", body)
    usages, conns = {}, []
    for blk in ("Toolchain", "SystemContext"):
        body = strip_docs(block(src, src.index(f"part def {blk}")))
        for n, t in re.findall(r"part (\w+) : (\w+);", body):
            usages[n] = (t, blk)
        for a, b in re.findall(r"connect ([\w.]+) to ([\w.]+);", body):
            conns.append((a.replace("toolchain.", ""), b.replace("toolchain.", "")))
    sat = re.findall(r"satisfy (\w+) by ([\w.]+);", src)
    return defs, usages, conns, sat


def check():
    model = read_model()
    name_to_id, _ = ids_and_names(model)
    defs, usages, conns, sat = architecture(model)
    problems = []
    endpoints = {e for c in conns for e in c}
    for u, (t, _) in usages.items():
        for p, _pt in defs[t]:
            if f"{u}.{p}" not in endpoints:
                problems.append(f"unconnected port {u}.{p}")
    touched = defaultdict(int)
    for a, b in conns:
        ua, pa = a.split(".")
        ub, pb = b.split(".")
        if ua not in usages or ub not in usages:
            problems.append(f"unknown part in connection {a} -> {b}")
            continue
        ta = dict(defs[usages[ua][0]]).get(pa)
        tb = dict(defs[usages[ub][0]]).get(pb)
        if ta is None or tb is None:
            problems.append(f"unknown port in connection {a} -> {b}")
        elif ta != tb:
            problems.append(f"port type mismatch {a}:{ta} -> {b}:{tb}")
        touched[ua] += 1
        touched[ub] += 1
    for u, (t, _) in usages.items():
        if touched[u] == 0 and t != "Toolchain":
            problems.append(f"isolated part {u}")
    toolchain_parts = {u for u, (_, blk) in usages.items() if blk == "Toolchain"}
    allocated = {s[1].split(".")[-1] for s in sat}
    for u in sorted(toolchain_parts):
        if u not in allocated:
            problems.append(f"part {u} has no allocated requirement")
    dr_ids = sorted(i for i in name_to_id.values() if i.startswith("DR-"))
    sat_ids = {name_to_id[s[0]] for s in sat if s[0] in name_to_id}
    for d in dr_ids:
        if d not in sat_ids:
            problems.append(f"{d} is not allocated to any part")
    covered = set().union(*(k for _s, _t, k, _n in VIEWS))
    for a, b in conns:
        if conn_kind(defs, usages, a) not in covered:
            problems.append(f"connection {a} -> {b} ({conn_kind(defs, usages, a)}) is not in any diagram view")
    print(f"parts={len(usages)} connections={len(conns)} allocations={len(sat)} DR={len(dr_ids)}")
    for p in problems:
        print("PROBLEM:", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def mm(s):
    return s.replace('"', "'")


# Views partition the connections by port type; coverage is enforced in check().
VIEWS = [
    ("01a_view_agent_path", "View: agent-facing path", {"McpPort", "ContentPort", "ConfirmationPort", "HumanPort"},
     "How the AI agent reaches the servers (through InputGuard), how content is filtered and how confirmations reach the human."),
    ("01b_view_services", "View: core service calls", {"TraceQueryPort", "ImpactPort", "RunPort", "LogPort", "IdPort", "ViewPort"},
     "Which components use the core services."),
    ("01c_view_governance", "View: governance", {"ApprovalPort", "GatePort", "CliPort", "AuditPort"},
     "Human-only governance: review CLI, approvals and gate evaluation."),
    ("01d_view_storage", "View: workspace and Git access", {"WorkspacePort", "GitPort"},
     "All file access goes through WorkspaceGuard; Git operations go to the repository."),
]


def conn_kind(defs, usages, endpoint):
    u, p = endpoint.split(".")
    return dict(defs[usages[u][0]])[p]


def build_diagrams():
    """Return a list of (slug, title, description, mermaid source)."""
    model = read_model()
    name_to_id, id_info = ids_and_names(model)
    defs, usages, conns, sat = architecture(model)
    links = trace_links(model, name_to_id)
    diagrams = []

    groups = {
        "agentfacing": ("Agent-facing servers", ["modelMcp", "specMcp", "promptLibrary"]),
        "guards": ("Security guards", ["inputGuard", "confidentialityFilter", "confirmationChannel", "workspaceGuard"]),
        "services": ("Core services", ["traceService", "impactAnalyzer", "specRunner", "idRegistry", "decisionLog", "viewExporter"]),
        "governance": ("Governance (human only)", ["reviewCli", "approvalService", "gateEvaluator", "tagStore", "auditReporter", "refGuardHook"]),
        "extagent": ("MCP client + AI agent", ["mcpClient"]),
        "exthuman": ("Human", ["human"]),
        "extrepo": ("Git repository", ["repo"]),
    }
    part_group = {p: g for g, (_t, ps) in groups.items() for p in ps}
    o = ["flowchart LR"]
    for g, (title, ps) in groups.items():
        o.append(f'  subgraph {g}["{title}"]')
        for p in ps:
            o.append(f'    {p}["{usages[p][0]}"]')
        o.append("  end")
    agg = defaultdict(set)
    for a, b in conns:
        ua, pa = a.split(".")
        ub, _pb = b.split(".")
        ga, gb = part_group[ua], part_group[ub]
        if ga != gb:
            agg[(ga, gb)].add(dict(defs[usages[ua][0]])[pa].replace("Port", ""))
    for (ga, gb), kinds in sorted(agg.items()):
        o.append(f'  {ga} -->|{", ".join(sorted(kinds))}| {gb}')
    for g in ("extagent", "exthuman", "extrepo"):
        o.append(f"  style {g} fill:#eee,stroke:#999")
    diagrams.append(("00_overview_layers", "Overview by layer",
                     "Parts grouped by role; arrows (sender to receiver) aggregate all connections between groups and are labelled with the interface types. Connections inside a group are only shown in the detailed diagram. Shaded groups are outside the system boundary.",
                     "\n".join(o)))

    o = ["flowchart LR", "  subgraph ext[External context]"]
    for u, (t, blk) in usages.items():
        if blk == "SystemContext" and u != "toolchain":
            o.append(f'    {u}["{t}"]')
    o += ["  end", "  subgraph tc[Toolchain - system of interest]"]
    for u, (t, blk) in usages.items():
        if blk == "Toolchain":
            o.append(f'    {u}["{t}"]')
    o.append("  end")
    seen = set()
    for a, b in conns:
        ua, pa = a.split(".")
        ub, _pb = b.split(".")
        label = dict(defs[usages[ua][0]])[pa]
        if (ua, ub, label) in seen:
            continue
        seen.add((ua, ub, label))
        o.append(f"  {ua} -->|{label}| {ub}")
    for u, (t, blk) in usages.items():
        if blk == "SystemContext" and u != "toolchain":
            o.append(f"  style {u} fill:#eee,stroke:#999")
    diagrams.append(("01_context_components", "System context and components (detailed)",
                     "All 46 connections, labelled with the interface (port type). Arrows point from the sender of a request or push to its receiver; replies to a call travel back on the same connection. Content returned to the agent is modelled as its own push: servers -> ConfidentialityFilter -> InputGuard. Shaded parts are outside the system boundary. See the overview above for a simplified view.",
                     "\n".join(o)))

    for slug, title, kinds, note in VIEWS:
        sel = [(a, b) for a, b in conns if conn_kind(defs, usages, a) in kinds]
        used = []
        for a, b in sel:
            for x in (a, b):
                if x.split(".")[0] not in used:
                    used.append(x.split(".")[0])
        o = ["flowchart LR"]
        for u in used:
            o.append(f'  {u}["{usages[u][0]}"]')
        seen = set()
        for a, b in sel:
            ua, ub = a.split(".")[0], b.split(".")[0]
            label = conn_kind(defs, usages, a)
            if (ua, ub, label) not in seen:
                seen.add((ua, ub, label))
                o.append(f"  {ua} -->|{label}| {ub}")
        for u in used:
            if usages[u][1] == "SystemContext":
                o.append(f"  style {u} fill:#eee,stroke:#999")
        diagrams.append((slug, title,
                         f"{note} Arrows point from the sender of a request or push to its receiver. Shaded parts are outside the system boundary. Port types shown: {', '.join(sorted(kinds))}. Together the views 01a-01d cover every connection of the detailed diagram 01.",
                         "\n".join(o)))

    diagrams.append(("02_agent_path_confirmation", "Agent-facing path and human confirmation",
                     "All agent traffic passes the input guard; state-changing calls need a human decision from outside the agent session (DR-024, DR-032).",
                     "\n".join([  # noqa: FLY002 - one line per diagram row
                         "sequenceDiagram",
                         "  participant A as AI agent (MCP client)",
                         "  participant G as InputGuard",
                         "  participant S as Model/Spec MCP server",
                         "  participant C as ConfirmationChannel",
                         "  actor H as Human",
                         "  participant R as Repository",
                         "  A->>G: tool call (read)",
                         "  G->>S: forward",
                         "  S->>G: content via ConfidentialityFilter",
                         "  G-->>A: content labelled untrusted",
                         "  A->>G: tool call (propose edit)",
                         "  G->>S: forward",
                         "  S->>G: request confirmation",
                         "  G->>C: confirmation request",
                         "  C->>H: prompt outside agent session",
                         "  H-->>C: decision",
                         "  C-->>G: decision only",
                         "  alt approved",
                         "    G-->>S: proceed",
                         "    S->>R: commit on proposal/* branch (AI-marked)",
                         "  else denied or no answer",
                         "    G-->>A: aborted",
                         "  end"])))

    diagrams.append(("03_approval_gate_path", "Approval and gate path (human only)",
                     "Approvals are signed git tags; the gate state is derived from them and the trace rules. Reachable only through the review CLI; there is no agent-facing port (DR-012 to DR-018).",
                     "\n".join([  # noqa: FLY002 - one line per diagram row
                         "sequenceDiagram",
                         "  actor H as Human approver",
                         "  participant CLI as ReviewCli",
                         "  participant AP as ApprovalService",
                         "  participant GE as GateEvaluator",
                         "  participant TS as TraceService",
                         "  participant TG as ApprovalTagStore",
                         "  participant R as Repository",
                         "  H->>CLI: approve(gate, role, rationale)",
                         "  CLI->>AP: sign approval/<gate>/<role>.<n>",
                         "  AP->>AP: check registered key, role mapping, clean scope",
                         "  AP->>TG: create signed tag",
                         "  TG->>R: store tag",
                         "  H->>CLI: evaluate gate",
                         "  CLI->>GE: evaluate(gate)",
                         "  GE->>TG: latest valid tag per role, scope drift",
                         "  GE->>TS: trace rules, signed waiver tags",
                         "  GE-->>CLI: open / closed with reasons (state derived, no baseline tag)",
                         "  GE->>TG: write evidence bundle of the gate"])))

    by_part = defaultdict(list)
    for dr, part in sat:
        by_part[part.split(".")[-1]].append(name_to_id.get(dr, dr))
    o = ["flowchart LR"]
    for part, drs in sorted(by_part.items()):
        o.append(f'  {part}["{part}"]')
        for d in sorted(drs):
            o.append(f'  {part} --- {d.replace("-", "")}["{d}"]')
    diagrams.append(("04_allocation", "Allocation of design requirements to parts",
                     "Each design requirement (DR) is satisfied by the part it is connected to.", "\n".join(o)))

    def chain(slug, title, desc, filt):
        nodes, edges = set(), []
        for a, v, b in links:
            if filt(a, v, b):
                edges.append((a, v, b))
                nodes.update([a, b])
        o = ["flowchart LR"]
        for n in sorted(nodes):
            o.append(f'  {n.replace("-", "")}["{n}<br/>{mm(id_info[n][0])}"]')
        for a, v, b in edges:
            o.append(f'  {a.replace("-", "")} -->|{v}| {b.replace("-", "")}')
        diagrams.append((slug, title, desc, "\n".join(o)))

    chain("05_needs_use_cases", "Needs and the use cases covering them", "Use case (UC) covers need (N).",
          lambda a, v, b: a.startswith("UC") and b.startswith("N-") and v == "covers")
    chain("06_needs_l1", "Needs and the L1 requirements derived from them", "L1 system requirement (SR) derives from need (N).",
          lambda a, v, b: a.startswith("SR") and b.startswith("N-"))
    chain("07_use_cases_l1", "Use cases and the L1 requirements they exercise", "Use case (UC) exercises L1 requirement (SR).",
          lambda a, v, b: a.startswith("UC") and b.startswith("SR") and v == "exercises")
    chain("08_l1_l2", "L1 requirements and the L2 requirements derived from them", "L2 design requirement (DR) derives from L1 requirement (SR).",
          lambda a, v, b: a.startswith("DR") and b.startswith("SR"))
    return diagrams


def render(mmd, base):
    cmd = [str(MMDC), "-i", str(mmd), "-p", str(PUPPETEER_CONFIG), "-c", str(MMDC_CONFIG), "-b", "white"]
    for ext, extra in (("svg", []), ("png", ["-s", "2"])):
        r = subprocess.run(cmd + ["-o", str(base.with_suffix("." + ext))] + extra, capture_output=True, text=True, check=False)
        if r.returncode != 0:
            print(f"render failed for {mmd.name} ({ext}):\n{r.stderr[-400:]}", file=sys.stderr)
            return False
    return True


TOOLING = """## Viewing the diagrams

- **Pre-rendered images** (this page): `docs/diagrams/*.svg` and `*.png`, regenerated with `uv run python tools/arch.py diagrams --render`.
- **Sources:** `docs/diagrams/*.mmd` (Mermaid text). GitHub and GitLab also render `.mmd` files and ```` ```mermaid ```` blocks natively.
- **Online editor (no install):** https://mermaid.live — paste or open a `.mmd` file; export SVG/PNG.
- **VS Code:** extension *Mermaid Chart* (`MermaidChart.vscode-mermaid-chart`) previews `.mmd` files; *Markdown Preview Mermaid Support* (`bierner.markdown-mermaid`) renders mermaid blocks in Markdown preview.
- **CLI:** `tools/node/node_modules/.bin/mmdc -i docs/diagrams/01_context_components.mmd -o out.svg`.
"""


def diagrams(do_render):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*"):
        old.unlink()
    items = build_diagrams()
    md = ["# Architecture and traceability diagrams", "",
          "Generated by `uv run python tools/arch.py diagrams --render` from the files in `model/`. Do not edit by hand.", "",
          TOOLING]
    can_render = do_render and MMDC.exists()
    if do_render and not MMDC.exists():
        print("mmdc not found; run ./setup.sh --install. Writing .mmd files only.", file=sys.stderr)
    rendered = 0
    for slug, title, desc, src in items:
        mmd = OUT_DIR / f"{slug}.mmd"
        mmd.write_text(src + "\n", encoding="utf-8")
        ok = can_render and render(mmd, OUT_DIR / slug)
        rendered += bool(ok)
        md += [f"## {title}", "", desc, ""]
        if ok:
            md += [f"[![{title}](diagrams/{slug}.svg)](diagrams/{slug}.svg)", "",
                   f"Source: [`{slug}.mmd`](diagrams/{slug}.mmd) · [PNG](diagrams/{slug}.png)", ""]
        else:
            md += [f"_Not rendered. Source: [`{slug}.mmd`](diagrams/{slug}.mmd)_", ""]
    (ROOT / "docs/diagrams.md").write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {len(items)} .mmd files, rendered {rendered}, docs/diagrams.md")
    return 0 if (not do_render or rendered == len(items)) else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        sys.exit(check())
    if cmd == "diagrams":
        sys.exit(diagrams("--render" in sys.argv))
    sys.exit(f"unknown command {cmd}")
