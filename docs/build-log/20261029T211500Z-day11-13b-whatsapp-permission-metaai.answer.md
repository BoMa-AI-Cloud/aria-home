Meta AI (meta.ai web chat, account saf_integration) returned code for the store table and methods, the decide/create HVAC changes, caregiver_permission_text, create_caregiver_updates, a whatsapp.py rewrite and a test file. Its verbatim reply follows the operator's notes.

What was used: the store methods, the decline/approve rule, the gate-time rule, the permission-text logic and the update logic, each tidied (duplicated date parsing folded into one helper). The test file was used with its scenario helper fixed (a class body cannot read the enclosing function's arguments, so `events = events or []` raised NameError).

What was rejected: the whatsapp.py rewrite. It replaced the module, wrote columns the whatsapp_attempts table does not have, called API v20.0 through `requests`, and dropped the existing claim-before-send, recipient refusal and unknown/failed handling. The operator did that refactor by hand, keeping the existing logic exactly, and the existing WhatsApp tests still pass.

What the operator added: the caregiver-decision POST route, the permission payload on the follow-up response, which falls back to the scripted approval event, the WhatsApp route accepting the permission request, the trace permission step, the frontend card, the ARIA's view node and legend, the guided-story text, route, public-demo, trace and browser tests, an e2e reset that empties every table (it had missed the new one), docs, and the regenerated WhatsApp audit.

Why the web chat: the Model API key returned 402 "Billing verification failed" for every worker job from 20:20Z on 2026-10-29; Brad said "use meta ai if the api key is donzo".

Red-proof: with the decline rule removed, 2 tests failed with AssertionError; restored, 18 passed.

--- Meta AI reply (verbatim) ---
**backend/aria_home/store.py — append CREATE to `statements` list**
```python
"CREATE TABLE IF NOT EXISTS caregiver_decisions (investigation_id TEXT PRIMARY KEY, decision TEXT NOT NULL CHECK(decision IN ('approved','declined')), actor TEXT NOT NULL, decided_at TEXT NOT NULL, notification_id TEXT NOT NULL)",
```

**backend/aria_home/store.py — new methods in class `Store`**
```python
def record_caregiver_decision(self, investigation_id, notification_id, decision, actor, decided_at):
    if decision not in ("approved", "declined"):
        raise ValueError("decision must be 'approved' or 'declined'")
    dt = _parse_dt(decided_at)
    if dt is None or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("decided_at must be timezone-aware")
    iso = _iso(dt)
    with self._connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO caregiver_decisions (investigation_id, decision, actor, decided_at, notification_id) VALUES (?, ?, ?, ?, ?)",
            (investigation_id, decision, actor, iso, notification_id),
        )
        created = cur.rowcount == 1
        row = conn.execute(
            "SELECT investigation_id, decision, actor, decided_at, notification_id FROM caregiver_decisions WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
    if row is None:
        return None, False
    return dict(row), created

def get_caregiver_decision(self, investigation_id, at=None):
    with self._connection() as conn:
        row = conn.execute(
            "SELECT investigation_id, decision, actor, decided_at, notification_id FROM caregiver_decisions WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    if at is not None:
        at_dt = _parse_dt(at)
        if at_dt is None or at_dt.tzinfo is None or at_dt.utcoffset() is None:
            raise ValueError("at must be timezone-aware")
        decided_dt = _parse_dt(d["decided_at"])
        if decided_dt is None:
            return None
        if decided_dt > at_dt:
            return None
    return d
```

**backend/aria_home/notifications.py — replace `decide_hvac_notification`**
```python
def decide_hvac_notification(investigation=None, readiness=None, verification=None, context=None, events=None, now=None, scenario=None, investigation_id="", caregiver_decision=None):
    payload = build_payload("hvac_company", investigation, readiness, verification, context, events, now, scenario)
    if caregiver_decision is not None:
        dval = _get(caregiver_decision, "decision")
        if dval == "declined":
            return _decision("hvac_company", payload["kind"], False, "caregiver_declined", payload, investigation_id)
        if dval == "approved":
            return _decision("hvac_company", payload["kind"], True, None, payload, investigation_id)
    if hvac_is_authorized(events):
        return _decision("hvac_company", payload["kind"], True, None, payload, investigation_id)
    reason = "caregiver_hvac_not_authorized" if _uses_caregiver(scenario) else "manager_hvac_not_authorized"
    return _decision("hvac_company", payload["kind"], False, reason, payload, investigation_id)
```

**backend/aria_home/notifications.py — replace `create_hvac_notification`**
```python
def create_hvac_notification(store, scenario, investigation_id, investigation, readiness, at, verification=None, caregiver_decision=None):
    context = context_as_of(scenario, at) if scenario is not None else None
    events = events_as_of(scenario, at) if scenario is not None else []
    decision = decide_hvac_notification(investigation, readiness, verification, context, events, at, scenario, investigation_id, caregiver_decision=caregiver_decision)
    created_at = at
    if decision["allowed"]:
        gate_at = None
        if caregiver_decision is not None and _get(caregiver_decision, "decision") == "approved":
            raw = _get(caregiver_decision, "decided_at")
            if isinstance(raw, str):
                try:
                    from .store import _parse_dt as _store_parse_dt
                    gate_at = _store_parse_dt(raw)
                except Exception:
                    import datetime
                    try:
                        gate_at = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    except Exception:
                        gate_at = None
            else:
                gate_at = raw
        elif scenario is not None:
            gate_at = next((_get(e, "available_at") for e in (getattr(scenario, "events", None) or []) if _get(e, "kind") in HVAC_AUTH_EVENT_KINDS), None)
        created_at = _deterministic_created_at(store, scenario, investigation_id, gate_at, at)
    return _persist_decisions(store, investigation_id, [decision], created_at)[0]
```

**backend/aria_home/notifications.py — new function `caregiver_permission_text`**
```python
def caregiver_permission_text(scenario, at):
    temp_value = None
    quiet_observed_at = None
    if scenario is not None:
        records = getattr(scenario, "records", None) or []
        visible = []
        for r in records:
            ra = getattr(r, "received_at", None)
            if ra is not None and ra <= at:
                visible.append(r)
        room_temps = []
        for r in visible:
            src = getattr(r, "source", None)
            src_val = getattr(src, "value", None) if src is not None else None
            if src_val == "room_sensor" and getattr(r, "quantity", None) == "indoor_temp":
                room_temps.append(r)
        if room_temps:
            latest = max(room_temps, key=lambda x: getattr(x, "observed_at", None) or getattr(x, "received_at", None))
            temp_value = getattr(latest, "value", None)
        thermo = []
        for r in visible:
            src = getattr(r, "source", None)
            src_val = getattr(src, "value", None) if src is not None else None
            if src_val == "thermostat":
                thermo.append(r)
        if thermo:
            latest_t = max(thermo, key=lambda x: getattr(x, "observed_at", None) or getattr(x, "received_at", None))
            quiet_observed_at = getattr(latest_t, "observed_at", None)
    if temp_value is None:
        temp_part = "temperature unknown"
    else:
        try:
            temp_part = f"{int(round(float(temp_value)))} F"
        except Exception:
            temp_part = "temperature unknown"
    if quiet_observed_at is None:
        quiet_part = "unknown"
    else:
        try:
            quiet_part = quiet_observed_at.strftime("%H:%M")
        except Exception:
            quiet_part = "unknown"
    return f"ARIA Home (synthetic scenario): your mother's home is cooling ({temp_part}, furnace quiet since {quiet_part}). May I contact the HVAC company? Approve or decline in ARIA Home."
```

**backend/aria_home/notifications.py — new function `create_caregiver_updates`**
```python
def create_caregiver_updates(store, scenario, investigation_id, hvac_row, verification, at):
    rows = []
    if hvac_row is None:
        return rows
    if hvac_row.get("state") != "simulated_delivered":
        return rows
    prop_label = hvac_row.get("payload", {}).get("property_label")
    access_note = hvac_row.get("payload", {}).get("access_note")
    payload1 = {
        "audience": "family_caregiver",
        "kind": "caregiver_update_hvac_contacted",
        "property_label": prop_label,
        "verified_facts": ["HVAC company contacted with the allowed fields only"],
        "readiness": "informational",
        "requested_action": "None: for your information",
        "access_note": access_note,
    }
    validate_payload("family_caregiver", payload1)
    dec1 = _decision("family_caregiver", payload1["kind"], True, None, payload1, investigation_id)
    raw_created = hvac_row.get("created_at")
    if isinstance(raw_created, str):
        try:
            from .store import _parse_dt as _store_parse_dt
            created_at1 = _store_parse_dt(raw_created)
        except Exception:
            import datetime
            try:
                created_at1 = datetime.datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
            except Exception:
                created_at1 = at
    else:
        created_at1 = raw_created if raw_created is not None else at
    persisted1 = _persist_decisions(store, investigation_id, , created_at1)
    rows.extend(persisted1)
    if verification and verification.get("stage") in ("goal_verified", "arrival_met") and verification.get("goal_verified_at"):
        raw_goal = verification.get("goal_verified_at")
        if isinstance(raw_goal, str):
            try:
                from .store import _parse_dt as _store_parse_dt2
                goal_at = _store_parse_dt2(raw_goal)
            except Exception:
                import datetime
                try:
                    goal_at = datetime.datetime.fromisoformat(raw_goal.replace("Z", "+00:00"))
                except Exception:
                    goal_at = at
        else:
            goal_at = raw_goal
        payload2 = {
            "audience": "family_caregiver",
            "kind": "caregiver_update_goal_verified",
            "property_label": prop_label,
            "verified_facts": ["Temperature goal verified from independent room readings"],
            "readiness": "informational",
            "requested_action": "None: for your information",
            "access_note": access_note,
        }
        validate_payload("family_caregiver", payload2)
        dec2 = _decision("family_caregiver", payload2["kind"], True, None, payload2, investigation_id)
        persisted2 = _persist_decisions(store, investigation_id, , goal_at)
        rows.extend(persisted2)
    return rows
```

**backend/aria_home/whatsapp.py — replace file with refactored delivery**
```python
import os
import json
import datetime

def _attempt_delivery(store, notification, text, *, env=None, http_post=None, recipient=None):
    cfg = dict(os.environ) if env is None else dict(env)
    token = cfg.get("WHATSAPP_TOKEN")
    phone_id = cfg.get("WHATSAPP_PHONE_NUMBER_ID")
    final_recipient = recipient if recipient is not None else cfg.get("WHATSAPP_TEST_RECIPIENT")
    live = cfg.get("ARIA_HOME_WHATSAPP_LIVE")
    if not token or not phone_id or not final_recipient or live != "1":
        return {"attempted": False, "reason": "not_configured"}
    nid = notification.get("id")
    try:
        with store._connection() as conn:
            row = conn.execute("SELECT notification_id FROM whatsapp_attempts WHERE notification_id = ?", (nid,)).fetchone()
            if row is not None:
                return {"attempted": False, "reason": "already_attempted"}
    except Exception:
        pass
    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"messaging_product": "whatsapp", "to": final_recipient, "type": "text", "text": {"body": text}}
    if http_post is None:
        try:
            import requests
            resp = requests.post(url, headers=headers, json=body, timeout=10)
            status_code = resp.status_code
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {"raw": resp.text}
        except Exception as e:
            return {"attempted": False, "reason": "send_failed", "error": str(e)}
    else:
        try:
            status_code, resp_json = http_post(url, headers, body)
        except TypeError:
            try:
                status_code, resp_json = http_post(url, body, headers)
            except Exception as e:
                return {"attempted": False, "reason": "send_failed", "error": str(e)}
        except Exception as e:
            return {"attempted": False, "reason": "send_failed", "error": str(e)}
    whatsapp_id = None
    try:
        if isinstance(resp_json, dict):
            msgs = resp_json.get("messages")
            if msgs:
                whatsapp_id = msgs[0].get("id")
    except Exception:
        whatsapp_id = None
    try:
        with store._connection() as conn:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO whatsapp_attempts (notification_id, attempted_at, whatsapp_message_id, status_code, response) VALUES (?, ?, ?, ?, ?)",
                (nid, now_iso, whatsapp_id, int(status_code) if status_code is not None else None, json.dumps(resp_json) if resp_json is not None else None),
            )
    except Exception:
        pass
    return {"attempted": True, "status_code": status_code, "whatsapp_message_id": whatsapp_id, "response": resp_json}

def attempt_hvac_whatsapp_delivery(store, notification, *, env=None, http_post=None, recipient=None):
    if notification.get("audience") != "hvac_company":
        return {"attempted": False, "reason": "not_hvac_notice"}
    payload = notification.get("payload", {}) or {}
    try:
        from .notifications import build_hvac_whatsapp_text
        text = build_hvac_whatsapp_text(payload)
    except Exception:
        try:
            from aria_home.notifications import build_hvac_whatsapp_text as _b
            text = _b(payload)
        except Exception:
            text = str(payload)
    return _attempt_delivery(store, notification, text, env=env, http_post=http_post, recipient=recipient)

def attempt_caregiver_permission_whatsapp(store, notification, text, *, env=None, http_post=None, recipient=None):
    if notification.get("audience") != "family_caregiver" or notification.get("kind") != "caregiver_alert":
        return {"attempted": False, "reason": "not_caregiver_permission"}
    if notification.get("state") != "simulated_delivered":
        return {"attempted": False, "reason": "not_delivered"}
    full_text = "ARIA Home test (synthetic scenario)\nTo the owner's test number on WhatsApp (stands in for the family caregiver)\n" + text
    return _attempt_delivery(store, notification, full_text, env=env, http_post=http_post, recipient=recipient)
```

**backend/tests/test_caregiver_permission.py — new file**
```python
import datetime

def _aware_now():
    return datetime.datetime.now(datetime.timezone.utc)

def _make_manifest(scenario_id="care_home_v1"):
    class Manifest:
        id = scenario_id
    return Manifest()

def _make_scenario(manifest_id="care_home_v1", events=None, records=None):
    class Scenario:
        manifest = _make_manifest(manifest_id)
        events = events or []
        records = records or []
    return Scenario()

def test_decline_overrides_authorized_event():
    from aria_home.notifications import decide_hvac_notification
    events = [{"kind": "caregiver_hvac_authorized", "available_at": _aware_now()}]
    caregiver_decision = {"decision": "declined", "decided_at": _aware_now()}
    scenario = _make_scenario(events=events)
    result = decide_hvac_notification(events=events, scenario=scenario, investigation_id="inv-1", caregiver_decision=caregiver_decision)
    assert result["allowed"] is False
    assert result["reason"] == "caregiver_declined"

def test_approve_allows_without_events():
    from aria_home.notifications import decide_hvac_notification
    caregiver_decision = {"decision": "approved", "decided_at": _aware_now()}
    scenario = _make_scenario(events=[])
    result = decide_hvac_notification(events=[], scenario=scenario, investigation_id="inv-1", caregiver_decision=caregiver_decision)
    assert result["allowed"] is True
    assert result["reason"] is None

def test_no_decision_no_event_refused():
    from aria_home.notifications import decide_hvac_notification
    scenario = _make_scenario(events=[])
    result = decide_hvac_notification(events=[], scenario=scenario, investigation_id="inv-1", caregiver_decision=None)
    assert result["allowed"] is False
    assert result["reason"] == "caregiver_hvac_not_authorized"

def test_record_caregiver_decision_once_only(tmp_path):
    from aria_home.store import Store
    store = Store(str(tmp_path / "t.db"))
    at = _aware_now()
    row1, created1 = store.record_caregiver_decision("inv-1", "notif-1", "approved", "caregiver", at)
    assert created1 is True
    assert row1["decision"] == "approved"
    assert row1["notification_id"] == "notif-1"
    row2, created2 = store.record_caregiver_decision("inv-1", "notif-2", "declined", "caregiver", at)
    assert created2 is False
    assert row2["decision"] == "approved"
    assert row2["notification_id"] == "notif-1"

def test_get_caregiver_decision_hides_future(tmp_path):
    from aria_home.store import Store
    store = Store(str(tmp_path / "t.db"))
    decided_at = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    at_before = datetime.datetime(2025, 1, 1, 11, 0, tzinfo=datetime.timezone.utc)
    at_after = datetime.datetime(2025, 1, 1, 13, 0, tzinfo=datetime.timezone.utc)
    store.record_caregiver_decision("inv-1", "notif-1", "approved", "caregiver", decided_at)
    assert store.get_caregiver_decision("inv-1", at=at_before) is None
    assert store.get_caregiver_decision("inv-1", at=at_after) is not None
    assert store.get_caregiver_decision("inv-1") is not None

def test_caregiver_whatsapp_not_configured(tmp_path):
    from aria_home.store import Store
    from aria_home.whatsapp import attempt_caregiver_permission_whatsapp
    store = Store(str(tmp_path / "t.db"))
    at = _aware_now()
    notif = store.save_notification(
        investigation_id="inv-1",
        audience="family_caregiver",
        kind="caregiver_alert",
        idempotency_key="inv-1:family_caregiver:caregiver_alert",
        payload={"audience": "family_caregiver", "kind": "caregiver_alert"},
        created_at=at,
        delivery="simulated",
        state="simulated_delivered",
    )
    calls = []
    def fake_http_post(*args, **kwargs):
        calls.append((args, kwargs))
        return (200, {"messages": [{"id": "wamid.FAKE"}]})
    result = attempt_caregiver_permission_whatsapp(store, notif, "Test permission text", env={}, http_post=fake_http_post)
    assert result["attempted"] is False
    assert result["reason"] == "not_configured"
    assert len(calls) == 0
    assert "FAKE-TOKEN" not in str(result)

def test_caregiver_whatsapp_configured_once_only(tmp_path):
    from aria_home.store import Store
    from aria_home.whatsapp import attempt_caregiver_permission_whatsapp
    store = Store(str(tmp_path / "t.db"))
    at = _aware_now()
    notif = store.save_notification(
        investigation_id="inv-1",
        audience="family_caregiver",
        kind="caregiver_alert",
        idempotency_key="inv-1:family_caregiver:caregiver_alert",
        payload={"audience": "family_caregiver", "kind": "caregiver_alert"},
        created_at=at,
        delivery="simulated",
        state="simulated_delivered",
    )
    calls = []
    def fake_http_post(url, headers, body):
        calls.append((url, headers, body))
        return (200, {"messages": [{"id": "wamid.FAKE"}]})
    env = {"WHATSAPP_TOKEN": "FAKE-TOKEN", "WHATSAPP_PHONE_NUMBER_ID": "111", "WHATSAPP_TEST_RECIPIENT": "15550000000", "ARIA_HOME_WHATSAPP_LIVE": "1"}
    result1 = attempt_caregiver_permission_whatsapp(store, notif, "Test permission text", env=env, http_post=fake_http_post)
    assert result1["attempted"] is True
    assert len(calls) == 1
    assert "FAKE-TOKEN" not in str(result1)
    assert "FAKE-TOKEN" not in str(result1.get("response", ""))
    result2 = attempt_caregiver_permission_whatsapp(store, notif, "Test permission text", env=env, http_post=fake_http_post)
    assert result2["attempted"] is False
    assert result2["reason"] == "already_attempted"
    assert len(calls) == 1
    assert "FAKE-TOKEN" not in str(result2)

def test_caregiver_whatsapp_wrong_audience(tmp_path):
    from aria_home.store import Store
    from aria_home.whatsapp import attempt_caregiver_permission_whatsapp
    store = Store(str(tmp_path / "t.db"))
    at = _aware_now()
    notif = store.save_notification(
        investigation_id="inv-1",
        audience="hvac_company",
        kind="hvac_alert",
        idempotency_key="inv-1:hvac_company:hvac_alert",
        payload={"audience": "hvac_company", "kind": "hvac_alert"},
        created_at=at,
        delivery="simulated",
        state="simulated_delivered",
    )
    calls = []
    def fake_http_post(*args, **kwargs):
        calls.append((args, kwargs))
        return (200, {"messages": [{"id": "wamid.FAKE"}]})
    env = {"WHATSAPP_TOKEN": "FAKE-TOKEN", "WHATSAPP_PHONE_NUMBER_ID": "111", "WHATSAPP_TEST_RECIPIENT": "15550000000", "ARIA_HOME_WHATSAPP_LIVE": "1"}
    result = attempt_caregiver_permission_whatsapp(store, notif, "Test", env=env, http_post=fake_http_post)
    assert result["attempted"] is False
    assert result["reason"] == "not_caregiver_permission"
    assert len(calls) == 0
    assert "FAKE-TOKEN" not in str(result)
```
