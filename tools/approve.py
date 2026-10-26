"""Human CLI for gate approvals. Not exposed through MCP.

  uv run python tools/approve.py status
  uv run python tools/approve.py approve G2 --role reviewer -m "Reviewed model, no findings"

Each stakeholder runs `approve` for their own role with their own SSH key (git config gpg.format ssh,
user.signingkey). A gate opens when all required roles have signed the same scope content.
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
    b = sub.add_parser("approve")
    b.add_argument("gate")
    b.add_argument("--role", required=True)
    b.add_argument("-m", "--message", required=True)
    a = ap.parse_args()
    if a.cmd == "status":
        st = approvals.status()
        print(json.dumps(st, indent=2))
        return 0 if all(g["open"] for g in st.values()) else 1
    try:
        v = approvals.create_approval(a.gate, a.role, a.message)
    except core.Rejected as e:
        print(e, file=sys.stderr)
        return 1
    print(f"approval/{a.gate}/{a.role} signed by {v.signer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
