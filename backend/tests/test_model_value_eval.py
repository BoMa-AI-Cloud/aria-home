import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from aria_home.investigator import build_evidence_pack  # noqa: E402
from aria_home.outcomes import follow_up_for  # noqa: E402
from aria_home.provider import MockProvider  # noqa: E402
from aria_home.scenario import load_scenario  # noqa: E402
from aria_home.verification import verify_recovery  # noqa: E402
from make_eval_variants import main as make_variants  # noqa: E402
from run_model_value_eval import (  # noqa: E402
    PLANTED_CLAIMS,
    load_variants,
    main as eval_main,
    render_report,
    score_spark,
    score_watcher,
    score_wonder,
)

VARIANTS_DIR = BACKEND_DIR / "scenarios" / "eval_variants"

EXPECTED = {
    "ev-outage-2310": ("at_risk", "telemetry_missing"),
    "ev-outage-0130": ("at_risk", "telemetry_missing"),
    "ev-outage-0340": ("at_risk", "telemetry_missing"),
    "ev-recovery-fails": ("at_risk", "goal_not_maintained"),
    "ev-slow-cool-ontrack": ("on_track", "goal_verified"),
    "ev-thermostat-gap-steady": ("on_track", "telemetry_missing"),
    "ev-stale-room": ("cannot_tell", "unable_to_verify"),
    "ev-wrong-zone": ("at_risk", "telemetry_missing"),
    "ev-report-no-warm": ("at_risk", "reporting_restored"),
    "ev-normal-night": ("on_track", "goal_verified"),
    "ev-conflict-sensors": ("cannot_tell", "unable_to_verify"),
    "ev-arrival-met": ("arrival_passed", "arrival_met"),
}

ALLOWLISTED = {
    Path("backend/tests/test_model_value_eval.py"),
    Path("backend/scripts/make_eval_variants.py"),
    Path("backend/scripts/run_model_value_eval.py"),
    Path("docs/model-value-eval-plan.md"),
    Path("docs/model-value-eval.md"),
}


def _variant_ids():
    return [json.loads((VARIANTS_DIR / vid / "variant.json").read_text(encoding="utf-8"))["id"] for vid in EXPECTED]


def test_variants_regenerate_deterministically(tmp_path):
    assert make_variants(["--out", str(tmp_path)]) == 0
    for vid in EXPECTED:
        for name in ("manifest.json", "calendar.json", "thermostat.json", "room_sensor.json",
                     "electrical.json", "weather.json", "events.json", "variant.json"):
            fresh = (tmp_path / vid / name).read_bytes()
            committed = (VARIANTS_DIR / vid / name).read_bytes()
            assert fresh == committed, f"{vid}/{name} differs from committed file"


def test_variant_labels_match_code():
    variants = load_variants(VARIANTS_DIR)
    assert len(variants) == 12
    for variant in variants:
        scenario = load_scenario(VARIANTS_DIR / variant["id"])
        at = datetime.fromisoformat(variant["eval_at"])
        pack = build_evidence_pack(scenario, at)
        followup = follow_up_for(scenario, f"inv-{variant['id']}", datetime.fromisoformat(variant["followup_created_at"]))
        stage = verify_recovery(scenario, followup, at)["stage"]
        assert pack["computed_readiness"] == variant["expected_readiness"]
        assert stage == variant["expected_verification"]
        assert (variant["expected_readiness"], variant["expected_verification"]) == EXPECTED[variant["id"]]
        assert variant["ground_truth"]["problem"]
        assert variant["ground_truth"]["next_action"]


