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


def _review_post_with_timeout(calls):
    def post(url, headers, body, timeout_s):
        calls.append(timeout_s)
        return 200, {"verdict": "no_issues", "issues": []}
    return post


def _run_timeout(argv_extra, tmp_path, monkeypatch, expected):
    monkeypatch.setattr(rca, "CHECKPOINTS", {CARE: tuple(REAL_POINTS[:1])})
    provider = FakeLiveProvider()
    seen = []
    lines = []
    recorded = tmp_path / f"recorded-{expected}"
    reviews = tmp_path / f"reviews-{expected}"
    rc = rca.main(
        ["--live", "--max-calls", "2", "--code-snapshot", "s",
         "--recorded-dir", str(recorded), "--reviews-dir", str(reviews),
         "--date", "2026-10-30", *argv_extra],
        provider=provider, http_post=_review_post_with_timeout(seen),
        env=_env(), out=lines.append, now=FIXED_NOW,
    )
    return rc, provider, seen


def test_recording_timeout_defaults_to_180s(tmp_path, monkeypatch):
    rc, provider, seen = _run_timeout([], tmp_path, monkeypatch, 180)
    assert rc == 0
    assert provider.timeout_s == 180.0
    assert seen == [180.0]


def test_recording_timeout_override_reaches_both_seams(tmp_path, monkeypatch):
    rc, provider, seen = _run_timeout(["--timeout-s", "42"], tmp_path, monkeypatch, 42)
    assert rc == 0
    assert provider.timeout_s == 42.0
    assert seen == [42.0]


def test_bad_review_response_reports_scrubbed_status_and_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(rca, "CHECKPOINTS", {CARE: tuple(REAL_POINTS[:1])})
    provider = FakeLiveProvider()
    long_message = f"invalid payload, key {SENTINEL_KEY} rejected; " + "x" * 500

    def post(url, headers, body, timeout_s):
        return 400, {"error": {"message": long_message}}

    lines = []
    rc = rca.main(
        ["--live", "--max-calls", "2", "--code-snapshot", "s",
         "--recorded-dir", str(tmp_path / "recorded"), "--reviews-dir", str(tmp_path / "reviews"),
         "--date", "2026-10-30"],
        provider=provider, http_post=post, env=_env(), out=lines.append, now=FIXED_NOW,
    )
    assert rc == 0
    text = "\n".join(lines)
    assert "review not recorded" in text
    assert "400" in text
    assert "[redacted]" in text
    assert SENTINEL_KEY not in text


def test_send_review_request_failure_carries_status_and_scrubbed_detail():
    from aria_home.review import build_review_request, send_review_request

    request = build_review_request({"answer": 1}, {"evidence_ids": []})
    long_message = f"bad request {SENTINEL_KEY} " + "y" * 500

    def post(url, headers, body, timeout_s):
        return 400, {"error": {"message": long_message}}

    sent = send_review_request(request, SENTINEL_KEY, http_post=post)
    assert sent["ok"] is False
    assert sent["error"] == "bad_response"
    assert sent["status"] == 400
    assert SENTINEL_KEY not in sent["detail"]
    assert "[redacted]" in sent["detail"]
    assert len(sent["detail"]) <= 300


def _seed_mixed_answers():
    from aria_home.scenario import load_scenario

    scn = load_scenario(rca.SCENARIOS_DIR / CARE)
    seed = []
    for index, point in enumerate(REAL_POINTS):
        identity = inference_identity(scn, datetime.fromisoformat(point))
        base = {
            "scenario_id": CARE,
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "model_id": "muse-spark-1.3",
            "provider_route": "meta live via Meta Model API",
            "prompt_version": "inv-v3",
            "readiness_policy_version": identity["readiness_policy_version"],
            "code_snapshot": "seed",
            "recorded_at": "2026-10-29T12:00:00+00:00",
        }
        if index == 0:
            seed.append({**base, "status": "accepted", "output": {}})
        else:
            seed.append({**base, "status": "rejected", "rejection_reasons": ["old"], "output": {"raw_text": ""}})
    return seed


def _run_only_missing(tmp_path, provider, review_calls, max_calls):
    lines = []
    recorded = tmp_path / "recorded"
    reviews = tmp_path / "reviews"
    rc = rca.main(
        ["--live", "--only-missing", "--max-calls", str(max_calls), "--code-snapshot", "s",
         "--recorded-dir", str(recorded), "--reviews-dir", str(reviews),
         "--date", "2026-10-30"],
        provider=provider, http_post=_review_post(review_calls),
        env=_env(), out=lines.append, now=FIXED_NOW,
    )
    return rc, "\n".join(lines)


def test_only_missing_plans_nine_answers_plus_ten_reviews(tmp_path):
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    (recorded / "care-2026-10-29.json").write_text(json.dumps({"answers": _seed_mixed_answers()}), encoding="utf-8")
    (tmp_path / "reviews").mkdir()
    provider = FakeLiveProvider()
    review_calls = []
    rc, text = _run_only_missing(tmp_path, provider, review_calls, 18)
    assert rc == 2
    assert provider.calls == 0
    assert review_calls == []
    assert "planned 19 calls exceed --max-calls 18" in text


def test_only_missing_records_nine_answers_and_ten_reviews(tmp_path):
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    (recorded / "care-2026-10-29.json").write_text(json.dumps({"answers": _seed_mixed_answers()}), encoding="utf-8")
    (tmp_path / "reviews").mkdir()
    provider = FakeLiveProvider()
    review_calls = []
    rc, text = _run_only_missing(tmp_path, provider, review_calls, 19)
    assert rc == 0
    assert provider.calls == 9
    assert len(review_calls) == 10
    assert "model calls made: 19" in text


def test_only_missing_dry_run_reports_exact_remaining():
    lines = []
    rc = rca.main(["--only-missing"], out=lines.append, now=FIXED_NOW)
    assert rc == 0
    text = "\n".join(lines)
    print("\n" + text)
    assert "only-missing:" in text
