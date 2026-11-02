"""Old recordings never match the restructured story: exact identity everywhere.

The curve rewrite changed every input_revision since 16:00 and the prompt
moved to inv-v6, so previously recorded answers, reviews, watcher runs and
corrections must all read as missing — never as matching.
"""
import json
from datetime import datetime
from pathlib import Path

from aria_home.investigator import PROMPT_VERSION, inference_identity
from aria_home.readiness import READINESS_POLICY_VERSION
from aria_home.recorded import NO_RECORDED_LABEL, find_recorded, public_investigation
from aria_home.review import REVIEW_CONTRACT_VERSION, REVIEW_MODEL_ID, find_recorded_review
from aria_home.scenario import load_scenario
from aria_home.trace import build_trace
from aria_home.watcher import (
    NO_RECORDED_WATCHER_LABEL,
    WATCHER_PROMPT_VERSION,
    public_watcher,
    watcher_identity,
)

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"
AT = "2026-01-16T22:46:00-05:00"


def _care():
    return load_scenario(SCENARIOS_DIR / CARE)


def _at():
    return datetime.fromisoformat(AT)


def test_old_prompt_answer_never_matches():
    scenario = _care()
    identity = inference_identity(scenario, _at())
    old = {
        "answer": {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "model_id": "muse-spark-1.3",
            "prompt_version": "inv-v3",
            "readiness_policy_version": READINESS_POLICY_VERSION,
            "output": {"interpretation": "stale"},
        }
    }
    assert PROMPT_VERSION == "inv-v6"
    assert find_recorded([old], identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"]) is None


def test_wrong_input_revision_answer_never_matches():
    scenario = _care()
    identity = inference_identity(scenario, _at())
    old = {
        "answer": {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": "pre-restructure-revision",
            "model_id": "muse-spark-1.3",
            "prompt_version": PROMPT_VERSION,
            "readiness_policy_version": READINESS_POLICY_VERSION,
            "output": {"interpretation": "stale"},
        }
    }
    assert find_recorded([old], identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"]) is None


def test_old_review_never_matches():
    scenario = _care()
    identity = inference_identity(scenario, _at())
    old = {
        "entry": {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "model_id": REVIEW_MODEL_ID,
            "review_contract_version": REVIEW_CONTRACT_VERSION,
            "reviewed_prompt_version": "inv-v3",
            "reviewed_readiness_policy_version": READINESS_POLICY_VERSION,
            "review": {"verdict": "no_issues", "issues": []},
        }
    }
    assert find_recorded_review([old], identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"]) is None


def test_stale_watcher_run_not_shown():
    scenario = _care()
    wid = watcher_identity(scenario, _at())
    old = {
        "entry": {
            "scenario_id": wid["scenario_id"],
            "evaluated_at_utc": wid["evaluated_at_utc"],
            "input_revision": "pre-restructure-revision",
            "laws_version": wid["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION,
            "model_id": "muse-spark-1.3",
            "output": {"observations": [{"kind": "temperature_drop", "claim": "stale", "evidence_ids": [], "values": {}}]},
            "final_result": "confirmed",
        }
    }
    view = public_watcher(scenario, _at(), entries=[old])
    assert view["model_observations"] == []
    assert view["model_note"] == NO_RECORDED_WATCHER_LABEL


def _seed_corrections(directory, revision):
    scenario = _care()
    wid = watcher_identity(scenario, _at())
    record = {
        "scenario_id": wid["scenario_id"],
        "evaluated_at_utc": wid["evaluated_at_utc"],
        "input_revision": revision,
        "laws_version": wid["laws_version"],
        "watcher_prompt_version": wid["watcher_prompt_version"],
        "original_claim": "stale claim",
        "failed_checks": ["observation value does not match"],
        "revision_claim": "stale revision",
        "final_result": "corrected and verified",
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "corrections-old.json").write_text(json.dumps({"records": [record]}), encoding="utf-8")
    return wid


def test_corrections_endpoint_scopes_old_records_out(tmp_path, monkeypatch):
    from aria_home.app import create_app

    corrections = tmp_path / "corrections"
    wid = _seed_corrections(corrections, "pre-restructure-revision")
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(corrections))
    client = create_app().test_client()
    unfiltered = client.get("/api/corrections").get_json()
    assert len(unfiltered["corrections"]) == 1
    scoped = client.get("/api/corrections", query_string={"scenario": CARE, "at": AT}).get_json()
    assert scoped["corrections"] == []
    _seed_corrections(corrections, wid["input_revision"])
    rescoped = client.get("/api/corrections", query_string={"scenario": CARE, "at": AT}).get_json()
    assert len(rescoped["corrections"]) == 1


def test_trace_corrections_exclude_old_identity(tmp_path, monkeypatch):
    corrections = tmp_path / "corrections"
    _seed_corrections(corrections, "pre-restructure-revision")
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(corrections))
    trace = build_trace(_care(), _at())
    assert trace["watcher"]["corrections"] == []


def test_earlier_explanations_empty_without_match():
    investigation, _ = public_investigation(_care(), _at(), entries=[])
    assert investigation.output is None
    assert NO_RECORDED_LABEL in (investigation.reasons or [])
