New task, same project (ARIA Home: Flask backend, SQLite store, synthetic care scenario). Reply ONLY with complete, pasteable Python code blocks, each headed by the file path and exactly where it goes (new function / replace function X). One line of prose per block at most. No placeholders, no "..." in code.

GOAL: before ARIA contacts the HVAC company, the family caregiver must approve in the app. Approval never changes readiness or verification.

EXISTING CODE YOU MUST FIT (backend/aria_home/notifications.py, excerpts):
HVAC_AUTH_EVENT_KINDS = ("manager_hvac_authorized", "caregiver_hvac_authorized")
def _get(obj, name, default=None): dict.get or getattr
def _uses_caregiver(scenario): True for scenario.manifest.id == "care_home_v1"
def hvac_is_authorized(events):
    return any(_get(event, "kind") in HVAC_AUTH_EVENT_KINDS for event in (events or []))
def _decision(audience, kind, allowed, reason, payload, investigation_id):
    return {"audience": audience, "kind": kind, "allowed": allowed, "reason": reason, "payload": payload, "idempotency_key": f"{investigation_id}:{audience}:{kind}"}
def decide_hvac_notification(investigation=None, readiness=None, verification=None, context=None, events=None, now=None, scenario=None, investigation_id=""):
    payload = build_payload("hvac_company", investigation, readiness, verification, context, events, now, scenario)
    if hvac_is_authorized(events):
        return _decision("hvac_company", payload["kind"], True, None, payload, investigation_id)
    reason = "caregiver_hvac_not_authorized" if _uses_caregiver(scenario) else "manager_hvac_not_authorized"
    return _decision("hvac_company", payload["kind"], False, reason, payload, investigation_id)
def create_hvac_notification(store, scenario, investigation_id, investigation, readiness, at, verification=None):
    context = context_as_of(scenario, at) if scenario is not None else None
    events = events_as_of(scenario, at) if scenario is not None else []
    decision = decide_hvac_notification(investigation, readiness, verification, context, events, at, scenario, investigation_id)
    created_at = at
    if decision["allowed"] and scenario is not None:
        gate_at = next((_get(e, "available_at") for e in (getattr(scenario, "events", None) or []) if _get(e, "kind") in HVAC_AUTH_EVENT_KINDS), None)
        created_at = _deterministic_created_at(store, scenario, investigation_id, gate_at, at)
    return _persist_decisions(store, investigation_id, [decision], created_at)[0]
_persist_decisions(store, investigation_id, decisions, created_at) saves allowed decisions as state "simulated_delivered" and refused ones as state "refused" with refusal_reason, idempotent on idempotency_key; returns the rows (dicts with id, audience, kind, payload, created_at, state).
ALLOWLISTS["family_caregiver"] = {"audience", "kind", "property_label", "verified_facts", "readiness", "requested_action", "access_note"}; validate_payload(audience, payload) raises if a key is outside the allowlist.
The caregiver_alert notification (audience family_caregiver, kind caregiver_alert) already exists and is created when readiness is at_risk.

Store (backend/aria_home/store.py, class Store): schema is a list `statements` of CREATE TABLE IF NOT EXISTS strings run at init. Helpers: `with self._connection() as conn:` (sqlite3 rows by name), `_iso(dt)` -> ISO string, `_parse_dt(value)` -> aware datetime. Example method:
    def record_ack(self, notification_id, actor, acknowledged_at):
        at = _parse_dt(acknowledged_at)
        if at is None or at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("acknowledged_at must be timezone-aware")
        with self._connection() as conn:
            conn.execute("INSERT OR IGNORE INTO notification_acks (id, notification_id, actor, acknowledged_at) VALUES (?, ?, ?, ?)", (...))

Scenario records: scenario.records is a list of EvidenceRecord with fields source (enum SourceKind; compare with `.value`, e.g. "room_sensor", "thermostat"), quantity (room sensor temperature is "indoor_temp"), value (float), unit, observed_at, received_at (aware datetimes). A record is visible at time t only if received_at <= t.

