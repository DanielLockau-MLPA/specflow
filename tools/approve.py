"""Human CLI for approvals: status, verify, baseline. Not exposed through MCP.

  uv run python tools/approve.py status
  uv run python tools/approve.py baseline G2 -m "Model approved by ..."
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals  # noqa: E402
import specflow_core as core  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    b = sub.add_parser("baseline")
    b.add_argument("gate", choices=["G1", "G2", "G3"])
    b.add_argument("-m", "--message", required=True)
    a = ap.parse_args()
    if a.cmd == "status":
        st = approvals.status()
        print(json.dumps(st, indent=2))
        return 1 if any(v["drift"] for v in st.values()) else 0
    try:
        v = approvals.create_baseline(a.gate, a.message)
    except core.Rejected as e:
        print(e, file=sys.stderr)
        return 1
    print(f"baseline/{a.gate} signed by {v.signer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
