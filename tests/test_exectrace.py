# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import exectrace

CODE = Path(__file__).resolve().parent.parent


def test_inventory_lists_nested_and_method_functions():
    inv = exectrace.inventory()
    assert "tools/exectrace.py:inventory" in inv
    assert "tools/exectrace.py:start.<locals>.on_start" in inv
    assert "tools/specflow_core.py:Workspace.read_text" in inv


def test_subprocess_records_functions_it_entered(tmp_path):
    trace = tmp_path / "t"
    env = {"PATH": "/usr/bin:/bin", "SPECFLOW_TRACE_DIR": str(trace), "PYTHONPATH": str(CODE / "tools")}
    subprocess.run([sys.executable, "-c", "import exectrace; exectrace.inventory()"], check=True, env=env, capture_output=True)
    merged = exectrace.merge(trace)
    assert "tools/exectrace.py:inventory" in merged and "tools/exectrace.py:_walk" in merged
    assert all(k in exectrace.inventory() for k in merged)


def test_report_flags_unexecuted_functions_and_honours_reasoned_allowlist(tmp_path):
    (tmp_path / "specs").mkdir()
    functions = {"tools/a.py:f", "tools/a.py:g", "tools/a.py:h"}
    rep = exectrace.report(["tools/a.py:f"], tmp_path, functions)
    assert rep["unexecuted"] == ["tools/a.py:g", "tools/a.py:h"] and rep["problems"]

    (tmp_path / exectrace.ALLOWLIST).write_text(json.dumps({"entries": [
        {"function": "tools/a.py:g", "reason": "operator-only recovery path"},
        {"function": "tools/a.py:h", "reason": " "},
        {"function": "tools/gone.py:x", "reason": "obsolete"}]}), encoding="utf-8")
    rep = exectrace.report(["tools/a.py:f"], tmp_path, functions)
    assert rep["allowlisted"] == ["tools/a.py:g"]
    assert rep["unexecuted"] == ["tools/a.py:h"]
    assert rep["stale_allowlist"] == ["tools/gone.py:x"]
    assert any("without a reason" in p for p in rep["problems"])


def test_report_without_trace_is_not_evidence(tmp_path):
    rep = exectrace.report(None, tmp_path, {"tools/a.py:f"})
    assert not rep["traced"] and rep["problems"]


def test_describe_lists_allowlisted_functions_with_reasons(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / exectrace.ALLOWLIST).write_text(
        '{"entries":[{"function":"tools/a.py:g","reason":"manual only"}]}', encoding="utf-8")
    rep = exectrace.report(["tools/a.py:f"], tmp_path, {"tools/a.py:f", "tools/a.py:g"})
    text = "\n".join(exectrace.describe(rep))
    assert "1 of 2 functions executed, 1 allowlisted" in text
    assert "allowlisted tools/a.py:g: manual only" in text
