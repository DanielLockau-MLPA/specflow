# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def run(root, backend_dir):
    env = {**os.environ, "SPECFLOW_ROOT": str(root), "SPECFLOW_PARSER_BACKEND": "fake_backend:parse",
           "PYTHONPATH": str(backend_dir)}
    r = subprocess.run([sys.executable, str(TOOLS / "validate_model.py"), "--json"], capture_output=True, text=True, env=env, check=False)
    return r.returncode, json.loads(r.stdout)


def test_alternative_backend_gives_same_structure_and_requirement_doc_check(tmp_path):
    (tmp_path / "model").mkdir()
    (tmp_path / "model/a.sysml").write_text("package P {\n  requirement <'SR-001'> A : R {\n  }\n  requirement <'SR-002'> B : R {\n"
                                            "    doc /* x */\n  }\n}\n")
    (tmp_path / "fake_backend.py").write_text(
        "def parse(docs):\n    return [{'file': f, 'line': 2, 'column': 3, 'severity': 'error', 'code': 'syntax', 'message': 'boom'} for f in docs]\n")
    rc, report = run(tmp_path, tmp_path)
    assert rc == 1
    keys = {"file", "line", "column", "severity", "code", "message", "element"}
    assert all(set(f) == keys for f in report["findings"])
    err = next(f for f in report["findings"] if f["severity"] == "error")
    assert err["element"] == "SR-001" and err["file"] == "model/a.sysml" and err["line"] == 2
    docs = [f for f in report["findings"] if f["code"] == "requirement-doc"]
    assert [f["element"] for f in docs] == ["SR-001"] and docs[0]["severity"] == "warning"
