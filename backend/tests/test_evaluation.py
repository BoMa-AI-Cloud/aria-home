import json
from pathlib import Path

import pytest

from aria_home.evaluation import (
    CASES,
    CONDITIONS,
    check_live_allowed,
    load_expected,
    main,
    run_model_cases,
    run_offline,
)
from aria_home.provider import MockProvider

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def offline():
    return run_offline()


def test_expected_covers_every_case():
    expected = load_expected()
    assert [(c["scenario"], c["at"]) for c in expected] == list(CASES)
    assert len({c["id"] for c in expected}) == len(expected)
    for case in expected:
        assert case["expected_readiness"] in ("on_track", "at_risk", "cannot_tell")
        assert case["reason"].strip()
    video = [c for c in expected if c["scenario"] == "demo_video_v1"]
    assert all(c["expected_verification"] for c in video)


def test_combined_matches_every_expected_label(offline):
    combined = [r for r in offline["rows"] if r["condition"] == "combined"]
    assert len(combined) == len(CASES)
    for row in combined:
        assert row["readiness_correct"], row
        assert row["verification_correct"] is not False, row
        assert row["correct"], row
    assert offline["totals"]["combined"]["fully_correct"] == len(CASES)
    for condition in CONDITIONS[1:]:
        assert offline["totals"][condition]["fully_correct"] < len(CASES)


def test_thermostat_only_during_video_outage_cannot_support_warming(offline):
    row = next(
        r
        for r in offline["rows"]
        if r["case_id"] == "demo_video_v1@16:31" and r["condition"] == "thermostat_only"
    )
    assert row["claims"]["warming"] is False
    assert row["claims"]["current_temperature"] is False
    assert row["claims"]["useful_heat"] is False
    combined = next(
        r
        for r in offline["rows"]
        if r["case_id"] == "demo_video_v1@16:31" and r["condition"] == "combined"
    )
    assert combined["claims"]["current_temperature"] is True
    assert combined["claims"]["warming"] is False


def test_electrical_only_never_supports_useful_heat(offline):
    rows = [r for r in offline["rows"] if r["condition"] == "electrical_only"]
    assert rows
    assert all(r["claims"]["useful_heat"] is False for r in rows)
    assert any(r["claims"]["electrical_activity"] for r in rows)
    assert all(r["claims"]["useful_heat"] is False for r in offline["rows"])


def test_live_refuses_without_all_three_switches(monkeypatch):
    monkeypatch.delenv("ARIA_HOME_MODEL_ENABLED", raising=False)
    with pytest.raises(RuntimeError):
        check_live_allowed(False, None)
    with pytest.raises(RuntimeError):
        check_live_allowed(True, None, env={"ARIA_HOME_MODEL_ENABLED": "1"})
    with pytest.raises(RuntimeError):
        check_live_allowed(True, 3, env={})
    with pytest.raises(RuntimeError):
        check_live_allowed(False, 3, env={"ARIA_HOME_MODEL_ENABLED": "1"})
    assert check_live_allowed(True, 3, env={"ARIA_HOME_MODEL_ENABLED": "1"}) is True

    with pytest.raises(SystemExit):
        main(["--live"])
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "1")
    with pytest.raises(SystemExit):
        main(["--live"])
    with pytest.raises(SystemExit):
        main(["--live", "--max-calls", "0"])


def test_model_condition_with_mock_provider():
    cases = load_expected()[:1]
    records = run_model_cases(MockProvider(), cases=cases)
    assert len(records) == 1
    record = records[0]
    assert record["case_id"] == cases[0]["id"]
    assert record["status"] in ("ok", "rejected", "unavailable")
    assert record["computed_readiness"] == cases[0]["expected_readiness"]
    assert "readiness_agreement" in record
    assert "rejected_claim_reasons" in record
    assert "latency_ms" in record
    assert "input_tokens" in record and "output_tokens" in record
    if record["status"] == "ok":
        assert record["readiness_agreement"] is True


def test_cli_offline_writes_both_files(tmp_path):
    results = tmp_path / "results-offline.json"
    docs = tmp_path / "evaluation.md"
    assert main(["--offline", "--results", str(results), "--docs", str(docs)]) == 0
    data = json.loads(results.read_text(encoding="utf-8"))
    assert data["totals"]["combined"]["fully_correct"] == len(CASES)
    assert len(data["rows"]) == len(CASES) * len(CONDITIONS)
    text = docs.read_text(encoding="utf-8")
    assert "not a benchmark of real homes" in text
    assert "demo_video_v1@16:31" in text
    assert "| Condition |" in text
