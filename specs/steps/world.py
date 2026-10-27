"""Test world for the step definitions: an isolated git workspace per scenario.

The world copies model/, specs/features/ and decisions/ of the project into a temporary git repository, registers
test keys (alice, bob, agent-1 registered; mallory not) and points the tools at it (core.ROOT and SPECFLOW_ROOT),
so scenarios exercise the real tools without touching the project.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE_ROOT / "tools"))

import approvals  # noqa: E402
import specflow_core as core  # noqa: E402

ALL_ROLES = ["requirements-owner", "systems-engineer", "reviewer", "agent-operator", "quality-management",
             "information-security", "implementation-team"]
COPY = ("model", "specs/features", "decisions")


def sh(cwd, *args, check=True, env=None):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, check=check)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{' '.join(args)}: {e.stderr.strip()}") from e


class Keys:
    """SSH keys generated once per test run."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="specflow-keys-"))
        for name in ("alice", "bob", "agent-1", "mallory"):
            sh(self.dir, "ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.dir / name))

    def private(self, name):
        return self.dir / name

    def public(self, name):
        return self.dir / f"{name}.pub"

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class World:
    def __init__(self, keys):
        self.keys = keys
        self.dir = Path(tempfile.mkdtemp(prefix="specflow-world-"))
        self.root = self.dir / "ws"
        self.root.mkdir()
        self.saved = (core.ROOT, os.environ.get("SPECFLOW_ROOT"))
        self.notes = {}
        self._build()
        core.ROOT = self.root.resolve()
        os.environ["SPECFLOW_ROOT"] = str(self.root)

    def _build(self):
        sh(self.root, "git", "init", "-q", "-b", "main")
        for k, v in (("user.email", "alice@example.com"), ("user.name", "alice"), ("gpg.format", "ssh"),
                     ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
            sh(self.root, "git", "config", k, v)
        for rel in COPY:
            shutil.copytree(CODE_ROOT / rel, self.root / rel, ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "approvals/keys").mkdir(parents=True)
        shutil.copy(CODE_ROOT / "approvals/gates.json", self.root / "approvals/gates.json")
        for name in ("alice", "bob", "agent-1"):
            shutil.copy(self.keys.public(name), self.root / "approvals/keys" / f"{name}.pub")
        self.write_json("approvals/roles.json", {"alice": ALL_ROLES, "bob": ["reviewer"], "agent-1": []})
        sh(self.root, "git", "add", "-A")
        sh(self.root, "git", "commit", "-q", "-m", "initial")
        self.use_key("alice")

    def close(self):
        core.ROOT = self.saved[0]
        if self.saved[1] is None:
            os.environ.pop("SPECFLOW_ROOT", None)
        else:
            os.environ["SPECFLOW_ROOT"] = self.saved[1]
        shutil.rmtree(self.dir, ignore_errors=True)

    @property
    def ws(self):
        return core.Workspace(self.root)

    def git(self, *args, check=True):
        return sh(self.root, "git", *args, check=check)

    def read_json(self, rel):
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def write_json(self, rel, data):
        (self.root / rel).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def commit(self, message="change", author=None, trailers=()):
        body = message + ("\n\n" + "\n".join(trailers) if trailers else "")
        self.git("add", "-A", "model", "specs", "decisions")
        args = ["commit", "-q", "--allow-empty", "-m", body]
        if author:
            args += ["--author", f"{author} <{author}@example.com>"]
        self.git(*args)

    def use_key(self, name):
        self.git("config", "user.signingkey", str(self.keys.private(name)))

    def set_gate(self, gate, **fields):
        cfg = self.read_json("approvals/gates.json")
        cfg["gates"][gate].update(fields)
        self.write_json("approvals/gates.json", cfg)

    def set_single_person(self, allowed):
        cfg = self.read_json("approvals/gates.json")
        cfg["allow_single_person"] = allowed
        self.write_json("approvals/gates.json", cfg)

    def roles_of(self, gate):
        return approvals.gates(self.ws)[gate]["roles"]

    def approve(self, gate, role, signer="alice", message="approved", commit=None):
        """Create the next approval revision signed by `signer`; raises core.Rejected when refused."""
        self.use_key(signer)
        try:
            return approvals.create_approval(gate, role, message, self.ws, commit=commit)
        finally:
            self.use_key("alice")

    def approve_all(self, gate, signer="alice"):
        for role in self.roles_of(gate):
            self.approve(gate, role, signer)

    def edit_element(self, element, new_text="changed text"):
        """Change the doc text of a model element and return the edited file."""
        import re
        for f in sorted((self.root / "model").glob("*.sysml")):
            text = f.read_text(encoding="utf-8")
            m = re.search(rf"<'{re.escape(element)}'.*?doc\s*/\*(.*?)\*/", text, re.S)
            if m:
                f.write_text(text[:m.start(1)] + f" {new_text} " + text[m.end(1):], encoding="utf-8")
                return f
        raise AssertionError(f"element {element} not found")

    def make_gap(self):
        """Remove the allocation of DR-001 and commit; returns (rule, element) of the single new trace gap."""
        from b_support import drop_satisfy
        assert drop_satisfy(self, "DR-001"), "DR-001 is not allocated"
        self.commit("remove allocation of DR-001")
        return "l2-allocated", "DR-001"

    def sign_waiver(self, rule, element, rationale="accepted for this iteration", expiry=None, signer="alice"):
        """Create a waiver tag by hand so that invalid variants (no rationale, past expiry, other signer) are possible."""
        import datetime
        import waivers
        expiry = expiry or (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        lines = ([f"rationale: {rationale}"] if rationale else []) + [f"expiry: {expiry}"]
        name = f"waiver/{rule}/{waivers.element_key(element)}.1"
        self.use_key(signer)
        try:
            self.git("tag", "-s", name, "-m", "\n".join(lines))
        finally:
            self.use_key("alice")
        return name

    def cli(self, *args, check=False):
        env = {**os.environ, "SPECFLOW_ROOT": str(self.root)}
        r = subprocess.run([sys.executable, str(CODE_ROOT / "tools/specflow.py"), *args], cwd=self.root,
                           capture_output=True, text=True, env=env)
        if check and r.returncode:
            raise RuntimeError(f"specflow {' '.join(args)} failed: {r.stdout}{r.stderr}")
        return r
