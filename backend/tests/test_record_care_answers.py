"""Operator script tests: record approved care-story answers and reviews."""
import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.record_care_answers as rca
from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack, inference_identity, investigate
from aria_home.provider import MockProvider, ProviderResult
from aria_home.public_demo import CHECKPOINTS
from aria_home.recorded import NO_RECORDED_LABEL, load_recorded_answers, public_investigation
from aria_home.review import load_recorded_reviews, recorded_review_for

CARE = rca.CARE_SCENARIO_ID
REAL_POINTS = list(CHECKPOINTS[CARE])
FIXED_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
SENTINEL_KEY = "sentinel-key-never-logged-xyz"


class FakeLiveProvider:
    mode = "live"
    model_id = "muse-spark-1.3"

    def __init__(self):
        self.calls = 0
        self._mock = MockProvider(model_id="muse-spark-1.3")

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return self._mock.generate(prompt, **kwargs)


class BadProvider:
    mode = "live"
    model_id = "muse-spark-1.3"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return ProviderResult(ok=True, mode="live", requested_model=self.model_id, answered_model=self.model_id, text="not json")


def _review_post(calls):
    def post(url, headers, body, timeout_s):
        calls.append((url, body))
        return 200, {"verdict": "no_issues", "issues": []}
    return post


def _env():
    return {"MODEL_API_KEY": SENTINEL_KEY}


def _run(argv, tmp_path, provider, review_calls=None, checkpoints=None, monkeypatch=None):
    lines = []
    recorded = tmp_path / "recorded"
    reviews = tmp_path / "reviews"
    args = [*argv, "--recorded-dir", str(recorded), "--reviews-dir", str(reviews), "--date", "2026-10-30"]
    if checkpoints is not None:
        monkeypatch.setattr(rca, "CHECKPOINTS", {CARE: tuple(checkpoints)})
    rc = rca.main(args, provider=provider, http_post=_review_post(review_calls) if review_calls is not None else None, env=_env(), out=lines.append, now=FIXED_NOW)
    return rc, "\n".join(lines), recorded, reviews


def test_dry_run_makes_zero_calls(tmp_path):
    provider = FakeLiveProvider()
    review_calls = []
    rc, text, recorded, reviews = _run([], tmp_path, provider, review_calls)
    assert rc == 0
    assert provider.calls == 0
    assert review_calls == []
    assert len(REAL_POINTS) == 10
    for point in REAL_POINTS:
        assert point in text
    assert "dry run" in text
    assert not recorded.exists() or list(recorded.glob("*.json")) == []


def test_live_without_max_calls_refuses(tmp_path):
    provider = FakeLiveProvider()
    rc, _, _, _ = _run(["--live", "--code-snapshot", "abc"], tmp_path, provider, [])
    assert rc == 2
    assert provider.calls == 0


def test_live_without_snapshot_refuses(tmp_path):
    provider = FakeLiveProvider()
    rc, _, _, _ = _run(["--live", "--max-calls", "20"], tmp_path, provider, [])
    assert rc == 2
    assert provider.calls == 0


def test_planned_exceeding_cap_refuses_before_any_call(tmp_path):
    provider = FakeLiveProvider()
    review_calls = []
    rc, text, recorded, _ = _run(["--live", "--max-calls", "4", "--code-snapshot", "abc"], tmp_path, provider, review_calls)
    assert rc == 2
    assert provider.calls == 0
    assert review_calls == []
    assert list(recorded.glob("*.json")) == [] if recorded.exists() else True


def test_cap_stops_after_exactly_four_calls(tmp_path, monkeypatch):
    provider = FakeLiveProvider()
    review_calls = []
    rc, text, recorded, reviews = _run(
        ["--live", "--max-calls", "4", "--code-snapshot", "test-snap"],
        tmp_path, provider, review_calls, checkpoints=REAL_POINTS[:2], monkeypatch=monkeypatch,
    )
    assert rc == 0
    assert provider.calls == 2
    assert len(review_calls) == 2
    assert "model calls made: 4" in text
    entries = load_recorded_answers(recorded)
    assert len(entries) == 2
    assert load_recorded_reviews(reviews) and len(load_recorded_reviews(reviews)) == 2


