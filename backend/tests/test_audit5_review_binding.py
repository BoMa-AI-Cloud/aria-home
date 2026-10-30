"""Audit 5 finding 5: each recorded review is bound to the exact answer it reviewed.

A review matches on scenario, replay time, evidence revision and review
configuration, but that is not enough: copying a valid care recording and
changing only its interpretation (still schema-valid) must not keep the old
no_issues review. Serving a review requires its answer_digest (sha256 of the
canonical JSON of the reviewed answer's output) to equal the digest of the
answer actually displayed; a mismatch shows no review and says
"review does not match this answer". Legacy reviews without answer_digest
(the ten committed ones) are never given a fabricated digest: they are shown
labelled "Review recorded before answer binding (legacy, not bound to this
exact answer)".
"""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from aria_home.app import create_app
from aria_home.investigator import PROMPT_VERSION, build_evidence_pack, inference_identity, investigate, validate
from aria_home.public_demo import CHECKPOINTS, scenario_list
from aria_home.readiness import READINESS_POLICY_VERSION
from aria_home.review import recorded_review_for
from aria_home.scenario import load_scenario

ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"
AT = "2026-01-17T02:31:00-05:00"
MISMATCH_MESSAGE = "review does not match this answer"
LEGACY_LABEL = "Review recorded before answer binding (legacy, not bound to this exact answer)"
LIVE_FLAGS = (
    "ARIA_HOME_MODEL_ENABLED",
    "ARIA_HOME_WHATSAPP_LIVE",
    "ARIA_HOME_EMPORIA_LIVE",
    "ARIA_HOME_VISUAL_LIVE",
    "ARIA_HOME_NEST_LIVE",
    "ARIA_HOME_E2E_HOOKS",
    "MODEL_API_KEY",
)


def _canonical_digest(output):
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _identity_and_answer():
    scn = load_scenario(SCENARIOS / CARE)
    at = datetime.fromisoformat(AT)
    identity = inference_identity(scn, at)
    result = investigate(scn, at)
    assert result.status == "ok", result.reasons
    return scn, at, identity, {
        "scenario_id": CARE,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API",
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "code_snapshot": "test-snapshot",
        "recorded_at": "2026-10-30T12:00:00+00:00",
        "status": "accepted",
        "output": result.output.model_dump(mode="json"),
    }


def _review_entry(identity, output, *, bound=True):
    entry = {
        "scenario_id": CARE,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-wonder-1.0",
        "review_contract_version": "review-v1",
        "reviewed_model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API (responses)",
        "recorded_at": "2026-10-30T12:00:00+00:00",
        "review": {"verdict": "no_issues", "issues": []},
    }
    if bound:
        entry["answer_digest"] = _canonical_digest(output)
    return entry


def _pack_ids(scn, at):
    return build_evidence_pack(scn, at)["evidence_ids"]


def _public_client(tmp_path, monkeypatch, name):
    for var in LIVE_FLAGS:
        monkeypatch.delenv(var, raising=False)
    recorded = tmp_path / name / "recorded"
    reviews = tmp_path / name / "reviews"
    recorded.mkdir(parents=True)
    reviews.mkdir(parents=True)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / name / "sessions"))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(reviews))
    return create_app().test_client(), recorded, reviews


def test_answer_digest_is_sha256_of_canonical_json():
    from aria_home.review import answer_digest

    output = {"b": [1, 2], "a": "x"}
    reordered = {"a": "x", "b": [1, 2]}
    assert answer_digest(output) == answer_digest(reordered)
    assert answer_digest(output) == hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    assert answer_digest({**output, "a": "y"}) != answer_digest(output)


def test_bound_review_shown_for_matching_answer():
    scn, at, identity, answer = _identity_and_answer()
    entries = [{"entry": _review_entry(identity, answer["output"]), "source": "test"}]
    shown = recorded_review_for(entries, CARE, identity["evaluated_at_utc"], identity["input_revision"], _pack_ids(scn, at), answer_output=answer["output"])
    assert shown is not None
    assert shown["review"] == {"verdict": "no_issues", "issues": []}
    assert shown["answer_bound"] is True


def test_review_withheld_when_only_interpretation_changed():
    scn, at, identity, answer = _identity_and_answer()
    tampered = copy.deepcopy(answer["output"])
    tampered["interpretation"] = answer["output"]["interpretation"] + " The hallway was quiet."
    assert validate(tampered, build_evidence_pack(scn, at)) == []
    entries = [{"entry": _review_entry(identity, answer["output"]), "source": "test"}]
    shown = recorded_review_for(entries, CARE, identity["evaluated_at_utc"], identity["input_revision"], _pack_ids(scn, at), answer_output=tampered)
    assert shown is not None
    assert shown["review"] is None
    assert MISMATCH_MESSAGE in " ".join(shown["provenance"]["validation"]["reasons"])


