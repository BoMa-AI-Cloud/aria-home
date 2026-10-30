"""The running version reported by /api/health (release process stage 12)."""
from aria_home.app import create_app, release_version


def test_env_wins_over_file(monkeypatch, tmp_path):
    (tmp_path / "RELEASE_COMMIT").write_text("abcdef1234567890abcdef12\n")
    monkeypatch.setenv("ARIA_HOME_RELEASE_COMMIT", "deadbeef1234567")
    assert release_version(base_dir=tmp_path) == {"commit": "deadbeef1234567", "source": "env"}


def test_file_used_when_env_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("ARIA_HOME_RELEASE_COMMIT", raising=False)
    (tmp_path / "RELEASE_COMMIT").write_text("  abcdef1234567\nsecond line\n")
    assert release_version(base_dir=tmp_path) == {"commit": "abcdef1234567", "source": "file"}


def test_neither_returns_unknown(monkeypatch, tmp_path):
    monkeypatch.delenv("ARIA_HOME_RELEASE_COMMIT", raising=False)
    assert release_version(base_dir=tmp_path) == {"commit": "unknown", "source": "not stamped"}


def test_invalid_env_value_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIA_HOME_RELEASE_COMMIT", "abc; SECRET=1")
    (tmp_path / "RELEASE_COMMIT").write_text("abc123def4567\n")
    assert release_version(base_dir=tmp_path) == {"commit": "abc123def4567", "source": "file"}
    (tmp_path / "RELEASE_COMMIT").unlink()
    assert release_version(base_dir=tmp_path) == {"commit": "unknown", "source": "not stamped"}


def test_health_endpoint_version(monkeypatch):
    sha = "a" * 40
    monkeypatch.setenv("ARIA_HOME_RELEASE_COMMIT", sha)
    resp = create_app().test_client().get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["version"] == {"commit": sha, "source": "env"}
