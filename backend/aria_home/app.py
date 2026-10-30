"""Flask application factory for the ARIA Home backend."""
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, g, has_request_context, jsonify, request, send_file

from aria_home import public_demo
from aria_home.recorded import annotate_public_result, public_investigation
from aria_home.review import load_recorded_reviews, recorded_review_for
from aria_home.transcribe import human_report_for
from aria_home.watcher import load_correction_records, load_recorded_watchers, public_watcher

from aria_home.contracts import Availability, SourceKind
from aria_home.eligibility import eligible_records
from aria_home.evidence import freshness, source_status
from aria_home.metrics import NOISE_FLOOR_W, circuit_activity, target_gap, temperature_trend
from aria_home.investigator import Investigation, build_evidence_pack, inference_identity, investigate
from aria_home.outcomes import evaluate_outcome, follow_up_for
from aria_home.store import Store
from aria_home.power_context import power_context
from aria_home.provider import ProviderConfig, get_provider
from aria_home.scenario import context_as_of, events_as_of, load_scenario, visible_records, visual_as_of
from aria_home.readiness import compute_readiness
from aria_home.scheduling import compute_follow_up_schedule
from aria_home.verification import build_evidence_timeline, verify_recovery
from aria_home.notifications import caregiver_permission_text, create_caregiver_updates, create_hvac_notification, create_investigation_notifications
from aria_home.whatsapp import attempt_caregiver_permission_whatsapp, attempt_hvac_whatsapp_delivery, whatsapp_config_from_env
from aria_home.emporia import read_live_power
from aria_home import nest as nest_camera