def test_variants_unused_elsewhere():
    needles = {"eval_variants", *_variant_ids()}
    roots = [BACKEND_DIR / "aria_home", BACKEND_DIR / "eval", BACKEND_DIR / "tests", BACKEND_DIR / "scenarios",
             BACKEND_DIR.parent / "docs", BACKEND_DIR.parent / "frontend"]
    hits = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix in {".pyc", ".png", ".svg"}:
                continue
            rel = path.relative_to(BACKEND_DIR.parent)
            if rel in ALLOWLISTED or "eval_variants" in rel.parts:
                continue
            if rel.parts[:3] == ("backend", "eval", "model-value"):
                continue
            # The build log records coding-agent prompts, never inputs to the evaluated models.
            if rel.parts[:2] == ("docs", "build-log"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for needle in needles:
                if needle in text:
                    hits.append(f"{rel}: {needle}")
    assert hits == []


def test_dry_run_makes_zero_calls(capsys):
    assert eval_main([]) == 0
    text = capsys.readouterr().out
    assert "variants: 12" in text
    assert "planned calls: 60" in text
    assert "zero model calls made" in text


def test_cap_refuses_live(capsys):
    assert eval_main(["--live", "--max-calls", "59", "--code-snapshot", "abc"]) == 2
    assert "exceed" in capsys.readouterr().out
    assert eval_main(["--live", "--max-calls", "60"]) == 2


def test_scoring_fakes():
    spark_item = {"variant": "v", "expected_readiness": "at_risk",
                  "spark": {"status": "ok", "output": {"readiness": "at_risk"}}}
    assert score_spark(spark_item)["verdict"] == "pass"
    bad_item = {"variant": "v", "expected_readiness": "at_risk",
                "spark": {"status": "rejected", "reasons": ["boom"]}}
    assert score_spark(bad_item)["verdict"] == "rejected"
    wonder = score_wonder([
        {"variant": "a", "wonder_genuine": {"status": "ok", "review": {"verdict": "no_issues"}},
         "wonder_planted": {"status": "ok", "planted_claim": "wrong-time", "review": {"verdict": "issues_found"}}},
        {"variant": "b", "wonder_genuine": {"status": "ok", "review": {"verdict": "issues_found"}},
         "wonder_planted": {"status": "error", "error": "timeout"}},
    ])
    assert (len(wonder["planted_flagged"]), wonder["planted_total"]) == (1, 1)
    assert (len(wonder["genuine_flagged"]), wonder["genuine_total"]) == (1, 2)
    watcher = score_watcher([
        {"variant": "a", "watcher": {"final_result": "confirmed", "observations": [{"claim": "x"}],
                                    "failed_checks": [], "correction_record": None,
                                    "code_detections": [], "code_triggered": False, "provider_calls": 1}},
        {"variant": "b", "watcher": {"final_result": "corrected and verified", "observations": [{"claim": "y"}],
                                    "failed_checks": [], "code_detections": [{"rule": "r"}],
                                    "code_triggered": True, "provider_calls": 2,
                                    "correction_record": {"failed_checks": ["bad value"], "final_result": "corrected and verified"}}},
    ])
    assert set(watcher["first_verified"]) == {"a"}
    assert set(watcher["revised_ok"]) == {"b"}
    assert watcher["missed_proxy"] == []


def _fake_http_post(url, headers, body, timeout_s):
    import json as _json

    user_content = body["input"][1]["content"]
    payload = _json.loads(user_content)
    pack_ids = payload["evidence_pack"].get("evidence_ids", [])
    planted = any(claim["sentence"] in user_content for claim in PLANTED_CLAIMS)
    if planted:
        review = {"verdict": "issues_found", "issues": [
            {"kind": "unsupported_claim", "evidence_ids": pack_ids[:1], "note": "fake catch"}]}
    else:
        review = {"verdict": "no_issues", "issues": []}
    return 200, {"output": [{"type": "message", "content": [{"type": "output_text", "text": _json.dumps(review)}]}]}


def test_live_with_fakes_writes_report(tmp_path):
    spark = MockProvider(model_id="muse-spark-1.3")
    watcher = MockProvider(model_id="muse-spark-1.3")
    report = tmp_path / "report.md"
    out_dir = tmp_path / "model-value"
    assert eval_main(["--live", "--max-calls", "60", "--code-snapshot", "fake-snap",
                      "--variants-dir", str(VARIANTS_DIR), "--out-dir", str(out_dir),
                      "--report", str(report)],
                     env={"MODEL_API_KEY": "test-fake-key"},
                     http_post=_fake_http_post,
                     spark_provider=spark, watcher_provider=watcher) == 0
    raws = list(out_dir.glob("model-value-*.json"))
    assert len(raws) == 1
    payload = json.loads(raws[0].read_text(encoding="utf-8"))
    assert len(payload["records"]) == 12
    planted_ids = {r["wonder_planted"]["planted_claim"] for r in payload["records"]
                   if r.get("wonder_planted", {}).get("planted_claim")}
    assert planted_ids == {c["id"] for c in PLANTED_CLAIMS}
    text = report.read_text(encoding="utf-8")
    assert "/12" in text
    assert "Limitations" in text


def test_report_shows_denominators_and_failures():
    results = [{"variant": "v1", "wonder_genuine": {"status": "ok", "review": {"verdict": "no_issues"}},
                "wonder_planted": {"status": "ok", "planted_claim": "wrong-time", "review": {"verdict": "no_issues"}},
                "watcher": {}}]
    spark_scores = [{"verdict": "fail", "reasons": ["readiness 'on_track' != code label 'at_risk'"], "needs_human": []}]
    wonder = score_wonder(results)
    watcher_scores = {"first_verified": {}, "first_rejected": {"v1": ["bad value"]},
                      "revisions_attempted": ["v1"], "revised_ok": [], "missed_proxy": ["v1"]}
    text = render_report(results, spark_scores, wonder, watcher_scores, "snap", "stamp")
    assert "0/1" in text
    assert "FAIL v1" in text
    assert "REJECTED v1" in text
    assert "MISSED-PROXY v1" in text
    assert "Limitations" in text
