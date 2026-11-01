"""P1-2: a currently rejected watcher observation must not be labelled "corrected and verified"."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from aria_home import laws as laws_module
from aria_home.investigator import build_evidence_pack
from aria_home.scenario import load_scenario
from aria_home.trace import build_trace
from aria_home.watcher import WATCHER_PROMPT_VERSION, verify_observation, watcher_identity

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"
AT = "2026-01-16T19:20:00-05:00"


@pytest.fixture(autouse=True)
def _empty_corrections(monkeypatch, tmp_path):
    empty = tmp_path / "corr-empty"
    empty.mkdir()
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(empty))
    return empty


def _scenario():
    return load_scenario(SCENARIO_DIR)


def _at():
    return datetime.fromisoformat(AT)


def _passing_obs(scn, at):
    pack = build_evidence_pack(scn, at)
    for item in pack.get("evidence", []):
        if not isinstance(item, dict) or "data" in item or not item.get("id"):
            continue
        obs = {
            "kind": "temperature_drop",
            "claim": "Room reading looks cooler than earlier",
            "evidence_ids": [item["id"]],
            "values": {},
        }
        if verify_observation(obs, pack, at):
            continue
        if laws_module.check_output({"observations": [obs]}, pack, at):
            continue
        return obs
    raise AssertionError("no observation passes current checks at 19:20")


def _entry(scn, at, obs_list, output=None, final_result="rejected"):
    wid = watcher_identity(scn, at)
    return {
        "entry": {
            "scenario_id": wid["scenario_id"],
            "evaluated_at_utc": wid["evaluated_at_utc"],
            "input_revision": wid["input_revision"],
            "laws_version": wid["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION,
            "model_id": "muse-spark-1.3",
            "provider_route": "mock",
            "recorded_at": wid["evaluated_at_utc"],
            "output": {"observations": obs_list} if output is None else output,
            "final_result": final_result,
        },
        "source": "test",
    }


def _correction(scn, at, revision_claim, final_result="corrected and verified", **overrides):
    wid = watcher_identity(scn, at)
    record = {
        "scenario_id": wid["scenario_id"],
        "evaluated_at_utc": wid["evaluated_at_utc"],
        "input_revision": wid["input_revision"],
        "laws_version": wid["laws_version"],
        "watcher_prompt_version": wid["watcher_prompt_version"],
        "model_id": "muse-spark-1.3",
        "provider_route": "mock",
        "recorded_at": wid["evaluated_at_utc"],
        "original_claim": None,
        "failed_checks": ["observation value does not match"],
        "revision_claim": revision_claim,
        "final_result": final_result,
    }
    record.update(overrides)
    return record


def _write_corrections(tmp_path, records):
    path = Path(str(tmp_path)) / "corrections-test.json"
    path.write_text(json.dumps({"records": records}), encoding="utf-8")
    return path


def test_valid_kind_citing_nonexistent_evidence_stays_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path))
    scn, at = _scenario(), _at()
    bad = {"kind": "temperature_drop", "claim": "Ghost reading dropped", "evidence_ids": ["no-such-evidence"], "values": {}}
    entry = _entry(scn, at, [bad])
    _write_corrections(tmp_path, [_correction(scn, at, [bad])])
    trace = build_trace(scn, at, watcher_entries=[entry])
    assert trace["watcher"]["status"] == "rejected"


def test_invalid_output_stays_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path))
    scn, at = _scenario(), _at()
    entry = _entry(scn, at, [], output={"observations": "not-a-list"})
    _write_corrections(tmp_path, [_correction(scn, at, [_passing_obs(scn, at)])])
    trace = build_trace(scn, at, watcher_entries=[entry])
    assert trace["watcher"]["status"] == "rejected"


def test_correction_with_different_input_revision_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path))
    scn, at = _scenario(), _at()
    bad = {"kind": "temperature_drop", "claim": "Ghost reading dropped", "evidence_ids": ["no-such-evidence"], "values": {}}
    entry = _entry(scn, at, [bad])
    _write_corrections(tmp_path, [_correction(scn, at, [bad], input_revision="other-revision")])
    trace = build_trace(scn, at, watcher_entries=[entry])
    assert trace["watcher"]["status"] == "rejected"


def test_unrelated_same_time_correction_is_history_not_status(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path))
    scn, at = _scenario(), _at()
    bad = {"kind": "temperature_drop", "claim": "Ghost reading dropped", "evidence_ids": ["ghost-1"], "values": {}}
    entry = _entry(scn, at, [bad])
    _write_corrections(tmp_path, [_correction(scn, at, [_passing_obs(scn, at)])])
    trace = build_trace(scn, at, watcher_entries=[entry])
    assert trace["watcher"]["status"] == "rejected"
    assert len(trace["watcher"]["corrections"]) == 1


def test_genuinely_matched_correction_stays_corrected_and_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path))
    scn, at = _scenario(), _at()
    good = _passing_obs(scn, at)
    entry = _entry(scn, at, [good], final_result="corrected and verified")
    _write_corrections(tmp_path, [_correction(scn, at, [good])])
    trace = build_trace(scn, at, watcher_entries=[entry])
    assert trace["watcher"]["status"] == "corrected and verified"
