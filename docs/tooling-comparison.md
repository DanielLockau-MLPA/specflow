# Tooling comparison: build versus reuse

Findings of a research pass on 2026-11-03 (sources: project READMEs and repositories; AI-assisted web research). Items marked (?) could not be verified. Decision: DL-025 in `decisions/model.md`.

## Scope of the comparison

The project is a SysML v2 centred toolchain: needs, use cases and requirements in a text model, architecture with allocation, executable Gherkin specs, signed stage gates, and agent access through MCP servers. Requirements-management tools (Doorstop, StrictDoc, Sphinx-Needs, OpenFastTrace) cover only a part of this.

## Feature comparison

Legend: yes = native, partial = possible with glue or limited, no = not offered, (?) = unverified.

| Feature | This project | Doorstop | StrictDoc | Sphinx-Needs | OpenFastTrace |
|---|---|---|---|---|---|
| Source of truth | `.sysml`, `.feature`, JSON, md in git | YAML item files in git | `.sdoc` text in git | reStructuredText directives | markdown and code tags |
| SysML v2 model (structure, ports, allocation) | yes | no | no | no | no |
| Typed architecture checks (ports connected, DR allocated) | yes | no | no | no | no |
| Diagrams generated from the model | yes (Mermaid) | no | partial (document graphs) | partial (needflow) | no |
| Stable requirement IDs | yes | yes | yes | yes | yes |
| Trace links between levels | yes (`dependency`, `satisfy`, tags) | yes (`links`) | yes (relations) | yes | yes |
| Suspect, stale or outdated link detection | yes (dangling and stale rules) | yes (content hash) | partial (?) | partial | yes (outdated) |
| Waivers for trace gaps | yes (signed) | no | no | no (?) | no (?) |
| Executable specifications | yes (behave, Gherkin) | no | no | no | no |
| Scenario-to-requirement traceability | yes (`@ID` tags, checked) | no (glue needed) | no (glue needed) | no (glue needed) | partial (custom importer) |
| Per-role signed approvals | yes (SSH-signed tags) | no | no | no | no |
| Stage gates with revision and scope invalidation | yes (G1-G4) | no | no | no | no |
| Agent access through MCP | yes (model-mcp, spec-mcp) | no | no | no | no |
| Human-only approval, agent proposals on branches | yes | no | no | no | no |
| Out-of-band human confirmation | yes | no | no | no | no |
| Path containment and confidentiality filter for agents | yes | no | no | no | no |
| Function-level execution check (railguard) | yes (`sys.monitoring`) | no | no | no | no |
| Import and export formats | open text only | YAML, Excel, ReqIF (?) | ReqIF, Excel, HTML, PDF | HTML, PDF | tracing reports |
| Document generation for reviews | partial (diagrams, reports) | yes (HTML) | yes (HTML, PDF) | yes | partial |
| Licence | this repository | NOASSERTION (?) | NOASSERTION (?) | MIT | GPL-3.0 |
| Runtime | Python 3.14, Node (parser) | Python | Python | Python, Sphinx | Java |

## SysML v2 MCP servers (comparison with model-mcp)

| Project | Runtime and licence | Storage | Edit workflow | Overlap |
|---|---|---|---|---|
| rttorase1/sysmlv2-mcp-server | TypeScript, no declared licence | REST API server | direct | concept only |
| redsteve/SysML-v2-API-MCP-Server | C++, MIT, work in progress, last push 2025-09 | REST API server | direct | concept only |
| hni-ase/SysMLV2-mcp | C#, MIT | REST API server | direct | concept only |
| jgsystemsconsulting/jgs-sysmlv2-api-mcp | closed source, binaries only | REST API server | staged commit with confirmation token | partial; internals unverified |
| model-mcp (this project) | Python, MIT-compatible stack | `.sysml` files in git | proposal branch, signed out-of-band confirmation | n/a |

All four need a running SysML v2 API server (Pilot Implementation, SysON or Teamwork Cloud). None works on text files in git, and none offers signed confirmation, path containment or a confidentiality filter.

## Parser and viewer components

| Component | Role | Assessment |
|---|---|---|
| `sysml-v2-lsp` (npm, MIT, very active) | parser and validator, Mermaid preview, own `sysml-mcp` CLI | used as the validator; no dependence on its edit semantics; its MCP tool list was not examined (?) |
| SysON (EPL-2.0) | graphical SysML v2 modeller on a REST and database backend | optional viewer; manual import and export |
| OMG Pilot Implementation | reference API server | not used |

## Conclusion

- No existing tool covers the SysML v2 layer, signed gates, agent safety design or the railguard.
- Doorstop and StrictDoc could replace only the trace checker, at the cost of a second data model and a conversion of SysML links, and they would not provide the architecture and diagram layer.
- Decision: keep the SysML v2 centred toolchain; adopt neither Doorstop nor StrictDoc (DL-025).
- Concepts worth borrowing: Doorstop suspect links (content-hash based) and OpenFastTrace status classes.

## Open points

1. Capabilities of the `sysml-mcp` CLI bundled with `sysml-v2-lsp`.
2. Licence texts of Doorstop and StrictDoc.
3. Internals of jgs-sysmlv2-api-mcp (closed source).
4. A second targeted search for `sys.monitoring` coverage gates and signed-tag approval tools.