SCENARIO_PATH = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def release_version(base_dir: Path | None = None) -> dict:
    """The deployed commit: ARIA_HOME_RELEASE_COMMIT, else backend/RELEASE_COMMIT, else "unknown". Never git."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
    env_value = os.environ.get("ARIA_HOME_RELEASE_COMMIT", "").strip()
    if env_value and _SHA_RE.fullmatch(env_value):
        return {"commit": env_value, "source": "env"}
    try:
        lines = (Path(base_dir) / "RELEASE_COMMIT").read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        lines = []
    first = lines[0].strip() if lines else ""
    if first and _SHA_RE.fullmatch(first):
        return {"commit": first, "source": "file"}
    return {"commit": "unknown", "source": "not stamped"}


def _recorded_review_for_display(scn, at, pack):
    try:
        identity = inference_identity(scn, at)
    except Exception:
        return None
    try:
        entries = load_recorded_reviews()
    except Exception:
        return None
    evidence_ids = pack.get("evidence_ids") if isinstance(pack, dict) else None
    try:
        return recorded_review_for(entries, scn.manifest.id, identity["evaluated_at_utc"], identity["input_revision"], evidence_ids or [])
    except Exception:
        return None


def _human_report_for_display(scn, at):
    try:
        return human_report_for(scn, at)
    except Exception:
        return None


_FLAGGABLE_READINESS = ("at_risk", "arrival_passed")


def _telemetry_missing_at(scn, at):
    visible = [r for r in scn.records if r.received_at <= at]
    thermostat = sorted(
        [r for r in eligible_records(visible, "indoor_temp") if r.source is SourceKind.thermostat],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    if not thermostat:
        return False
    return freshness(thermostat[-1], at) is not Availability.available


def _follow_up_anchor(scn, at):
    if not any(r.source is SourceKind.room_sensor for r in scn.records):
        return at
    for checkpoint in sorted(public_demo.parsed_checkpoints(scn.manifest.id)):
        if checkpoint > at:
            break
        if _telemetry_missing_at(scn, checkpoint):
            return checkpoint
    return at


def create_app():
    public = public_demo.is_public_demo()
    if public:
        public_demo.check_fail_closed()
    app = Flask(__name__)
    if public:
        app.debug = False
    scenario = load_scenario(SCENARIO_PATH)

    def _not_registered(*args, **kwargs):
        def _wrap(func):
            return func

        return _wrap

    live_only_get = app.get if not public else _not_registered
    live_only_post = app.post if not public else _not_registered

    @app.get("/api/health")
    def health():
        db_marker = Path(os.environ.get("ARIA_HOME_DB_PATH") or "").name or None
        return jsonify({"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic", "scenario": scenario.manifest.id, "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(), "timezone": scenario.manifest.timezone, "db_marker": db_marker, "public_demo": public, "version": release_version()})

    @app.get("/api/evaluation/offline")
    def evaluation_offline():
        import json

        path = Path(__file__).resolve().parent.parent / "eval" / "results-offline.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("scenario", scenario.manifest.id)
            payload.setdefault("at", (scenario.manifest.start + timedelta(hours=3)).isoformat())
            payload.setdefault("timezone", scenario.manifest.timezone)
        return jsonify(payload)

    @app.get("/api/laws")
    def laws_endpoint():
        from aria_home import laws as laws_module

        registry = laws_module.load_laws()
        counts = {law["id"]: 0 for law in registry["model_laws"]}
        try:
            from aria_home.recorded import load_recorded_answers

            recorded_outputs = [
                item["answer"].get("output")
                for item in load_recorded_answers()
                if isinstance(item.get("answer"), dict) and isinstance(item["answer"].get("output"), dict)
            ]
        except Exception:
            recorded_outputs = []
        try:
            recorded_outputs += [
                item["entry"].get("review")
                for item in load_recorded_reviews()
                if isinstance(item.get("entry"), dict) and isinstance(item["entry"].get("review"), dict)
            ]
        except Exception:
            pass
        try:
            recorded_outputs += [
                item["entry"].get("output")
                for item in load_recorded_watchers()
                if isinstance(item.get("entry"), dict) and isinstance(item["entry"].get("output"), dict)
            ]
        except Exception:
            pass
        for output in recorded_outputs:
            for violation in laws_module.check_output(output):
                if violation["law"] in counts:
                    counts[violation["law"]] += 1
        repo_root = Path(__file__).resolve().parent.parent.parent
        process = []
        for law in registry["process_laws"]:
            check = law.get("check")
            if check == "checked at review":
                status = "checked at review"
            else:
                candidate = str(check or "").split("::")[0]
                status = "automated" if candidate and (repo_root / candidate).is_file() else "missing test"
            process.append(
                {
                    "id": law.get("id"),
                    "statement": law.get("statement"),
                    "stage": law.get("stage"),
                    "check": check,
                    "check_status": status,
                }
            )
        return jsonify(
            {
                "data_mode": "synthetic",
                "version": registry["version"],
                "model_laws": [
                    {
                        "id": law.get("id"),
                        "statement": law.get("statement"),
                        "origin": law.get("origin"),
                        "status": law.get("status"),
                        "check": law.get("check"),
                        "rejected_recorded": counts.get(law.get("id"), 0),
                    }
                    for law in registry["model_laws"]
                ],
                "process_laws": process,
            }
        )

    @app.get("/api/watcher")
    def watcher_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "data_mode": "synthetic", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "data_mode": "synthetic", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)
        result = public_watcher(scn, at)
        result.update({"data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "recorded_only": True})
        return jsonify(result)

    @app.get("/api/trace")
    def trace_endpoint():
        from aria_home.trace import build_trace

        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        result = build_trace(scn, at)
        result.update({"data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "recorded_only": True})
        return jsonify(result)

    @app.get("/api/corrections")
    def corrections_endpoint():
        try:
            records = load_correction_records()
        except Exception:
            records = []
        return jsonify({"data_mode": "synthetic", "corrections": records})

    @app.get("/api/sources")
    def sources():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)

        visible = visible_records(scn.records, at)
        has_room_sensor = any(r.source is SourceKind.room_sensor for r in scn.records)
        statuses = [
            source_status(source, visible, at, mode=scn.manifest.mode)
            for source in SourceKind
            if source is not SourceKind.room_sensor or has_room_sensor
        ]
        return jsonify(
            {
                "data_mode": scn.manifest.mode.value,
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "sources": [s.model_dump(mode="json") for s in statuses],
            }
        )

    @live_only_get("/api/provider")
    def provider():
        try:
            config = ProviderConfig.from_env(os.environ)
            selected = get_provider(config)
        except ValueError as exc:
            return jsonify({"error": str(exc), "scenario": scenario.manifest.id, "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(), "timezone": scenario.manifest.timezone}), 400
        missing = config.missing_settings() if config.enabled else None
        return jsonify(
            {
                "mode": selected.mode,
                "model_id": config.model_id,
                "enabled": config.enabled,
                "key_present": bool(config.api_key),
                "configured": config.configured,
                "config_error": missing or None,
                "scenario": scenario.manifest.id,
                "at": (scenario.manifest.start + timedelta(hours=3)).isoformat(),
                "timezone": scenario.manifest.timezone,
            }
        )

    @app.get("/api/metrics")
    def metrics():
        from datetime import datetime as _datetime

        def _jsonable(value):
            if isinstance(value, _datetime):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: _jsonable(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_jsonable(v) for v in value]
            return value

        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)

        start = at - timedelta(hours=3)
        ctx = context_as_of(scn, at)
        visible = visible_records(scn.records, at)
        zones = sorted({r.subject for r in eligible_records(visible, "indoor_temp", now=at, require_value=False)})
        zone = zones[0] if zones else "demo-house/main"
        trend = temperature_trend(visible, zone, start, at, at)
        gap = None
        if ctx.confirmation is not None:
            gap = target_gap(trend, ctx.confirmation.target_temp, ctx.confirmation.target_unit)
        circuit_ids = sorted(
            {
                (r.binding.circuit_id if r.binding else None) or r.subject
                for r in eligible_records(visible, "circuit_power", now=at, require_value=False)
            }
        )
        circuits = {cid: _jsonable(circuit_activity(visible, cid, start, at, at)) for cid in circuit_ids}
        statuses = [
            source_status(source, visible, at, mode=scn.manifest.mode)
            for source in SourceKind
        ]
        trip_payload = ctx.trip.model_dump(mode="json") if ctx.trip is not None else None
        confirmation_payload = ctx.confirmation.model_dump(mode="json") if ctx.confirmation is not None else None
        canonical_pack = build_evidence_pack(scn, at)
        readiness = canonical_pack.get("readiness") or canonical_pack.get("canonical_readiness")
        return jsonify(
            {
                "data_mode": scn.manifest.mode.value,
                "computed_by": "deterministic code",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "zone": zone,
                "window": {"start": start.isoformat(), "end": at.isoformat()},
                "indoor_trend": _jsonable(trend),
                "target_gap": _jsonable(gap),
                "circuits": circuits,
                "trip": trip_payload,
                "confirmation": confirmation_payload,
                "readiness_flags": dict(ctx.flags),
                "flags": dict(ctx.flags),
                "context_flags": dict(ctx.flags),
                "readiness": _jsonable(dict(readiness)),
                "computed_readiness": readiness["status"],
            }
        )

    @live_only_get("/api/power-context")
    def power_context_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)
        start = at - timedelta(hours=3)
        visible = visible_records(scn.records, at)
        result = power_context(visible, start, at, NOISE_FLOOR_W)
        payload = result.model_dump(mode="json")
        payload.update(
            {
                "data_mode": scn.manifest.mode.value,
                "computed_by": "deterministic code",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "timezone": scn.manifest.timezone,
                "window": {"start": start.isoformat(), "end": at.isoformat()},
            }
        )
        return jsonify(payload)

    @live_only_get("/api/live-power")
    def live_power_endpoint():
        try:
            payload = read_live_power()
        except Exception as exc:
            payload = {"status": "unavailable", "source": "live-read-only (owner's home)", "fetched_at": None, "circuits": [], "error": str(exc)[:200]}
        if not isinstance(payload, dict):
            payload = {"status": "unavailable", "source": "live-read-only (owner's home)", "fetched_at": None, "circuits": [], "error": "unavailable"}
        payload.setdefault("source", "live-read-only (owner's home)")
        return jsonify(payload)

    @app.get("/api/investigation")
    def investigation():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        raw_at = request.args.get("at")
        if raw_at:
            try:
                at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "at must be an ISO 8601 datetime", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            if at.tzinfo is None or at.utcoffset() is None:
                return jsonify({"error": "at must be timezone-aware", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
        else:
            at = scn.manifest.start + timedelta(hours=3)
        if public:
            provider = None
        else:
            try:
                provider = get_provider()
            except ValueError as exc:
                return jsonify({"error": str(exc), "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone}), 400
        pack = build_evidence_pack(scn, at)
        identity = inference_identity(scn, at, pack=pack, provider=provider)
        store = _get_store()
        row = store.get_inference(identity["identity_key"])
        readiness = pack.get("readiness") if isinstance(pack, dict) else None
        summary = {"source_statuses": pack.get("source_statuses", []), "metrics": pack.get("metrics", {}), "power_context": pack.get("power_context", {}), "power_context_statement": (pack.get("power_context") or {}).get("statement"), "continuity": (pack.get("power_context") or {}).get("continuity"), "readiness": readiness, "computed_readiness": readiness.get("status") if isinstance(readiness, dict) else None}
        base = {"data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "evaluated_at": at.isoformat(), "readiness": readiness, "computed_readiness": summary["computed_readiness"], "identity_key": identity["identity_key"], "investigation_id": identity["investigation_id"], "id": identity["investigation_id"]}
        if row is not None and row.get("state") in ("completed", "failed") and row.get("result") is not None:
            payload = dict(row["result"])
            payload.update(base)
            if public:
                stored = Investigation.model_validate(row["result"])
                stored_provenance = annotate_public_result(scn, at, stored)
                if stored_provenance:
                    payload["recorded_provenance"] = stored_provenance
                    review = _recorded_review_for_display(scn, at, pack)
                    if review is not None:
                        payload["recorded_review"] = review
            payload["deduplicated"] = True
            payload["inference_state"] = row["state"]
            stored_readiness = payload.get("evidence_pack", {}).get("readiness") if isinstance(payload.get("evidence_pack"), dict) else None
            if stored_readiness is not None:
                payload["readiness"] = stored_readiness
                payload["computed_readiness"] = stored_readiness.get("status") if isinstance(stored_readiness, dict) else None
            return jsonify(payload)
        if row is not None and row.get("state") == "pending":
            return jsonify({**base, "status": "pending", "investigation_status": "pending", "inference_state": "pending", "output": None, "reasons": ["inference is pending"], "model_id": None, "prompt_version": identity["prompt_version"], "provider_mode": None, "summary": summary, "evidence_pack": pack}), 202
        if row is not None and row.get("state") == "recovery_required":
            return jsonify({**base, "status": "recovery_required", "investigation_status": "recovery_required", "inference_state": "recovery_required", "output": None, "reasons": ["inference claim expired before completion; recovery requires an explicit POST with retry=true"], "model_id": None, "prompt_version": identity["prompt_version"], "provider_mode": None, "summary": summary, "evidence_pack": pack}), 409
        payload = {"status": "unavailable", "output": None, "reasons": ["no stored investigation for this scenario and time; create one with POST /api/investigations"], "model_id": None, "prompt_version": identity["prompt_version"], "provider_mode": None, "latency_ms": None, "input_tokens": None, "output_tokens": None, "token_usage": {"input_tokens": None, "output_tokens": None}, "max_tokens_used": None, "summary": summary, "evidence_pack": pack, "inference_state": "not_started"}
        payload.update(base)
        return jsonify(payload)

    _store = None
    _scenarios = {}

    def _get_store():
        nonlocal _store
        if public and has_request_context():
            session_path = getattr(g, "public_session_path", None)
            if session_path is not None:
                return Store(path=session_path)
        if _store is None:
            _store = Store()
        return _store

    def _load_named_scenario(name):
        import re

        scenario_name = name or "care_home_v1"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", scenario_name):
            return None
        if scenario_name not in _scenarios:
            if scenario_name == scenario.manifest.id:
                _scenarios[scenario_name] = scenario
            else:
                path = SCENARIO_PATH.parent / scenario_name
                if not (path / "manifest.json").is_file():
                    return None
                try:
                    _scenarios[scenario_name] = load_scenario(path)
                except (ValueError, TypeError, KeyError, OSError):
                    return None
        return _scenarios[scenario_name]

    def _parse_at(raw_at, default):
        if raw_at is None:
            return default, None
        if raw_at == "":
            return None, (jsonify({"error": "at must be an ISO 8601 datetime", "data_mode": "synthetic"}), 400)
        try:
            at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
        except ValueError:
            return None, (jsonify({"error": "at must be an ISO 8601 datetime", "data_mode": "synthetic"}), 400)
        if at.tzinfo is None or at.utcoffset() is None:
            return None, (jsonify({"error": "at must be timezone-aware", "data_mode": "synthetic"}), 400)
        return at, None

    def _notification_api(row):
        if row is None:
            return None
        item = {k: v for k, v in row.items() if k != "payload_json"}
        return item

    @app.get("/api/context")
    def context_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic", "scenario": request.args.get("scenario"), "at": request.args.get("at"), "timezone": scenario.manifest.timezone}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        ctx = context_as_of(scn, at)
        flags = dict(ctx.flags)
        base = {"data_mode": scn.manifest.mode.value, "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "flags": flags, "context_flags": dict(flags), "readiness_flags": dict(flags)}
        trip_payload = ctx.trip.model_dump(mode="json") if ctx.trip is not None else None
        if ctx.confirmation is None:
            if flags.get("trip_cancelled"):
                reason, reason_in_words = "trip_cancelled", "Trip cancelled"
            elif flags.get("confirmation_outdated"):
                reason, reason_in_words = "confirmation_outdated", "Confirmation outdated for the current trip"
            elif flags.get("trip_mismatched"):
                reason, reason_in_words = "trip_mismatched", "Trip and confirmation do not match"
            else:
                reason, reason_in_words = "trip_unconfirmed", "Not yet confirmed"
            return jsonify({**base, "confirmed": False, "reason": reason, "reason_in_words": reason_in_words, "confirmation": None, "confirmed_at": None, "revision_id": None, "current_trip_revision_id": ctx.trip.revision_id if ctx.trip is not None else None})
        confirmation = ctx.confirmation
        trip = ctx.trip
        arrival_plan = dict(getattr(scn, "arrival_plan", None) or {}) or None
        allowances = []
        if arrival_plan:
            if arrival_plan.get("airport_exit_baggage_allowance_min") is not None:
                allowances.append({"kind": "airport_exit_baggage", "minutes": arrival_plan["airport_exit_baggage_allowance_min"], "label": arrival_plan.get("airport_exit_baggage_label") or f"labeled allowance: {arrival_plan['airport_exit_baggage_allowance_min']} min airport-exit/baggage"})
            if arrival_plan.get("driving_allowance_min") is not None:
                allowances.append({"kind": "driving", "minutes": arrival_plan["driving_allowance_min"], "label": arrival_plan.get("driving_label") or f"labeled allowance: {arrival_plan['driving_allowance_min']} min driving"})
        revision_id = confirmation.revision_id or confirmation.trip_revision_id or (trip.revision_id if trip is not None else None)
        property_label = trip.property_id if trip is not None else confirmation.property_id
        return jsonify({**base, "confirmed": True, "reason": None, "property_label": property_label, "property_id": property_label, "property": property_label, "planned_arrival": trip.planned_arrival.isoformat() if trip is not None else None, "arrival_plan": arrival_plan, "landing": arrival_plan.get("landing") if arrival_plan else None, "allowances": allowances, "arrival_allowances": allowances, "arrival_estimates_note": "Arrival times and allowances are scenario estimates, not live travel claims", "estimates_note": "Scenario estimates, not live travel claims", "target_temp": confirmation.target_temp, "target_unit": confirmation.target_unit, "target_temperature": f"{confirmation.target_temp:g} {confirmation.target_unit}", "notify_homeowner": confirmation.notify_homeowner, "homeowner_notification_preference": confirmation.notify_homeowner, "homeowner_notification": confirmation.notify_homeowner, "manager_authorized": confirmation.manager_authorized, "manager_coordination_permission": confirmation.manager_authorized, "manager_coordination": "allowed" if confirmation.manager_authorized else "not allowed", "confirmed_at": confirmation.confirmed_at.isoformat(), "revision_id": revision_id, "trip_revision_id": revision_id, "confirmation_revision_id": revision_id, "trip_revision": confirmation.trip_revision, "trip": trip_payload, "confirmation": confirmation.model_dump(mode="json")})

    def _follow_up_payload(store, investigation_id, at=None, outcome=None):
        follow_up = store.get_follow_up(investigation_id)
        row = store.get_follow_up_row(investigation_id)
        if follow_up is None:
            return None
        payload = follow_up.model_dump(mode="json")
        if at is not None and outcome is not None:
            status = outcome.status.value if hasattr(outcome.status, "value") else outcome.status
            payload.update({"target": row["target"], "last_status": status, "status": status, "last_evaluated_at": at.isoformat() if hasattr(at, "isoformat") else str(at), "supporting_ids": list(outcome.supporting_ids), "next_check_at": row.get("next_check_at") or payload.get("next_check_at"), "when": row.get("next_check_at") or payload.get("next_check_at"), "schedule_status": row.get("schedule_status") or payload.get("schedule_status"), "deadline_passed": row.get("deadline_passed", payload.get("deadline_passed"))})
            return payload
        payload.update({"target": row["target"], "last_status": row["last_status"], "status": row["last_status"], "last_evaluated_at": row["last_evaluated_at"], "supporting_ids": row["supporting_ids"], "next_check_at": row.get("next_check_at") or payload.get("next_check_at"), "when": row.get("next_check_at") or payload.get("next_check_at"), "schedule_status": row.get("schedule_status") or payload.get("schedule_status"), "deadline_passed": row.get("deadline_passed", payload.get("deadline_passed"))})
        return payload

    @app.post("/api/investigations")
    def create_investigation():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        if public:
            provider = None
        else:
            try:
                provider = get_provider()
            except ValueError as exc:
                return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        pack = build_evidence_pack(scn, at)
        identity = inference_identity(scn, at, pack=pack, provider=provider)
        investigation_id = identity["investigation_id"]
        store = _get_store()
        retry = str(request.args.get("retry") or "").lower() in ("1", "true", "yes")
        test_delay_s = 0.0
        test_fail = False
        lease_override = None
        if not public and os.environ.get("ARIA_HOME_E2E_HOOKS") == "1" and os.environ.get("ARIA_HOME_MODEL_ENABLED") != "1":
            try:
                test_delay_s = min(max(float(request.args.get("test_delay_s") or 0), 0.0), 30.0)
            except (TypeError, ValueError):
                test_delay_s = 0.0
            test_fail = str(request.args.get("test_fail") or "").lower() in ("1", "true", "yes")
            try:
                lease_raw = request.args.get("lease_s")
                lease_override = min(max(int(float(lease_raw)), 1), 600) if lease_raw else None
            except (TypeError, ValueError):
                lease_override = None
        claim_kwargs = {"lease_seconds": lease_override} if lease_override else {}
        claimed, claim_row = store.claim_inference(identity, retry=retry, **claim_kwargs)
        deduplicated = False
        owner_id = claim_row.get("owner_id") if claim_row else None
        if not claimed:
            if claim_row is not None and claim_row.get("state") == "recovery_required":
                return jsonify({"data_mode": "synthetic", "status": "recovery_required", "investigation_status": "recovery_required", "inference_state": "recovery_required", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity": identity, "identity_key": identity["identity_key"], "error": "inference recovery required; repeat with retry=true to explicitly re-run", "deduplicated": False}), 409
            if claim_row is None or claim_row["state"] == "pending":
                return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity": identity, "identity_key": identity["identity_key"]}), 202
            if claim_row["result"] is None:
                return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity_key": identity["identity_key"]}), 202
            result = Investigation.model_validate(claim_row["result"])
            deduplicated = True
        else:
            if public:
                result, _ = public_investigation(scn, at)
            else:
                if test_delay_s:
                    time.sleep(test_delay_s)
                try:
                    if test_fail:
                        result = Investigation(status="unavailable", reasons=["provider error: test_fail"], prompt_version=identity["prompt_version"], evidence_pack=pack)
                    else:
                        result = investigate(scn, at, provider)
                except Exception as exc:
                    result = Investigation(status="unavailable", reasons=[f"provider error: {exc}"], prompt_version=identity["prompt_version"], evidence_pack=pack)
            completion = store.complete_inference(identity["identity_key"], result.model_dump(mode="json"), "completed" if result.status == "ok" else "failed", owner_id=owner_id)
            if completion is not None and not completion.get("completion_accepted", True):
                if completion.get("state") == "pending":
                    return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity": identity, "identity_key": identity["identity_key"]}), 202
                if completion.get("state") == "recovery_required":
                    return jsonify({"data_mode": "synthetic", "status": "recovery_required", "investigation_status": "recovery_required", "inference_state": "recovery_required", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity": identity, "identity_key": identity["identity_key"], "error": "inference recovery required; repeat with retry=true to explicitly re-run", "deduplicated": False}), 409
                if completion.get("result") is not None:
                    result = Investigation.model_validate(completion["result"])
                    deduplicated = True
                else:
                    return jsonify({"data_mode": "synthetic", "status": "pending", "investigation_status": "pending", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "identity_key": identity["identity_key"]}), 202
        public_provenance = annotate_public_result(scn, at, result) if public else None
        recorded_review = _recorded_review_for_display(scn, at, pack) if public and public_provenance else None
        store.save_investigation(result, investigation_id=investigation_id, scenario=scn.manifest.id, evaluated_at=at)
        _inference_row = store.get_inference(identity["identity_key"]) or {}
        identity_extra = {"provider": identity.get("provider"), "provider_identity": identity.get("provider"), "identity_version": identity.get("identity_version"), "attempts": _inference_row.get("attempts"), "attempt_history": _inference_row.get("attempt_history", [])}
        _readiness_for_notif = result.evidence_pack.get("readiness") if result.evidence_pack else None
        notif_rows = [_notification_api(r) for r in create_investigation_notifications(store, scn, investigation_id, result, _readiness_for_notif, at)]
        ctx = context_as_of(scn, at)
        arrival = ctx.trip.planned_arrival if ctx.trip else None
        cadence_s = next((r.expected_cadence_s for r in scn.records if r.quantity == "indoor_temp" and r.expected_cadence_s is not None), None)
        model_when = None
        if result.output and result.output.follow_up:
            model_when = result.output.follow_up.next_check_at or result.output.follow_up.when
        schedule = compute_follow_up_schedule(at, arrival=arrival, cadence_s=cadence_s, model_when=model_when)
        schedule_payload = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in schedule.items()}
        investigation_payload = result.model_dump(mode="json")
        readiness = result.evidence_pack.get("readiness") if result.evidence_pack else None
        computed_readiness = readiness.get("status") if isinstance(readiness, dict) else None
        investigation_payload.update({"id": investigation_id, "investigation_id": investigation_id, "scenario": scn.manifest.id, "evaluated_at": at.isoformat(), "readiness": readiness, "computed_readiness": computed_readiness, **({"recorded_provenance": public_provenance} if public_provenance else {}), **({"recorded_review": recorded_review} if recorded_review else {})})
        if schedule["deadline_passed"]:
            return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"], **identity_extra})
        anchor = _follow_up_anchor(scn, at)
        try:
            try:
                follow_up = follow_up_for(scn, investigation_id, anchor, cadence_s=cadence_s)
            except ValueError:
                if anchor == at:
                    raise
                follow_up = follow_up_for(scn, investigation_id, at, cadence_s=cadence_s)
        except ValueError as exc:
            if "deadline_passed" in str(exc):
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "deadline_passed", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": "deadline_passed", "flag": "deadline_passed", "deadline_passed": True, "next_check_at": None, "outcome": None, "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"], **identity_extra})
            if any(token in str(exc) for token in ("trip_cancelled", "trip_unconfirmed", "trip_mismatched", "confirmation_outdated", "no homeowner confirmation", "no trip visible")):
                primary = next((name for name in ("trip_cancelled", "confirmation_outdated", "trip_mismatched", "trip_unconfirmed") if ctx.flags.get(name)), "trip_unconfirmed")
                not_scheduled = {**schedule_payload, "status": "not_scheduled", "schedule_status": "not_scheduled", "next_check_at": None, "when": None}
                return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": "cannot_tell", "investigation_status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": None, "follow_up_schedule": not_scheduled, "schedule": not_scheduled, "schedule_status": "not_scheduled", "flag": primary, "flags": dict(ctx.flags), "readiness_flags": dict(ctx.flags), "context_flags": dict(ctx.flags), "deadline_passed": False, "next_check_at": None, "outcome": None, "error": str(exc), "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"], **identity_extra})
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        if follow_up.next_check_at is None or follow_up.next_check_at.tzinfo is None or follow_up.next_check_at <= follow_up.created_at:
            return jsonify({"error": "invalid follow-up schedule", "data_mode": "synthetic"}), 400
        try:
            outcome = evaluate_outcome(follow_up, scn.records, at)
            store.save_follow_up(follow_up, outcome=outcome)
        except ValueError as exc:
            return jsonify({"error": str(exc), "data_mode": "synthetic"}), 400
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "id": investigation_id, "scenario": scn.manifest.id, "status": result.status, "readiness": readiness, "computed_readiness": computed_readiness, "investigation": investigation_payload, "follow_up": _follow_up_payload(store, investigation_id), "follow_up_schedule": schedule_payload, "schedule": schedule_payload, "schedule_status": schedule["status"], "deadline_passed": False, "next_check_at": schedule_payload["next_check_at"], "outcome": outcome.model_dump(mode="json"), "notifications": notif_rows, "deduplicated": deduplicated, "identity_key": identity["identity_key"], "input_revision": identity["input_revision"], **identity_extra})

    if not public and os.environ.get("ARIA_HOME_E2E_HOOKS") == "1" and os.environ.get("ARIA_HOME_MODEL_ENABLED") != "1":
        @app.post("/api/e2e/reset")
        def e2e_reset_endpoint():
            _get_store().reset_e2e()
            return jsonify({"data_mode": "synthetic", "status": "ok", "reset": True})

    @app.get("/api/events")
    def events_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        return jsonify(
            {
                "data_mode": "synthetic",
                "scenario": scn.manifest.id,
                "at": at.isoformat(),
                "events": [event.model_dump(mode="json") for event in events_as_of(scn, at)],
            }
        )

    @app.get("/api/visual")
    def visual_endpoint():
        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        visual = visual_as_of(scn, at)
        if visual is None:
            return jsonify({"data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "visual": None})
        mode = "recorded"
        payload = dict(visual)
        payload["provider_mode"] = "recorded"
        payload["caption"] = f"Synthetic camera frame ({visual.get('generator')}) - segmentation by {visual.get('model')} ({mode})"
        payload["image_url"] = "/api/visual/image?" + urlencode({"scenario": scn.manifest.id, "at": at.isoformat()})
        return jsonify({"data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "visual": payload})

    @app.get("/api/visual/image")
    def visual_image_endpoint():
        from aria_home.visual import FIXTURES_DIR

        scn = _load_named_scenario(request.args.get("scenario"))
        if scn is None:
            return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), scn.manifest.start + timedelta(hours=3))
        if error:
            return error
        visual = visual_as_of(scn, at)
        if not isinstance(visual, dict):
            return jsonify({"error": "no visual evidence for this scenario", "data_mode": "synthetic"}), 404
        filename = str(visual.get("file") or "")
        if not filename.endswith(".webp") or Path(filename).is_absolute() or ".." in Path(filename).parts:
            return jsonify({"error": "no visual image for this scenario", "data_mode": "synthetic"}), 404
        base = FIXTURES_DIR.resolve()
        path = (base / filename).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            return jsonify({"error": "no visual image for this scenario", "data_mode": "synthetic"}), 404
        if path.suffix != ".webp" or not path.is_file():
            return jsonify({"error": "no visual image for this scenario", "data_mode": "synthetic"}), 404
        return send_file(path, mimetype="image/webp")

    def _caregiver_alert_row(rows):
        return next((r for r in rows if r.get("audience") == "family_caregiver" and r.get("kind") == "caregiver_alert" and r.get("state") == "simulated_delivered"), None)

    def _caregiver_permission_payload(store, scn, investigation_id, rows, at):
        alert = _caregiver_alert_row(rows)
        if alert is None:
            return None
        decision = store.get_caregiver_decision(investigation_id, at=at)
        source = "in-app decision" if decision else None
        if decision is None:
            scripted = next((e for e in events_as_of(scn, at) if e.kind == "caregiver_hvac_authorized"), None)
            if scripted is not None:
                decision = {"decision": "approved", "decided_at": scripted.available_at.isoformat(), "actor": "family_caregiver"}
                source = "scenario event (the recorded story)"
        created_at = datetime.fromisoformat(str(alert["created_at"]).replace("Z", "+00:00"))
        return {
            "notification_id": alert["id"],
            "text": caregiver_permission_text(scn, created_at),
            "requested_at": alert["created_at"],
            "status": decision["decision"] if decision else "waiting",
            "decided_at": decision["decided_at"] if decision else None,
            "actor": decision["actor"] if decision else None,
            "source": source,
            "note": "Approval only lets ARIA contact the HVAC company; it never changes readiness or verification.",
        }

    @app.get("/api/follow-ups/<investigation_id>")
    def get_follow_up_endpoint(investigation_id):
        store = _get_store()
        follow_up = store.get_follow_up(investigation_id)
        if follow_up is None:
            return jsonify({"error": "follow-up not found", "data_mode": "synthetic"}), 404
        at, error = _parse_at(request.args.get("at"), follow_up.deadline)
        if error:
            return error
        if at < follow_up.created_at:
            return jsonify({"error": "investigation not yet created at this time", "data_mode": "synthetic"}), 409
        investigation_row = store.get_investigation(investigation_id)
        scenario_name = investigation_row["scenario"] if investigation_row else "care_home_v1"
        scn = _load_named_scenario(scenario_name) or scenario
        if public and request.args.get("at") is not None and not public_demo.checkpoint_ok(at, scn.manifest.id):
            return jsonify({"error": "at is not an allowlisted replay time for this scenario", "data_mode": "synthetic", "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone}), 400
        row_before = store.get_follow_up_row(investigation_id)
        latest_before = None
        if row_before and row_before.get("last_evaluated_at"):
            latest_before = datetime.fromisoformat(str(row_before["last_evaluated_at"]).replace("Z", "+00:00"))
        is_rewind = latest_before is not None and at < latest_before
        outcome = evaluate_outcome(follow_up, scn.records, at)
        if not is_rewind:
            store.record_outcome(investigation_id, outcome)
        outcome_payload = outcome.model_dump(mode="json")
        payload = {"data_mode": "synthetic", "investigation_id": investigation_id, "scenario": scn.manifest.id, "at": at.isoformat(), "timezone": scn.manifest.timezone, "status": outcome.status.value, "outcome": outcome_payload, "follow_up": _follow_up_payload(store, investigation_id, at=at, outcome=outcome), "supporting_ids": outcome.supporting_ids, "history": store.list_outcomes(investigation_id, at=at)}
        verification = None
        if any(r.source is SourceKind.room_sensor for r in scn.records):
            verification = verify_recovery(scn, follow_up, at)
            latest = verification.get("latest_reading_used")
            latest_payload = None
            if isinstance(latest, dict):
                latest_payload = {
                    "id": latest.get("id"),
                    "observed_at": latest["observed_at"].isoformat() if hasattr(latest.get("observed_at"), "isoformat") else latest.get("observed_at"),
                    "received_at": latest["received_at"].isoformat() if hasattr(latest.get("received_at"), "isoformat") else latest.get("received_at"),
                }
            payload["verification"] = {**verification, "evaluated_at": verification["evaluated_at"].isoformat(), "goal_verified_at": verification["goal_verified_at"].isoformat() if verification.get("goal_verified_at") else None, "arrival_met_at": verification["arrival_met_at"].isoformat() if verification.get("arrival_met_at") else None, "latest_reading_used": latest_payload}
            history_rows = payload["history"]
            verification_history = []
            for entry in history_rows:
                try:
                    entry_at = datetime.fromisoformat(str(entry["evaluated_at"]).replace("Z", "+00:00"))
                except ValueError:
                    continue
                entry_verification = verify_recovery(scn, follow_up, entry_at)
                verification_history.append({"evaluated_at": entry["evaluated_at"], "stage": entry_verification["stage"], "sample_count": entry.get("sample_count")})
            payload["verification_history"] = verification_history
        timeline = build_evidence_timeline(scn, follow_up, at) if any(r.source is SourceKind.room_sensor for r in scn.records) else []
        human_report = _human_report_for_display(scn, at)
        if human_report is not None:
            timeline = [*timeline, human_report["timeline_entry"]]
            timeline.sort(key=lambda e: (e["first_known_at"], e["observed_at"], e["kind"]))
        payload["evidence_timeline"] = [
            {
                **entry,
                "observed_at": entry["observed_at"].isoformat() if hasattr(entry["observed_at"], "isoformat") else entry["observed_at"],
                "received_at": entry["received_at"].isoformat() if hasattr(entry["received_at"], "isoformat") else entry["received_at"],
                "available_at": entry["available_at"].isoformat() if hasattr(entry["available_at"], "isoformat") else entry["available_at"],
                "first_known_at": entry["first_known_at"].isoformat() if hasattr(entry["first_known_at"], "isoformat") else entry["first_known_at"],
                "evaluated_at": entry["evaluated_at"].isoformat() if hasattr(entry["evaluated_at"], "isoformat") else entry["evaluated_at"],
            }
            for entry in timeline
        ]
        if scn.manifest.id in ("demo_video_v1", "care_home_v1") and not is_rewind:
            stored_output = investigation_row["output"] if investigation_row else None
            pseudo = {"output": stored_output} if stored_output else None
            readiness_for_hvac = {"status": "cannot_tell", "reasons": list(verification["reasons"]) if verification else []}
            caregiver_decision = store.get_caregiver_decision(investigation_id, at=at)
            hvac_row = create_hvac_notification(store, scn, investigation_id, pseudo, readiness_for_hvac, at, verification=verification, caregiver_decision=caregiver_decision)
            if scn.manifest.id == "care_home_v1":
                create_caregiver_updates(store, scn, investigation_id, hvac_row, verification, at)
        payload["notifications"] = [_notification_api(r) for r in store.list_notifications(investigation_id, at=at)]
        if scn.manifest.id == "care_home_v1":
            payload["caregiver_permission"] = _caregiver_permission_payload(store, scn, investigation_id, payload["notifications"], at)
        if human_report is not None:
            payload["human_report"] = human_report["payload"]
        return jsonify(payload)

    @app.get("/api/notifications")
    def list_notifications_endpoint():
        store = _get_store()
        investigation_id = request.args.get("investigation_id")
        raw_at = request.args.get("at")
        if raw_at:
            at, error = _parse_at(raw_at, None)
            if error:
                return error
            if investigation_id:
                follow_up = store.get_follow_up(investigation_id)
                created_at = follow_up.created_at if follow_up is not None else None
                if created_at is None:
                    inv_row = store.get_investigation(investigation_id)
                    if inv_row and inv_row.get("created_at"):
                        created_at = datetime.fromisoformat(str(inv_row["created_at"]).replace("Z", "+00:00"))
                if created_at is not None and at < created_at:
                    return jsonify({"error": "investigation not yet created at this time", "data_mode": "synthetic"}), 409
            if public:
                notif_scenario = None
                if investigation_id:
                    inv_row = store.get_investigation(investigation_id)
                    if inv_row:
                        notif_scenario = inv_row.get("scenario")
                if not public_demo.checkpoint_ok(at, notif_scenario):
                    return jsonify({"error": "at is not an allowlisted replay time", "data_mode": "synthetic", "at": at.isoformat()}), 400
            rows = store.list_notifications(investigation_id, at=at)
            return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "at": at.isoformat(), "notifications": [_notification_api(r) for r in rows]})
        rows = store.list_notifications(investigation_id)
        return jsonify({"data_mode": "synthetic", "investigation_id": investigation_id, "notifications": [_notification_api(r) for r in rows]})

    CAMERA_PHRASES = ("frost", "water puddle", "indicator light")
    CAMERA_UPLOAD_DISCLOSURE = "this real image was uploaded to Meta's sam-3.1"
    CAMERA_NOT_EVIDENCE = "live camera (owner's mechanical room): shown for the owner only, never evidence for the synthetic scenario's readiness or verification"

    def _segment_camera_frame(frame_path):
        from aria_home.visual import MODEL_API_KEY_ENV, SAM_BASE_URL, SAM_MODEL_ID, SamLiveProvider, VisualConfig, extract_sam_text, parse_sam_text

        api_key = (os.environ.get(MODEL_API_KEY_ENV) or "").strip()
        if not api_key:
            return {"status": "not_configured", "reason": f"{MODEL_API_KEY_ENV} is not set; nothing was uploaded"}
        provider = SamLiveProvider(VisualConfig(base_url=SAM_BASE_URL, model_id=SAM_MODEL_ID, api_key=api_key, enabled=True))
        image = Path(frame_path).read_bytes()
        results = []
        for phrase in CAMERA_PHRASES:
            try:
                data = provider.segment(image, phrase, mime="image/jpeg")
            except Exception as exc:
                results.append({"phrase": phrase, "status": "failed", "error": str(exc).replace(api_key, "[redacted]")[:200]})
                continue
            boxes = parse_sam_text(extract_sam_text(data))
            results.append({"phrase": phrase, "status": "ok", "count": len(boxes), "note": "no detection is not an all-clear" if not boxes else None})
        return {"status": "uploaded", "disclosure": CAMERA_UPLOAD_DISCLOSURE, "model": SAM_MODEL_ID, "results": results}

    @live_only_get("/api/camera/status")
    def camera_status_endpoint():
        return jsonify({"data_mode": "synthetic", "configured": bool(nest_camera.nest_config_from_env()["configured"])})

    @live_only_post("/api/camera/snapshot")
    def camera_snapshot_endpoint():
        body = request.get_json(force=False, silent=True)
        body = body if isinstance(body, dict) else {}
        if not nest_camera.nest_config_from_env()["configured"]:
            return jsonify({"error": "Nest camera snapshot is not configured", "reason": "not_configured", "data_mode": "synthetic"}), 409
        result = nest_camera.capture_snapshot()
        frame_path = result.pop("frame_path", None)
        payload = {"data_mode": "synthetic", "camera": result, "note": CAMERA_NOT_EVIDENCE, "image_url": None, "segmentation": None}
        if result.get("status") == "ok" and frame_path:
            payload["image_url"] = f"/api/camera/snapshot/{Path(frame_path).name}"
            if body.get("segment") is True:
                payload["segmentation"] = _segment_camera_frame(frame_path)
        return jsonify(payload)

    @live_only_get("/api/camera/snapshot/<name>")
    def camera_snapshot_image(name):
        import re as _re

        if not _re.fullmatch(r"nest-\d{8}T\d{6}Z\.jpg", name):
            return jsonify({"error": "not found", "data_mode": "synthetic"}), 404
        path = nest_camera.SNAPSHOT_DIR / name
        if not path.is_file():
            return jsonify({"error": "not found", "data_mode": "synthetic"}), 404
        return send_file(path, mimetype="image/jpeg", max_age=0)

    @live_only_get("/api/whatsapp/status")
    def whatsapp_status_endpoint():
        config = whatsapp_config_from_env()
        return jsonify({"data_mode": "synthetic", "configured": bool(config["configured"])})

    @live_only_post("/api/notifications/<notification_id>/whatsapp")
    def send_notification_whatsapp_endpoint(notification_id):
        store = _get_store()
        existing = store.get_notification(notification_id)
        if existing is None:
            return jsonify({"error": "notification not found", "data_mode": "synthetic"}), 404
        is_permission = existing.get("audience") == "family_caregiver" and existing.get("kind") == "caregiver_alert"
        if existing.get("audience") != "hvac_company" and not is_permission:
            return jsonify({"error": "only the hvac_company notice and the caregiver permission request can be sent via WhatsApp", "reason": "wrong_audience", "data_mode": "synthetic"}), 409
        raw_at = request.args.get("at")
        if raw_at is None:
            try:
                body = request.get_json(force=False, silent=True)
            except Exception:
                body = None
            if isinstance(body, dict) and isinstance(body.get("at"), str):
                raw_at = body.get("at")
        if raw_at is not None:
            at, error = _parse_at(raw_at, None)
            if error:
                return error
            try:
                created_dt = datetime.fromisoformat(str(existing.get("created_at")).replace("Z", "+00:00"))
            except ValueError:
                created_dt = None
            if created_dt is not None and at < created_dt:
                return jsonify({"error": "notification not yet visible at this time", "reason": "not_yet_visible", "data_mode": "synthetic"}), 409
        config = whatsapp_config_from_env()
        if not config["configured"]:
            return jsonify({"error": "WhatsApp live delivery is not configured", "reason": "not_configured", "data_mode": "synthetic"}), 409
        try:
            if is_permission:
                inv_row = store.get_investigation(existing["investigation_id"])
                perm_scn = _load_named_scenario(inv_row["scenario"] if inv_row else None) or scenario
                created_dt = datetime.fromisoformat(str(existing["created_at"]).replace("Z", "+00:00"))
                result = attempt_caregiver_permission_whatsapp(store, existing, caregiver_permission_text(perm_scn, created_dt))
            else:
                result = attempt_hvac_whatsapp_delivery(store, existing)
        except Exception as exc:
            return jsonify({"error": f"delivery failed: {exc}"[:200], "data_mode": "synthetic"}), 500
        updated = store.get_notification(notification_id)
        payload = {"data_mode": "synthetic", "notification": _notification_api(updated), "whatsapp": (updated or {}).get("whatsapp"), "delivery": result}
        return jsonify(payload)

    @app.post("/api/notifications/<notification_id>/caregiver-decision")
    def caregiver_decision_endpoint(notification_id):
        body = request.get_json(force=False, silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "request body must be a JSON object", "data_mode": "synthetic"}), 400
        choice = {"approve": "approved", "decline": "declined"}.get(body.get("decision"))
        if choice is None:
            return jsonify({"error": "decision must be 'approve' or 'decline'", "data_mode": "synthetic"}), 400
        raw_at = body.get("at")
        if not isinstance(raw_at, str) or not raw_at.strip():
            return jsonify({"error": "at must be a non-empty ISO 8601 datetime string", "data_mode": "synthetic"}), 400
        at, error = _parse_at(raw_at, None)
        if error:
            return error
        store = _get_store()
        existing = store.get_notification(notification_id)
        if existing is None:
            return jsonify({"error": "notification not found", "data_mode": "synthetic"}), 404
        if existing.get("audience") != "family_caregiver" or existing.get("kind") != "caregiver_alert" or existing.get("state") != "simulated_delivered":
            return jsonify({"error": "only a delivered caregiver permission request can be approved or declined", "reason": "not_permission_request", "data_mode": "synthetic"}), 409
        created_dt = datetime.fromisoformat(str(existing["created_at"]).replace("Z", "+00:00"))
        if at < created_dt:
            return jsonify({"error": "the request is not yet visible at this time", "reason": "not_yet_visible", "data_mode": "synthetic"}), 409
        inv_row = store.get_investigation(existing["investigation_id"])
        dec_scn = _load_named_scenario(inv_row["scenario"] if inv_row else None) or scenario
        if public and not public_demo.checkpoint_ok(at, dec_scn.manifest.id):
            return jsonify({"error": "at is not an allowlisted replay time for this scenario", "data_mode": "synthetic", "scenario": dec_scn.manifest.id, "at": at.isoformat(), "timezone": dec_scn.manifest.timezone}), 400
        row, created = store.record_caregiver_decision(existing["investigation_id"], notification_id, choice, "family_caregiver", at)
        permission = _caregiver_permission_payload(store, dec_scn, existing["investigation_id"], store.list_notifications(existing["investigation_id"], at=at), at)
        return jsonify({"data_mode": "synthetic", "scenario": dec_scn.manifest.id, "at": at.isoformat(), "timezone": dec_scn.manifest.timezone, "recorded": created, "decision": row, "caregiver_permission": permission}), (201 if created else 200)

    @app.post("/api/notifications/<notification_id>/ack")
    def ack_notification_endpoint(notification_id):
        raw_body = request.get_data(cache=True)
        if raw_body:
            try:
                body = request.get_json(force=False)
            except Exception:
                return jsonify({"error": "request body must be a JSON object", "data_mode": "synthetic"}), 400
        else:
            body = {}
        if not isinstance(body, dict):
            return jsonify({"error": "request body must be a JSON object", "data_mode": "synthetic"}), 400
        store = _get_store()
        existing = store.get_notification(notification_id)
        if existing is None:
            return jsonify({"error": "notification not found", "data_mode": "synthetic"}), 404
        if existing.get("state") != "simulated_delivered":
            return jsonify({"error": f"notification in state {existing.get('state')} cannot be acknowledged; only simulated_delivered notifications can be acknowledged", "data_mode": "synthetic"}), 409
        actor = body.get("actor", body.get("by"))
        if not isinstance(actor, str) or not actor.strip():
            return jsonify({"error": "actor must be a non-empty string", "data_mode": "synthetic"}), 400
        actor = actor.strip()
        allowed_actors = {"homeowner": {"homeowner"}, "property_manager": {"property_manager"}, "family_caregiver": {"family_caregiver"}, "hvac_company": {"hvac_company"}}
        allowed = allowed_actors.get(existing.get("audience"), set())
        if actor not in allowed:
            return jsonify({"error": f"actor {actor!r} is not allowed to acknowledge a {existing.get('audience')} notification", "data_mode": "synthetic"}), 403
        if "at" in body:
            raw_at = body["at"]
            at_given = True
        elif "acknowledged_at" in body:
            raw_at = body["acknowledged_at"]
            at_given = True
        else:
            raw_at = request.args.get("at")
            at_given = raw_at is not None
        if not at_given:
            from datetime import timezone as _tz
            at = datetime.now(_tz.utc)
        else:
            if not isinstance(raw_at, str) or not raw_at.strip():
                return jsonify({"error": "at must be a non-empty ISO 8601 datetime string", "data_mode": "synthetic"}), 400
            at, error = _parse_at(raw_at, None)
            if error:
                return error
        created_at = existing.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            except ValueError:
                created_dt = None
            if created_dt is not None and at < created_dt:
                return jsonify({"error": "acknowledgement time must not be earlier than the notification creation time", "data_mode": "synthetic"}), 400
        ack = store.record_ack(notification_id, actor, at)
        if ack is None:
            return jsonify({"error": "notification not found", "data_mode": "synthetic"}), 404
        updated = store.get_notification(notification_id)
        inv_row = store.get_investigation(updated["investigation_id"]) if updated else None
        ack_scenario = inv_row["scenario"] if inv_row else scenario.manifest.id
        ack_scn = _load_named_scenario(ack_scenario) or scenario
        if public and at_given and not public_demo.checkpoint_ok(at, ack_scn.manifest.id):
            return jsonify({"error": "at is not an allowlisted replay time for this scenario", "data_mode": "synthetic", "scenario": ack_scn.manifest.id, "at": at.isoformat(), "timezone": ack_scn.manifest.timezone}), 400
        return jsonify({"data_mode": "synthetic", "scenario": ack_scn.manifest.id, "at": at.isoformat(), "timezone": ack_scn.manifest.timezone, "message": "acknowledged, not resolved", "acknowledgement": "acknowledged, not resolved", "notification": _notification_api(updated), "ack": ack, "acks": updated["acks"] if updated else []})

    DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    _SCOPED_AT_PATHS = ("/api/sources", "/api/context", "/api/metrics", "/api/investigation", "/api/investigations", "/api/events", "/api/visual", "/api/visual/image", "/api/watcher", "/api/trace")

    if public:

        @app.before_request
        def _public_guard():
            import json as _json

            if request.content_length and request.content_length > public_demo.MAX_BODY_BYTES:
                return jsonify({"error": "request body too large", "data_mode": "synthetic"}), 413
            if request.method in ("POST", "PUT", "PATCH"):
                body = request.get_data(cache=True)
                if len(body) > public_demo.MAX_BODY_BYTES:
                    return jsonify({"error": "request body too large", "data_mode": "synthetic"}), 413
                if body:
                    if request.mimetype != "application/json":
                        return jsonify({"error": "request body must be JSON", "data_mode": "synthetic"}), 415
                    try:
                        _json.loads(body)
                    except ValueError:
                        return jsonify({"error": "request body must be valid JSON", "data_mode": "synthetic"}), 400
            if request.path == "/api/health":
                return None
            session_id = request.cookies.get(public_demo.SESSION_COOKIE)
            if not public_demo.valid_session_id(session_id):
                session_id = public_demo.new_session_id()
                g.public_session_new = True
                public_demo.sweep_sessions(public_demo.sessions_dir())
            g.public_session_id = session_id
            g.public_session_path = public_demo.session_db_path(public_demo.sessions_dir(), session_id)
            public_demo.touch_session(g.public_session_path)
            raw_at = request.args.get("at")
            if request.path.startswith("/api/"):
                named = request.args.get("scenario")
                if named is not None and named not in public_demo.SCENARIOS:
                    return jsonify({"error": "unknown scenario", "data_mode": "synthetic"}), 404
            if request.path in _SCOPED_AT_PATHS and raw_at is not None:
                scn = _load_named_scenario(request.args.get("scenario"))
                if scn is not None:
                    try:
                        at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
                    except ValueError:
                        at = None
                    if at is not None and (at.tzinfo is None or at.utcoffset() is None):
                        at = None
                    if at is not None and not public_demo.checkpoint_ok(at, scn.manifest.id):
                        return jsonify({"error": "at is not an allowlisted replay time for this scenario", "data_mode": "synthetic", "scenario": scn.manifest.id, "at": raw_at, "timezone": scn.manifest.timezone}), 400
            return None

        @app.after_request
        def _public_session_cookie(response):
            if getattr(g, "public_session_new", False) and request.path != "/api/health":
                secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "") == "https"
                response.set_cookie(public_demo.SESSION_COOKIE, g.public_session_id, httponly=True, samesite="Lax", secure=secure, path="/")
            return response

        def _public_error(message, code):
            return jsonify({"error": message, "data_mode": "synthetic"}), code

        @app.errorhandler(400)
        def _public_400(exc):
            return _public_error("bad request", 400)

        @app.errorhandler(404)
        def _public_404(exc):
            return _public_error("not found", 404)

        @app.errorhandler(405)
        def _public_405(exc):
            return _public_error("method not allowed", 405)

        @app.errorhandler(413)
        def _public_413(exc):
            return _public_error("request body too large", 413)

        @app.errorhandler(415)
        def _public_415(exc):
            return _public_error("request body must be JSON", 415)

        @app.errorhandler(500)
        def _public_500(exc):
            return _public_error("internal error", 500)

        @app.get("/api/scenarios")
        def scenarios_endpoint():
            items = []
            for item in public_demo.scenario_list():
                scn = _load_named_scenario(item["id"])
                items.append({**item, "timezone": scn.manifest.timezone if scn else "America/New_York"})
            return jsonify({"data_mode": "synthetic", "scenarios": items})

        @app.post("/api/session/reset")
        def session_reset_endpoint():
            public_demo.destroy_session(g.public_session_path)
            return jsonify({"data_mode": "synthetic", "status": "ok", "reset": True})

        def _serve_dist(filename):
            if filename == "api" or (filename and filename.startswith("api/")):
                return jsonify({"error": "not found", "data_mode": "synthetic"}), 404
            index = DIST_DIR / "index.html"
            if filename:
                try:
                    resolved = (DIST_DIR / filename).resolve()
                except OSError:
                    resolved = None
                if resolved is not None and DIST_DIR.resolve() in resolved.parents and resolved.is_file():
                    return send_file(resolved)
            if index.is_file():
                return send_file(index)
            return jsonify({"error": "frontend not built", "data_mode": "synthetic"}), 404

        @app.get("/")
        def public_index():
            return _serve_dist(None)

        @app.get("/<path:filename>")
        def public_static(filename):
            return _serve_dist(filename)

        @app.route("/api/<path:_unmatched>", methods=["POST", "PUT", "PATCH", "DELETE"])
        def public_api_unmatched(_unmatched):
            return jsonify({"error": "not found", "data_mode": "synthetic"}), 404

    @app.after_request
    def _echo_context(response):
        if not request.path.startswith("/api/") or not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        scn = _load_named_scenario(request.args.get("scenario")) or scenario
        if request.path.startswith("/api/follow-ups/") and payload.get("scenario"):
            scn = _load_named_scenario(payload.get("scenario")) or scn
        changed = False
        if "scenario" not in payload or payload.get("scenario") is None:
            payload["scenario"] = scn.manifest.id
            changed = True
        if "timezone" not in payload or payload.get("timezone") is None:
            payload["timezone"] = scn.manifest.timezone
            changed = True
        if "at" not in payload or payload.get("at") is None:
            raw_at = request.args.get("at")
            at_value = None
            if raw_at:
                try:
                    parsed = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
                    at_value = parsed.isoformat() if parsed.tzinfo else raw_at
                except ValueError:
                    at_value = raw_at
            else:
                at_value = (scn.manifest.start + timedelta(hours=3)).isoformat()
            payload["at"] = at_value
            changed = True
        if changed:
            import json as _json

            response.set_data(_json.dumps(payload))
        return response

    return app
