"""Operator script tests: record the approved care-story watcher batch."""
import json
from datetime import datetime, timezone

import scripts.record_care_watcher as rcw
from aria_home.public_demo import CHECKPOINTS
from aria_home.scenario import load_scenario
from aria_home.watcher import (
    NO_TEXT_REASON,
    WATCHER_MODEL_ID,
    WATCHER_PROMPT_VERSION,
    find_recorded_watcher,
    load_correction_records,
    load_recorded_watchers,
)

CARE = rcw.CARE_SCENARIO_ID
REAL_POINTS = [s for s in CHECKPOINTS[CARE] if any(f"T{label}:" in s for label in rcw.WATCHER_LABELS)]
FIXED_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
SENTINEL_KEY = "sentinel-key-never-logged-xyz"


class QuietProvider:
    mode = "live"
    model_id = WATCHER_MODEL_ID

    def __init__(self):
        self.calls = 0
        self.seen_max_tokens = []

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        self.seen_max_tokens.append(kwargs.get("max_tokens"))
        return {"text": '{"observations": []}', "answered_model": self.model_id,
                "requested_model": self.model_id, "mode": "live"}


class FailOnceProvider(QuietProvider):
    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {"text": "not json", "answered_model": self.model_id,
                    "requested_model": self.model_id, "mode": "live"}
        return {"text": '{"observations": []}', "answered_model": self.model_id,
                "requested_model": self.model_id, "mode": "live"}


class AlwaysBadProvider(QuietProvider):
    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return {"text": "not json", "answered_model": self.model_id,
                "requested_model": self.model_id, "mode": "live"}


def _env():
    return {"MODEL_API_KEY": SENTINEL_KEY}


def _run(argv, tmp_path, provider, monkeypatch=None, checkpoints=None):
    lines = []
    watchers = tmp_path / "watchers"
    corrections = tmp_path / "corrections"
    args = [*argv, "--watchers-dir", str(watchers), "--corrections-dir", str(corrections),
            "--date", "2026-10-30"]
    if checkpoints is not None and monkeypatch is not None:
        monkeypatch.setattr(rcw, "CHECKPOINTS", {CARE: tuple(checkpoints)})
    rc = rcw.main(args, provider=provider, env=_env(), out=lines.append, now=FIXED_NOW)
    return rc, "\n".join(lines), watchers, corrections


def test_dry_run_makes_zero_calls(tmp_path):
    provider = QuietProvider()
    rc, text, watchers, _ = _run([], tmp_path, provider)
    assert rc == 0
    assert provider.calls == 0
    assert len(REAL_POINTS) == 8
    for point in REAL_POINTS:
        assert point in text
    assert "up to 16" in text
    assert "dry run" in text
    assert not watchers.exists() or list(watchers.glob("*.json")) == []


def test_live_without_cap_or_snapshot_refuses(tmp_path):
    assert _run(["--live", "--code-snapshot", "abc"], tmp_path, QuietProvider())[0] == 2
    assert _run(["--live", "--max-calls", "16"], tmp_path, QuietProvider())[0] == 2


def test_cap_below_plan_refuses_before_any_call(tmp_path):
    provider = QuietProvider()
    rc, text, watchers, _ = _run(
        ["--live", "--max-calls", "15", "--code-snapshot", "abc"], tmp_path, provider)
    assert rc == 2
    assert provider.calls == 0
    assert "planned 16 calls exceed --max-calls 15" in text
    assert not watchers.exists() or list(watchers.glob("*.json")) == []


def test_failed_first_attempt_gets_exactly_one_revision(tmp_path, monkeypatch):
    provider = FailOnceProvider()
    rc, text, watchers, corrections = _run(
        ["--live", "--max-calls", "2", "--code-snapshot", "s"],
        tmp_path, provider, monkeypatch, checkpoints=REAL_POINTS[:1])
    assert rc == 0
    assert provider.calls == 2
    assert "model calls made: 2" in text
    payload = json.loads(next(watchers.glob("*.json")).read_text(encoding="utf-8"))
    assert payload["watchers"][0]["final_result"] == "corrected and verified"
    assert load_correction_records(corrections) != []


