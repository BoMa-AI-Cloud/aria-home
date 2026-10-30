"""Tests for the seven process laws in backend/laws/laws.json.

Each law names its enforcement check: an automated pytest id, or the words
"checked at review" for the one human-gated release step.
"""

import re
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.laws import load_laws

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
BUILD_LOG = DOCS / "build-log"


def _backtick_paths(text):
    return re.findall(r"`([^`]+)`", text)


def _test_path(token):
    token = token.strip()
    for prefix in ("backend/", "frontend/"):
        if token.startswith(prefix):
            return ROOT / token
    return None


def _repaired_audit3_rows():
    text = (DOCS / "audit-3.md").read_text(encoding="utf-8")
    table = text.split("## Follow-ups")[0]
    return [line for line in table.splitlines() if line.startswith("| ") and not line.startswith("| #")]


def _repaired_audit4_rows():
    text = (DOCS / "audit-4.md").read_text(encoding="utf-8")
    return [line for line in text.splitlines()
            if line.startswith("| ") and not line.startswith("| #") and "repaired" in line]


def test_audit_rows_name_existing_tests():
    missing = []
    for row in _repaired_audit3_rows() + _repaired_audit4_rows():
        named = [_test_path(t) for t in _backtick_paths(row)]
        named = [p for p in named if p is not None]
        assert named, f"repaired audit row names no test file: {row[:80]}"
        for path in named:
            if not path.exists():
                missing.append(f"{path.relative_to(ROOT)} (in {row[:60]})")
    assert not missing, "repaired audit rows naming files that do not exist:\n" + "\n".join(missing)


def test_audit4_rows_have_red_proofs():
    proofs_path = DOCS / "red-proofs.md"
    if not proofs_path.exists():
        pytest.xfail("red-proofs pending")
    proofs = proofs_path.read_text(encoding="utf-8")
    rows = _repaired_audit4_rows()
    assert rows
    unmatched = [row for row in rows
                 if not any(f"audit-4 row {n}" in proofs or f"finding {n}" in proofs
                            for n in re.findall(r"^\|\s*(\d+)", row))]
    assert not unmatched, f"{len(unmatched)} repaired audit-4 rows lack a red-proofs entry"


def test_build_log_tasks_have_prompts():
    readme = (BUILD_LOG / "README.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"\[prompt\]\(([^)]+)\)", readme))
    assert linked, "build-log README links no prompt files"
    for name in sorted(linked):
        assert (BUILD_LOG / name).exists(), f"build-log README links missing prompt file {name}"
    on_disk = {p.name for p in BUILD_LOG.glob("*.prompt.md")}
    unlisted = sorted(on_disk - linked)
    assert not unlisted, f"prompt files not listed in build-log README: {unlisted}"


def test_env_example_has_no_live_values():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if "LIVE" in name or "ENABLED" in name:
            assert value.strip() in ("", "0"), f".env.example sets a live value: {stripped}"


def test_ci_enables_no_live_flags():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    enabled = [line.strip() for line in text.splitlines()
               if re.search(r"ARIA_HOME_\w*(LIVE|ENABLED)\w*\s*:\s*[\"']?1[\"']?", line)]
    assert not enabled, f"CI enables live flags: {enabled}"


def test_health_reports_version():
    body = create_app().test_client().get("/api/health").get_json()
    assert body.get("version", {}).get("commit"), "/api/health reports the running version"


def test_process_laws_structure():
    registry = load_laws()
    assert len(registry["process_laws"]) == 7
    for law in registry["process_laws"]:
        assert law["id"] and law["statement"] and law["stage"]
        check = law["check"]
        if check != "checked at review":
            node_id = check.split("::", 1)[1]
            assert (ROOT / check.split("::")[0]).exists(), f"process law {law['id']} names a missing test file"
            assert re.match(r"^test_[A-Za-z0-9_]+$", node_id), f"process law {law['id']} names a bad test id"