def test_files_load_serve_and_hide_key(tmp_path):
    provider = FakeLiveProvider()
    review_calls = []
    rc, text, recorded, reviews = _run(
        ["--live", "--max-calls", "20", "--code-snapshot", "test-snap"],
        tmp_path, provider, review_calls,
    )
    assert rc == 0
    entries = load_recorded_answers(recorded)
    assert len(entries) == 10
    for item in entries:
        answer = item["answer"]
        for field in ("scenario_id", "evaluated_at_utc", "input_revision", "model_id", "provider_route", "prompt_version", "readiness_policy_version", "code_snapshot", "recorded_at", "output"):
            assert field in answer, field
        assert answer["scenario_id"] == CARE
        assert answer["model_id"] == "muse-spark-1.3"
        assert answer["code_snapshot"] == "test-snap"
    accepted = [item["answer"] for item in entries if item["answer"].get("status") == "accepted"]
    assert accepted
    first = accepted[0]
    from aria_home.scenario import load_scenario

    scn = load_scenario(rca.SCENARIOS_DIR / CARE)
    at = datetime.fromisoformat(REAL_POINTS[0])
    identity = inference_identity(scn, at)
    if first["input_revision"] != identity["input_revision"]:
        at = next(datetime.fromisoformat(p) for p in REAL_POINTS if inference_identity(scn, datetime.fromisoformat(p))["input_revision"] == first["input_revision"])
        identity = inference_identity(scn, at)
    result, provenance = public_investigation(scn, at, entries=entries)
    assert result.status == "ok"
    assert provenance["model_id"] == "muse-spark-1.3"
    review_entries = load_recorded_reviews(reviews)
    assert len(review_entries) == len(accepted)
    pack_ids = build_evidence_pack(scn, at)["evidence_ids"]
    shown = recorded_review_for(review_entries, CARE, identity["evaluated_at_utc"], identity["input_revision"], pack_ids)
    assert shown is not None and shown["review"] == {"verdict": "no_issues", "issues": []}
    assert SENTINEL_KEY not in text
    for path in (*recorded.glob("*.json"), *reviews.glob("*.json")):
        assert SENTINEL_KEY not in path.read_text(encoding="utf-8")


def test_rejected_answer_is_never_served(tmp_path, monkeypatch):
    provider = BadProvider()
    rc, _, recorded, _ = _run(
        ["--live", "--max-calls", "4", "--code-snapshot", "test-snap"],
        tmp_path, provider, None, checkpoints=REAL_POINTS[:2], monkeypatch=monkeypatch,
    )
    assert rc == 0
    assert provider.calls == 2
    entries = load_recorded_answers(recorded)
    assert len(entries) == 2
    assert all(item["answer"].get("status") == "rejected" for item in entries)
    from aria_home.scenario import load_scenario

    scn = load_scenario(rca.SCENARIOS_DIR / CARE)
    at = datetime.fromisoformat(REAL_POINTS[0])
    result, provenance = public_investigation(scn, at, entries=entries)
    assert result.status == "unavailable"
    assert NO_RECORDED_LABEL in result.reasons
    assert provenance is None


def test_rejected_status_refused_even_with_valid_output():
    from aria_home.scenario import load_scenario

    scn = load_scenario(rca.SCENARIOS_DIR / CARE)
    at = datetime.fromisoformat(REAL_POINTS[0])
    identity = inference_identity(scn, at)
    result = investigate(scn, at)
    assert result.status == "ok", result.reasons
    good = {
        "scenario_id": CARE,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API",
        "prompt_version": result.prompt_version,
        "readiness_policy_version": identity["readiness_policy_version"],
        "code_snapshot": "test-snap",
        "recorded_at": "2026-10-30T12:00:00+00:00",
        "status": "rejected",
        "rejection_reasons": ["stale test rejection"],
        "output": result.output.model_dump(mode="json"),
    }
    served, _ = public_investigation(scn, at, entries=[{"answer": dict(good, status="accepted"), "source": "test"}])
    assert served.status == "ok"
    refused, _ = public_investigation(scn, at, entries=[{"answer": good, "source": "test"}])
    assert refused.status == "unavailable"


def test_second_run_never_overwrites(tmp_path):
    provider = FakeLiveProvider()
    args = ["--live", "--max-calls", "20", "--code-snapshot", "s"]
    _run(args, tmp_path, provider, [])
    _run(args, tmp_path, provider, [])
    names = sorted(p.name for p in (tmp_path / "recorded").glob("*.json"))
    assert names == ["care-2026-10-30-1.json", "care-2026-10-30.json"]


def test_app_serves_recorded_answer_and_review(tmp_path, monkeypatch):
    provider = FakeLiveProvider()
    review_calls = []
    rc, _, recorded, reviews = _run(
        ["--live", "--max-calls", "20", "--code-snapshot", "test-snap"],
        tmp_path, provider, review_calls,
    )
    assert rc == 0
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE", "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(reviews))
    client = create_app().test_client()
    body = client.post(f"/api/investigations?scenario={CARE}&at={REAL_POINTS[0]}").get_json()
    assert body["investigation"]["status"] == "ok"
    assert body["investigation"]["recorded_provenance"]["model_id"] == "muse-spark-1.3"
    assert body["investigation"]["recorded_review"]["review"] == {"verdict": "no_issues", "issues": []}
    assert SENTINEL_KEY not in json.dumps(body)
