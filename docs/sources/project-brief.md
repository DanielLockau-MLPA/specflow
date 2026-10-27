# Project brief (requirement source SRC-001)

Written record of the requirements owner's initial request and the Q&A that followed (session of 2026-10-26),
summarised by the AI agent. The requirements owner confirms or corrects this record in the G1 review; the owner's
confirmation, not this text, is the source.

The requirements owner asked for tooling for the following workflow:

1. A human supplies requirements as input documents and in a Q&A session with an AI agent. When both agree on the
   project, the agent drafts an MBSE (SysML v2) model of a system design. This is not limited to software systems.
2. The human engineers organise a review team and modify the proposal until the stakeholders agree on the design.
   The final model contains all normative requirements and the requirements from threat modelling.
3. Specifications are then written in agreement with the design, in a language that supports executable specification.
   This stage starts again with a Q&A review of the model between engineers and the agent; the agent drafts the
   executable specification as a starting point, and the humans review and modify it until stakeholders agree.
4. Goals: visual models and traceability, a conceptual architecture usable as input for threat modelling, and a
   precisely testable specification as the stage gate for implementation.
5. Preferences stated by the owner: MCP servers for interaction with the model and the specification; SysML v2 (text
   and visual rendering) with SysON for the graphical view; no paid tools; Python with `uv`; any MCP client.
6. The result must be acceptable in an organisation certified to ISO 27001, ISO 9001 and IEC 62443 (records, access
   control, change control), must not depend on one AI client or LLM, and checks must be reproducible in CI.
7. Humans stay in control: AI assistance never changes approved content or approves anything.

Later requests from the owner (per-role signed approvals, revisioned approval tags, commit-bound gate revisions,
requirement sources) are recorded in `decisions/model.md` and `decisions/spec.md`.
