# Copyright (c) 2026 Bradley Allen Wentzel. MIT License.
"""Gate A reproduction probes for Audit 5 findings 1-5 and 7, run in-process (Flask test client, temp dirs, no network).

Usage: python gate_a_probe.py <path-to-backend-dir>
Prints one RESULT line per finding: the observed behaviour on that tree.
"""
import copy
import glob
import json
import os
import sys
import tempfile
from pathlib import Path

backend = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(backend))
os.chdir(backend)
for k in list(os.environ):
    if k.startswith(("ARIA_HOME_", "WHATSAPP_", "NEST_", "EMPORIA_")) or k == "MODEL_API_KEY":
        os.environ[k] = ""

T231, T245, T621 = "2026-01-17T02:31:00-05:00", "2026-01-17T02:45:00-05:00", "2026-01-17T06:21:00-05:00"


def private_client():
    os.environ["ARIA_HOME_PUBLIC_DEMO"] = ""
    os.environ["ARIA_HOME_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "p.db")
    from aria_home.app import create_app
    return create_app().test_client()


def public_client(sessions_dir):
    os.environ["ARIA_HOME_PUBLIC_DEMO"] = "1"
    os.environ["ARIA_HOME_PUBLIC_DEMO_DIR"] = str(sessions_dir)
    from aria_home.app import create_app
    return create_app().test_client()


def out(name, text):
    print(f"RESULT {name}: {text}", flush=True)


# Findings 1 and 2: the decision map vs the real follow-up and the caregiver's decline.
try:
    c = private_client()
    inv = c.post(f"/api/investigations?scenario=care_home_v1&at={T231}").get_json()["investigation_id"]
    fu = c.get(f"/api/follow-ups/{inv}?at={T231}").get_json()
    perm = fu["caregiver_permission"]["notification_id"]
    c.post(f"/api/notifications/{perm}/caregiver-decision", json={"decision": "decline", "at": T231})
    fu621 = c.get(f"/api/follow-ups/{inv}?at={T621}").get_json()
    tr = c.get(f"/api/trace?scenario=care_home_v1&at={T621}&investigation_id={inv}").get_json()
    hvac = [n for n in tr.get("notices", []) if n.get("audience") == "hvac_company"]
    out("F1 map verification vs follow-up at 06:21", f"follow-up={fu621['verification']['stage']} map={tr['verification'].get('stage')} -> {'AGREE' if fu621['verification']['stage'] == tr['verification'].get('stage') else 'DISAGREE'}")
    out("F2 map after an in-app decline", f"follow-up permission={fu621['caregiver_permission']['status']} map permission={(tr.get('permission') or {}).get('status')} map HVAC allowed={[n.get('allowed') for n in hvac]}")
except Exception as exc:
    out("F1/F2", f"probe error {type(exc).__name__}: {exc}")

# Finding 3: 502 distinct client-chosen cookies of valid syntax vs the 500-session cap.
try:
    sd = Path(tempfile.mkdtemp()) / "sessions"
    from aria_home import public_demo
    c = public_client(sd)
    codes = {}
    for i in range(502):
        sid = public_demo.new_session_id() if hasattr(public_demo, "new_session_id") else f"{i:032x}"
        c.set_cookie(public_demo.SESSION_COOKIE, sid) if "key" not in c.set_cookie.__code__.co_varnames else c.set_cookie(key=public_demo.SESSION_COOKIE, value=sid)
        r = c.post(f"/api/investigations?scenario=care_home_v1&at={T231}")
        codes[r.status_code] = codes.get(r.status_code, 0) + 1
    files = [p for p in sd.rglob("*") if p.is_file()]
    out("F3 502 forged cookies", f"status counts={codes} session files created={len(files)} bytes={sum(p.stat().st_size for p in files)} (cap 500)")
except Exception as exc:
    out("F3", f"probe error {type(exc).__name__}: {exc}")

# Finding 4: an off-checkpoint acknowledgement in public mode is rejected; is it written anyway?
try:
    sd = Path(tempfile.mkdtemp()) / "sessions"
    c = public_client(sd)
    inv = c.post(f"/api/investigations?scenario=care_home_v1&at={T231}").get_json()["investigation_id"]
    rows = c.get(f"/api/notifications?investigation_id={inv}&at={T231}").get_json()["notifications"]
    cg = next(r for r in rows if r["audience"] == "family_caregiver" and r["state"] == "simulated_delivered")
    r = c.post(f"/api/notifications/{cg['id']}/ack", json={"actor": "family_caregiver", "at": "2026-01-17T02:32:00-05:00"})
    after = c.get(f"/api/notifications?investigation_id={inv}").get_json()["notifications"]
    acks = next(x for x in after if x["id"] == cg["id"]).get("acks", [])
    out("F4 off-checkpoint ack 02:32", f"HTTP {r.status_code}, acks stored afterwards={len(acks)}")
except Exception as exc:
    out("F4", f"probe error {type(exc).__name__}: {exc}")

# Finding 7: a malformed caregiver decision body.
try:
    c = private_client()
    inv = c.post(f"/api/investigations?scenario=care_home_v1&at={T231}").get_json()["investigation_id"]
    perm = c.get(f"/api/follow-ups/{inv}?at={T231}").get_json()["caregiver_permission"]["notification_id"]
    res = []
    for bad in ([], {}, None, 5, True):
        r = c.post(f"/api/notifications/{perm}/caregiver-decision", json={"decision": bad, "at": T231})
        res.append(f"{json.dumps(bad)}->{r.status_code}")
    out("F7 malformed decision values", ", ".join(res))
except Exception as exc:
    out("F7", f"probe error {type(exc).__name__}: {exc}")

# Finding 5: copy one real recording, change only its interpretation, and see whether the app still shows the old review.
try:
    rec_files = sorted(glob.glob(str(backend / "eval" / "recorded" / "care-*.json")))
    entries = [a for f in rec_files for a in json.load(open(f, encoding="utf-8"))["answers"]]
    target = next(a for a in entries if a.get("evaluated_at_utc") == "2026-01-17T07:31:00Z" and a.get("status", "accepted") != "rejected")
    rd = Path(tempfile.mkdtemp())
    for label, interp in (("original", None), ("tampered", "The furnace is certainly fine and the house will be warm by 7:00.")):
        e = copy.deepcopy(target)
        if interp:
            e["output"]["interpretation"] = interp
        d = rd / label
        d.mkdir()
        (d / "answers.json").write_text(json.dumps({"answers": [e]}), encoding="utf-8")
        os.environ["ARIA_HOME_RECORDED_DIR"] = str(d)
        sd = Path(tempfile.mkdtemp()) / "s"
        c = public_client(sd)
        body = c.post(f"/api/investigations?scenario=care_home_v1&at={T231}").get_json()
        s = json.dumps(body)
        review_shown = '"muse-wonder-1.0"' in s and '"verdict"' in s
        mismatch = "does not match this answer" in s
        out(f"F5 {label} answer", f"recorded answer served={'recorded' in s and 'muse-spark-1.3' in s}; wonder review shown={review_shown}; mismatch note={mismatch}")
    os.environ["ARIA_HOME_RECORDED_DIR"] = ""
except Exception as exc:
    out("F5", f"probe error {type(exc).__name__}: {exc}")
