"""Tests for the Render blueprint (hosted public demo)."""
import re
from pathlib import Path

from aria_home import public_demo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RENDER_YAML = REPO_ROOT / "render.yaml"
REQUIREMENTS_LOCK = REPO_ROOT / "backend" / "requirements.lock"

FORBIDDEN_NAME_PARTS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def _blueprint():
    return RENDER_YAML.read_text(encoding="utf-8")


def _start_command(text):
    match = re.search(r"^\s*startCommand:\s*(.+?)\s*$", text, re.M)
    assert match is not None
    return match.group(1)


def _env_keys(text):
    section = text.split("envVars:", 1)[1]
    return re.findall(r"key:\s*(\S+)", section)


def test_plan_is_starter_and_deploys_are_manual():
    text = _blueprint()
    assert re.search(r"^\s*plan:\s*starter\s*$", text, re.M) is not None
    assert re.search(r"^\s*autoDeploy:\s*false\s*$", text, re.M) is not None


def test_public_demo_flag_and_health_path():
    text = _blueprint()
    assert re.search(r"key:\s*ARIA_HOME_PUBLIC_DEMO\s*\n\s*value:\s*\"1\"", text) is not None
    assert re.search(r"^\s*healthCheckPath:\s*/api/health\s*$", text, re.M) is not None


def test_start_command_uses_waitress_factory_and_port():
    command = _start_command(_blueprint())
    assert "waitress-serve" in command
    assert "--call aria_home.app:create_app" in command
    assert "$PORT" in command


def test_no_secrets_or_live_flags_in_env():
    keys = _env_keys(_blueprint())
    assert keys
    for key in keys:
        upper = key.upper()
        assert not any(part in upper for part in FORBIDDEN_NAME_PARTS), key
        assert key not in public_demo.LIVE_FLAGS, key


def test_requirements_lock_pins_waitress():
    lock = REQUIREMENTS_LOCK.read_text(encoding="utf-8")
    assert re.search(r"^waitress==3\.0\.2\s*$", lock, re.M) is not None
