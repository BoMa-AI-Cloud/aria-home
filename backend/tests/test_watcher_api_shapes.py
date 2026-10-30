"""Watcher/correction API shapes match what the frontend renders.

The real recordings store correction claims as lists of observation objects
({kind, claim, evidence_ids, values}), not strings. The API serves those
shapes through, so the frontend types and renderer must accept them.
"""
import json
from datetime import datetime
from pathlib import Path

from aria_home.eligibility import is_fresh
from aria_home.investigator import build_evidence_pack
from aria_home.scenario import load_scenario
from aria_home.watcher import (
    WATCHER_MODEL_ID,
    WATCHER_PROMPT_VERSION,
    watcher_identity,
)

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
AT = datetime.fromisoformat("2026-01-17T02:31:00-05:00")


def _care():
    return load_scenario(SCENARIOS_DIR / "care_home_v1")


def _assert_observation_shape(obs):
    assert isinstance(obs["kind"], str)
    assert isinstance(obs["claim"], str)
    assert isinstance(obs["evidence_ids"], list) and all(isinstance(i, str) for i in obs["evidence_ids"])
    assert isinstance(obs["values"], dict)


def _assert_correction_shape(record):
    assert isinstance(record["failed_checks"], list)
    assert all(isinstance(check, str) for check in record["failed_checks"])
    assert isinstance(record["final_result"], str)
    for key in ("original_claim", "revision_claim"):
        claims = record.get(key)
        assert claims is None or isinstance(claims, list)
        for obs in claims or []:
            assert isinstance(obs, dict)
            _assert_observation_shape(obs)


def test_real_correction_records_use_list_shaped_claims():
    paths = sorted(EVAL_DIR.glob("corrections-*.json"))
    assert paths, "expected real correction recordings in backend/eval"
    seen = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload["records"] if isinstance(payload, dict) and isinstance(payload.get("records"), list) else [payload]
        for record in records:
            if isinstance(record, dict) and "failed_checks" in record:
                _assert_correction_shape(record)
                seen += 1
    assert seen > 0


def test_real_watcher_entries_use_object_shaped_observations():
    paths = sorted(EVAL_DIR.glob("watchers-*.json"))
    assert paths, "expected real watcher recordings in backend/eval"
    seen = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload["watchers"] if isinstance(payload, dict) and isinstance(payload.get("watchers"), list) else payload
        for entry in entries:
            output = entry.get("output") if isinstance(entry, dict) else None
            for obs in (output or {}).get("observations", []):
                _assert_observation_shape(obs)
                seen += 1
    assert seen > 0


def _seeded_client(tmp_path, monkeypatch):
    from aria_home.app import create_app

    scenario = _care()
    pack = build_evidence_pack(scenario, AT)
    good = None
    for item in pack["evidence"]:
        if not isinstance(item, dict) or "data" in item:
            continue
        if item.get("quantity") != "indoor_temp" or item.get("value") is None:
            continue
        if not is_fresh(item, AT):
            continue
        good = {"kind": "temperature_drop", "claim": f"Room reading {item['value']} {item['unit']} noted",
                "evidence_ids": [item["id"]],
                "values": {"value": item["value"], "unit": item["unit"], "at": item["observed_at"]}}
        break
    assert good is not None
    identity = watcher_identity(scenario, AT)
    watchers_dir = tmp_path / "watchers"
    watchers_dir.mkdir(parents=True, exist_ok=True)
    (watchers_dir / "watchers-care-2026-10-30.json").write_text(json.dumps({"watchers": [{
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "laws_version": identity["laws_version"],
        "watcher_prompt_version": WATCHER_PROMPT_VERSION,
        "model_id": WATCHER_MODEL_ID,
        "provider_route": "mock",
        "code_snapshot": "shape-test",
        "recorded_at": "2026-10-30T19:03:25.476706+00:00",
        "status": "confirmed",
        "final_result": "confirmed",
        "failed_checks": [],
        "output": {"observations": [good]},
    }]}), encoding="utf-8")
    corrections_dir = tmp_path / "corrections"
    corrections_dir.mkdir(parents=True, exist_ok=True)
    (corrections_dir / "corrections-shape.json").write_text(json.dumps({"records": [{
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "laws_version": identity["laws_version"],
        "watcher_prompt_version": WATCHER_PROMPT_VERSION,
        "model_id": WATCHER_MODEL_ID,
        "provider_route": "mock",
        "recorded_at": "2026-10-30T19:03:48.602233Z",
        "original_claim": [good],
        "failed_checks": ["observation value does not match evidence r1"],
        "revision_claim": [good],
        "final_result": "corrected and verified",
    }]}), encoding="utf-8")
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(watchers_dir))
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(corrections_dir))
    return create_app().test_client()


def test_watcher_endpoint_observation_shapes(tmp_path, monkeypatch):
    client = _seeded_client(tmp_path, monkeypatch)
    body = client.get("/api/watcher", query_string={"scenario": "care_home_v1", "at": AT.isoformat()}).get_json()
    assert isinstance(body["model_observations"], list) and body["model_observations"]
    for obs in body["model_observations"]:
        _assert_observation_shape(obs)
        assert isinstance(obs["status"], str)
    assert isinstance(body["code_detections"], list)
    for detection in body["code_detections"]:
        assert isinstance(detection, dict)


def test_corrections_endpoint_claim_shapes(tmp_path, monkeypatch):
    client = _seeded_client(tmp_path, monkeypatch)
    body = client.get("/api/corrections").get_json()
    assert isinstance(body["corrections"], list) and body["corrections"]
    for record in body["corrections"]:
        _assert_correction_shape(record)