def test_files_load_and_serve_at_matching_checkpoint(tmp_path, monkeypatch):
    provider = QuietProvider()
    rc, text, watchers, _ = _run(
        ["--live", "--max-calls", "16", "--code-snapshot", "test-snap"], tmp_path, provider)
    assert rc == 0
    assert provider.calls == 8
    entries = load_recorded_watchers(watchers)
    assert len(entries) == 8
    first = entries[0]["entry"]
    assert first["scenario_id"] == CARE
    assert first["code_snapshot"] == "test-snap"
    assert first["output"] == {"observations": []}
    match = find_recorded_watcher(
        entries, CARE, first["evaluated_at_utc"], first["input_revision"], first["laws_version"])
    assert match is not None
    assert SENTINEL_KEY not in text
    for path in watchers.glob("*.json"):
        assert SENTINEL_KEY not in path.read_text(encoding="utf-8")
    from aria_home.app import create_app
    from aria_home.scenario import load_scenario

    scn = load_scenario(rcw.SCENARIOS_DIR / CARE)
    at = datetime.fromisoformat(REAL_POINTS[0])
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(watchers))
    client = create_app().test_client()
    body = client.get("/api/watcher", query_string={"scenario": CARE, "at": at.isoformat()}).get_json()
    assert body["provenance"]["model_id"] == WATCHER_MODEL_ID
    assert body["provenance"]["validation"]["passed"] is True
    assert body["model_observations"] == []
    assert SENTINEL_KEY not in json.dumps(body)


def test_failed_run_recorded_never_lowers_risk(tmp_path, monkeypatch):
    provider = AlwaysBadProvider()
    rc, _, watchers, _ = _run(
        ["--live", "--max-calls", "2", "--code-snapshot", "s"],
        tmp_path, provider, monkeypatch, checkpoints=REAL_POINTS[:1])
    assert rc == 0
    assert provider.calls == 2
    entries = load_recorded_watchers(watchers)
    assert entries[0]["entry"]["final_result"] == "rejected"
    assert entries[0]["entry"]["failed_checks"]
    from aria_home.scenario import load_scenario
    from aria_home.watcher import public_watcher

    scn = load_scenario(rcw.SCENARIOS_DIR / CARE)
    viewed = public_watcher(scn, datetime.fromisoformat(REAL_POINTS[0]), entries=entries)
    assert viewed["model_observations"] == []
    assert viewed["provenance"]["validation"]["passed"] is False


def test_timeout_and_budget_reach_fake_seams(tmp_path, monkeypatch):
    provider = QuietProvider()
    rc, _, _, _ = _run(
        ["--live", "--max-calls", "2", "--code-snapshot", "s"],
        tmp_path, provider, monkeypatch, checkpoints=REAL_POINTS[:1])
    assert rc == 0
    assert provider.timeout_s == 180.0
    assert provider.max_tokens == 4096
    override = QuietProvider()
    rc, _, _, _ = _run(
        ["--live", "--max-calls", "2", "--code-snapshot", "s",
         "--timeout-s", "42", "--max-tokens", "1024"],
        tmp_path, override, monkeypatch, checkpoints=REAL_POINTS[:1])
    assert rc == 0
    assert override.timeout_s == 42.0
    assert override.max_tokens == 1024


def test_second_run_never_overwrites(tmp_path):
    provider = QuietProvider()
    args = ["--live", "--max-calls", "16", "--code-snapshot", "s"]
    _run(args, tmp_path, provider)
    _run(args, tmp_path, provider)
    names = sorted(p.name for p in (tmp_path / "watchers").glob("*.json"))
    assert names == ["watchers-care-2026-10-30-1.json", "watchers-care-2026-10-30.json"]


def test_only_missing_skips_recorded_checkpoint(tmp_path, monkeypatch):
    provider = QuietProvider()
    _run(["--live", "--max-calls", "16", "--code-snapshot", "s"], tmp_path, provider)
    again = QuietProvider()
    lines = []
    rc = rcw.main(
        ["--live", "--only-missing", "--max-calls", "16", "--code-snapshot", "s",
         "--watchers-dir", str(tmp_path / "watchers"),
         "--corrections-dir", str(tmp_path / "corrections"),
         "--date", "2026-10-30"],
        provider=again, env=_env(), out=lines.append, now=FIXED_NOW)
    assert rc == 0
    assert again.calls == 0
    assert "model calls made: 0" in "\n".join(lines)


