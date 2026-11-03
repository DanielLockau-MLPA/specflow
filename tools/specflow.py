"""Single headless entry point for CI and audits (SR-021, DR-030). No agent, no network, deterministic output.

  uv run python tools/specflow.py validate [--json]
  uv run python tools/specflow.py trace [--stage ...] [--json]
  uv run python tools/specflow.py run [--json]               run the specification, record the result
  uv run python tools/specflow.py coverage [--format json|markdown]
  uv run python tools/specflow.py gate G2 [--run] [--json]
  uv run python tools/specflow.py impact SR-004 [--json]
  uv run python tools/specflow.py audit G3 approvals|waivers|changes|test-evidence|integrity|bundle
  uv run python tools/specflow.py id check SR-100
  uv run python tools/specflow.py approve|roles|status|waive ...   (human actions, see tools/approve.py)

The exit code is non-zero on errors, trace gaps, failing scenarios and closed gates.
"""
import subprocess
import sys
from pathlib import Path

import exectrace  # noqa: F401  (starts the railguard function trace when SPECFLOW_TRACE_DIR is set)

TOOLS = Path(__file__).resolve().parent
COMMANDS = {"validate": "validate_model.py", "trace": "tracecheck.py", "run": "specrun.py", "coverage": "coverage_report.py",
            "gate": "gate.py", "impact": "impact.py", "audit": "audit.py", "id": "ids.py",
            "approve": "approve.py", "roles": "approve.py", "status": "approve.py", "waive": "approve.py"}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "trace" and "check" not in rest:
        rest = ["check", *rest]
    if cmd in ("approve", "roles", "status", "waive"):
        rest = [cmd, *rest]
    return subprocess.call([sys.executable, str(TOOLS / COMMANDS[cmd]), *rest])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
