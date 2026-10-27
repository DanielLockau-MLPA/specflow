"""Waivers as signed tags `waiver/<rule>/<element>[.<n>]` (SR-015, DR-015, DR-018).

The tag message carries `rationale: ...` and `expiry: YYYY-MM-DD`; the approver is the verified signer. A waiver
counts only with a valid signature from a registered key, a human signer (not an agent principal), a rationale and an
expiry in the future. Newer revisions supersede older ones. Waivers are created by humans (tools/approve.py waive).
"""
# comment by DL: this needs to be accompanied by documentation, the waiver process is not clear by just reading this file
import datetime
import re

import approvals
import specflow_core as core

AGENT_PREFIXES = ("agent",)


def element_key(element):
    """Ref-safe form of an element ID or location (a violation element may be `file.feature:12`)."""
    return re.sub(r"[^\w.\-]", "_", str(element))


def _parse(name, ws):
    m = re.fullmatch(r"waiver/([\w\-]+)/(.+?)(?:\.(\d+))?", name)
    if not m:
        return None
    rule, element, rev = m.group(1), m.group(2), int(m.group(3) or 0)
    body = core.git("tag", "--list", "--format=%(contents)", name, cwd=ws.root)
    fields = dict(re.findall(r"^(rationale|expiry):\s*(.*)$", body, re.M))
    return rule, element, rev, fields


def load(ws=None):
    """Return (valid, invalid) waivers; each is a dict with rule, element, rationale, approver, expiry, tag, reason."""
    ws = ws or core.Workspace()
    today = datetime.date.today().isoformat()
    newest = {}
    for name in core.git("tag", "--list", "waiver/*", cwd=ws.root).split():
        parsed = _parse(name, ws)
        if parsed:
            rule, element, rev, fields = parsed
            key = (rule, element)
            if key not in newest or rev > newest[key][0]:
                newest[key] = (rev, name, fields)
    valid, invalid = [], []
    for (rule, element), (_rev, name, fields) in sorted(newest.items()):
        v = approvals.verify_tag(name, ws)
        w = {"rule": rule, "element": element, "rationale": fields.get("rationale", "").strip(),
             "expiry": fields.get("expiry", "").strip(), "approver": v.signer, "tag": name}
        reason = None
        if not v.ok:
            reason = v.reason
        elif v.signer.lower().startswith(AGENT_PREFIXES):
            reason = "signed by an agent identity"
        elif not w["rationale"]:
            reason = "no rationale"
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", w["expiry"]) or w["expiry"] < today:
            reason = "expiry missing or in the past"
        if reason:
            invalid.append({**w, "reason": reason})
        else:
            valid.append(w)
    return valid, invalid


def create_waiver(rule, element, rationale, expiry, ws=None):
    """Human action: sign the next revision of a waiver with the operator's SSH key."""
    ws = ws or core.Workspace()
    if not rationale.strip():
        raise core.Rejected("a waiver needs a rationale")
    try:
        if datetime.date.fromisoformat(expiry) <= datetime.date.today():
            raise core.Rejected("the expiry must be in the future")
    except ValueError:
        raise core.Rejected("expiry must be YYYY-MM-DD")
    base = f"waiver/{rule}/{element_key(element)}"
    revs = [int(m.group(1) or 0) for t in core.git("tag", "--list", f"{base}*", cwd=ws.root).split()
            if (m := re.fullmatch(re.escape(base) + r"(?:\.(\d+))?", t))]
    name = f"{base}.{max(revs, default=0) + 1}"
    core.git("-c", "gpg.format=ssh", "tag", "-s", name, "-m", f"rationale: {rationale}\nexpiry: {expiry}", cwd=ws.root)
    v = approvals.verify_tag(name, ws)
    if not v.ok:
        core.git("tag", "-d", name, cwd=ws.root)
        raise core.Rejected(f"tag deleted: {v.reason}")
    return name, v