WRITE:
1. Store: a table caregiver_decisions (investigation_id TEXT PRIMARY KEY, decision TEXT NOT NULL CHECK(decision IN ('approved','declined')), actor TEXT NOT NULL, decided_at TEXT NOT NULL, notification_id TEXT NOT NULL); the CREATE statement string to append to `statements`; method record_caregiver_decision(self, investigation_id, notification_id, decision, actor, decided_at) -> (row_dict, created_bool), once-only (INSERT OR IGNORE, then read back; created False if a row already existed); method get_caregiver_decision(self, investigation_id, at=None) -> dict or None, returning None when at is given and decided_at > at.
2. notifications.py:
   a. decide_hvac_notification gains keyword caregiver_decision=None (a dict with "decision" and "decided_at" or None). Rules: decision "declined" -> refused with reason "caregiver_declined"; decision "approved" -> allowed; no decision -> existing event rule unchanged.
   b. create_hvac_notification gains keyword caregiver_decision=None and passes it on; when allowed by an approved decision, gate_at is the decision's decided_at (parsed to datetime if a string) instead of the scenario event time.
   c. caregiver_permission_text(scenario, at) -> str. Exactly: "ARIA Home (synthetic scenario): your mother's home is cooling ({temp} F, furnace quiet since {quiet}). May I contact the HVAC company? Approve or decline in ARIA Home." temp = latest visible room_sensor indoor_temp value at `at`, rounded to whole degrees; quiet = observed_at of the latest visible thermostat record formatted "%H:%M" in that datetime's own timezone. If either is missing, use "temperature unknown" / "unknown" in its place (never invent a number).
   d. create_caregiver_updates(store, scenario, investigation_id, hvac_row, verification, at) -> list of rows: if hvac_row is not None and hvac_row["state"] == "simulated_delivered", persist (via _persist_decisions with allowed decisions) a family_caregiver notification kind "caregiver_update_hvac_contacted" created at hvac_row["created_at"]; and if verification and verification.get("stage") in ("goal_verified", "arrival_met") and verification.get("goal_verified_at"), persist kind "caregiver_update_goal_verified" created at goal_verified_at. Payload keys only from the family_caregiver allowlist: audience, kind, property_label (take it from hvac_row["payload"]["property_label"]), verified_facts (["HVAC company contacted with the allowed fields only"] or ["Temperature goal verified from independent room readings"]), readiness ("informational"), requested_action ("None: for your information"), access_note (from hvac_row["payload"].get("access_note")). Call validate_payload on each.
3. whatsapp.py: refactor attempt_hvac_whatsapp_delivery into a shared private _attempt_delivery(store, notification, text, *, env=None, http_post=None, recipient=None) holding the existing config / already_attempted / recipient refusal / claim / send / state-update logic unchanged; attempt_hvac_whatsapp_delivery keeps its signature and behaviour (audience hvac_company only, reason "not_hvac_notice" otherwise, text = build_hvac_whatsapp_text(payload)). Add attempt_caregiver_permission_whatsapp(store, notification, text, *, env=None, http_post=None, recipient=None): only for audience family_caregiver and kind caregiver_alert (otherwise {"attempted": False, "reason": "not_caregiver_permission"}), state must be simulated_delivered, text sent is "ARIA Home test (synthetic scenario)\nTo the owner's test number on WhatsApp (stands in for the family caregiver)\n" + text. Same once-only rule per notification id.
4. backend/tests/test_caregiver_permission.py using only fakes (fake http_post callable recording calls; Store on a tmp_path db: `from aria_home.store import Store; store = Store(str(tmp_path / "t.db"))`): decline -> decide_hvac_notification refused "caregiver_declined" even when events contain caregiver_hvac_authorized; approve -> allowed with no events; no decision + no event -> refused; record_caregiver_decision is once-only (second call returns created False and the first decision); get_caregiver_decision hides a decision whose decided_at is after `at`; caregiver permission WhatsApp: not configured env -> not_configured and zero http calls; configured env dict {"WHATSAPP_TOKEN": "FAKE-TOKEN", "WHATSAPP_PHONE_NUMBER_ID": "111", "WHATSAPP_TEST_RECIPIENT": "15550000000", "ARIA_HOME_WHATSAPP_LIVE": "1"} with fake returning (200, {"messages": [{"id": "wamid.FAKE"}]}) -> exactly one call, second attempt -> already_attempted and still one call; an hvac_company notification passed to the caregiver function -> not_caregiver_permission with zero calls; the token never appears in the returned dict.
   To make a notification row for the WhatsApp tests, use: store.save_notification(investigation_id="inv-1", audience="family_caregiver", kind="caregiver_alert", idempotency_key="inv-1:family_caregiver:caregiver_alert", payload={"audience": "family_caregiver", "kind": "caregiver_alert"}, created_at=<aware datetime>, delivery="simulated", state="simulated_delivered") which returns the row dict.