def _seed_care_watchers(watchers_dir, unreadable=(), real_rejections=()):
    scenario = load_scenario(rcw.SCENARIOS_DIR / CARE)
    items = [item for item in rcw._plan(scenario)]
    recorded = []
    for index, item in enumerate(items):
        identity = item["identity"]
        if index in unreadable:
            failed = ["invalid JSON: Expecting value: line 1 column 1 (char 0)"]
            status = "rejected"
        elif index in real_rejections:
            failed = ["observation value does not match evidence room-care-1630: 71.0 != 52.0 (tolerance 0.15)"]
            status = "rejected"
        else:
            failed, status = [], "confirmed"
        recorded.append({
            "scenario_id": CARE,
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "laws_version": identity["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION,
            "model_id": WATCHER_MODEL_ID,
            "provider_route": "meta live via Meta Model API (messages)",
            "code_snapshot": "seed",
            "recorded_at": "2026-10-30T19:03:25.476706+00:00",
            "status": status,
            "final_result": status,
            "failed_checks": failed,
            "output": {"observations": []},
        })
    watchers_dir.mkdir(parents=True, exist_ok=True)
    (watchers_dir / "watchers-care-2026-10-30.json").write_text(json.dumps({"watchers": recorded}), encoding="utf-8")
    return items


def test_only_missing_dry_run_rerecords_only_unreadable(tmp_path):
    _seed_care_watchers(tmp_path / "watchers", unreadable=(1, 2))
    provider = QuietProvider()
    lines = []
    rc = rcw.main(
        ["--only-missing", "--watchers-dir", str(tmp_path / "watchers"),
         "--corrections-dir", str(tmp_path / "corrections"), "--date", "2026-10-30"],
        provider=provider, env=_env(), out=lines.append, now=FIXED_NOW)
    text = "\n".join(lines)
    assert rc == 0
    assert provider.calls == 0
    assert "planned calls: up to 4 (2 first + up to 2 revisions)" in text
    assert "only-missing: skipped 6 recorded watcher(s); 2 checkpoint(s) still needed" in text


def test_only_missing_rerecords_thinking_only_rejection(tmp_path, monkeypatch):
    _seed_care_watchers(tmp_path / "watchers")
    path = tmp_path / "watchers" / "watchers-care-2026-10-30.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["watchers"][0]["status"] = payload["watchers"][0]["final_result"] = "rejected"
    payload["watchers"][0]["failed_checks"] = [NO_TEXT_REASON]
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(rcw, "CHECKPOINTS", {CARE: (REAL_POINTS[0],)})
    provider = QuietProvider()
    lines = []
    rc = rcw.main(
        ["--only-missing", "--watchers-dir", str(tmp_path / "watchers"),
         "--corrections-dir", str(tmp_path / "corrections"), "--date", "2026-10-30"],
        provider=provider, env=_env(), out=lines.append, now=FIXED_NOW)
    text = "\n".join(lines)
    assert rc == 0
    assert provider.calls == 0
    assert "planned calls: up to 2 (1 first + up to 1 revisions)" in text
    assert "only-missing: skipped 0 recorded watcher(s); 1 checkpoint(s) still needed" in text


def test_only_missing_keeps_real_code_check_rejection(tmp_path, monkeypatch):
    _seed_care_watchers(tmp_path / "watchers", real_rejections=(0,))
    monkeypatch.setattr(rcw, "CHECKPOINTS", {CARE: (REAL_POINTS[0],)})
    provider = QuietProvider()
    lines = []
    rc = rcw.main(
        ["--only-missing", "--watchers-dir", str(tmp_path / "watchers"),
         "--corrections-dir", str(tmp_path / "corrections"), "--date", "2026-10-30"],
        provider=provider, env=_env(), out=lines.append, now=FIXED_NOW)
    text = "\n".join(lines)
    assert rc == 0
    assert provider.calls == 0
    assert "planned calls: up to 0 (0 first + up to 0 revisions)" in text
    assert "only-missing: skipped 1 recorded watcher(s); 0 checkpoint(s) still needed" in text