def test_audit_repro_changed_answer_loses_review_in_app(tmp_path, monkeypatch):
    scn, at, identity, answer = _identity_and_answer()
    client, recorded, reviews = _public_client(tmp_path, monkeypatch, "before")
    (recorded / "answers.json").write_text(json.dumps({"answers": [answer]}), encoding="utf-8")
    (reviews / "reviews-t1.json").write_text(json.dumps({"reviews": [_review_entry(identity, answer["output"])]}), encoding="utf-8")
    body = client.post(f"/api/investigations?scenario={CARE}&at={AT}").get_json()
    assert body["investigation"]["recorded_review"]["review"] == {"verdict": "no_issues", "issues": []}

    tampered_answer = dict(answer)
    tampered_answer["output"] = copy.deepcopy(answer["output"])
    tampered_answer["output"]["interpretation"] = answer["output"]["interpretation"] + " The hallway was quiet."
    assert validate(tampered_answer["output"], build_evidence_pack(scn, at)) == []
    client2, recorded2, reviews2 = _public_client(tmp_path, monkeypatch, "after")
    (recorded2 / "answers.json").write_text(json.dumps({"answers": [tampered_answer]}), encoding="utf-8")
    (reviews2 / "reviews-t1.json").write_text(json.dumps({"reviews": [_review_entry(identity, answer["output"])]}), encoding="utf-8")
    body2 = client2.post(f"/api/investigations?scenario={CARE}&at={AT}").get_json()
    assert body2["investigation"]["status"] == "ok"
    shown = body2["investigation"]["recorded_review"]
    assert shown["review"] is None
    assert MISMATCH_MESSAGE in " ".join(shown["provenance"]["validation"]["reasons"])


def test_legacy_review_shown_flagged_unbound(tmp_path, monkeypatch):
    _, _, identity, answer = _identity_and_answer()
    client, recorded, reviews = _public_client(tmp_path, monkeypatch, "legacy")
    (recorded / "answers.json").write_text(json.dumps({"answers": [answer]}), encoding="utf-8")
    (reviews / "reviews-t1.json").write_text(json.dumps({"reviews": [_review_entry(identity, answer["output"], bound=False)]}), encoding="utf-8")
    body = client.post(f"/api/investigations?scenario={CARE}&at={AT}").get_json()
    shown = body["investigation"]["recorded_review"]
    assert shown["review"] == {"verdict": "no_issues", "issues": []}
    assert shown.get("answer_bound") is False
    assert LEGACY_LABEL in (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")


def test_only_missing_treats_unbound_review_as_missing(tmp_path, monkeypatch):
    import scripts.record_care_answers as rca

    scn = load_scenario(SCENARIOS / CARE)
    point = list(CHECKPOINTS[CARE])[0]
    identity = inference_identity(scn, datetime.fromisoformat(point))
    seed_answer = {
        "scenario_id": CARE,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API",
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "code_snapshot": "seed",
        "recorded_at": "2026-10-29T12:00:00+00:00",
        "status": "accepted",
        "output": {},
    }
    monkeypatch.setattr(rca, "CHECKPOINTS", {CARE: (point,)})
    recorded = tmp_path / "recorded"
    reviews = tmp_path / "reviews"
    recorded.mkdir()
    reviews.mkdir()
    (recorded / "care-seed.json").write_text(json.dumps({"answers": [seed_answer]}), encoding="utf-8")
    (reviews / "reviews-seed.json").write_text(
        json.dumps({"reviews": [_review_entry(identity, {}, bound=False)]}), encoding="utf-8"
    )
    lines = []
    rc = rca.main(
        ["--only-missing", "--recorded-dir", str(recorded), "--reviews-dir", str(reviews), "--date", "2026-10-30"],
        out=lines.append,
        now=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )
    assert rc == 0
    assert "up to 1 (0 muse-spark-1.3 answers + up to 1 muse-wonder-1.0 reviews)" in "\n".join(lines)

    (reviews / "reviews-seed.json").write_text(
        json.dumps({"reviews": [_review_entry(identity, {}, bound=True)]}), encoding="utf-8"
    )
    lines = []
    rc = rca.main(
        ["--only-missing", "--recorded-dir", str(recorded), "--reviews-dir", str(reviews), "--date", "2026-10-30"],
        out=lines.append,
        now=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )
    assert rc == 0
    assert "skipped 1 recorded answer(s)" in "\n".join(lines)


def test_public_scenario_count_matches_docs(tmp_path, monkeypatch):
    items = scenario_list()
    assert len(items) == 8
    assert {item["id"] for item in items} >= {"care_home_v1", "demo_video_v1"}
    client, _, _ = _public_client(tmp_path, monkeypatch, "scenarios")
    exposed = client.get("/api/scenarios").get_json()["scenarios"]
    assert len(exposed) == 8
    assert "8 demo scenarios" in (ROOT / "README.md").read_text(encoding="utf-8")
