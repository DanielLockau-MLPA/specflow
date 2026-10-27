"""ID scheme and uniqueness (SR-022, DR-028).

An ID is `N|UC|SR|DR|SRC|STK-<digits>`. It cannot be registered when it exists in the model or ever existed in the model
history, so IDs are never reused after deletion. Elements are looked up by ID, so renaming does not affect them.

Usage: uv run python tools/ids.py check SR-100     Exit code 1 when the ID cannot be registered.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specflow_core as core

DECL = re.compile(r"<'((?:N|UC|SR|DR|SRC|STK)-\d+)'")


def used_ids(ws):
    """Every ID declared in model/ now or in any commit of any branch."""
    ids = set()
    for f in (ws.root / "model").glob("*.sysml"):
        ids.update(DECL.findall(f.read_text(encoding="utf-8")))
    history = core.git("log", "--all", "-p", "--format=", "--", "model/", cwd=ws.root, check=False)
    ids.update(DECL.findall(history))
    return ids


def check_new_id(new_id, ws=None):
    """Return None when the ID can be registered, otherwise the reason it cannot."""
    ws = ws or core.Workspace()
    if not core.ID_PATTERN.fullmatch(new_id):
        return f"{new_id} does not follow the scheme (N|UC|SR|DR|SRC|STK)-<number>"
    if new_id in used_ids(ws):
        return f"{new_id} is already used or was used before and is never reused"
    return None


def main(argv):
    if len(argv) != 2 or argv[0] != "check":
        print(__doc__)
        return 2
    why = check_new_id(argv[1])
    print(f"rejected: {why}" if why else "accepted")
    return 1 if why else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
