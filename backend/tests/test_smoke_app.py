import os

from aria_home.app import create_app


def test_smoke_page_contract(monkeypatch):
    secrets = [
        value
        for key, value in os.environ.items()
        if value
        and len(value) >= 8
        and ("KEY" in key.upper() or key in ("api_key", "key"))
    ]
    for var in (
        "ARIA_HOME_PROVIDER_URL",
        "ARIA_HOME_BASE_URL",
        "ARIA_HOME_MODEL_ID",
        "MODEL_API_KEY",
        "api_key",
        "key",
        "ARIA_HOME_MODEL_ENABLED",
    ):
        monkeypatch.delenv(var, raising=False)

    client = create_app().test_client()
    health = client.get("/api/health")
    sources = client.get("/api/sources?scenario=demo_v1")
    provider = client.get("/api/provider")

    assert health.status_code == 200
    assert sources.status_code == 200
    assert provider.status_code == 200

    health_body = health.get_json()
    sources_body = sources.get_json()
    provider_body = provider.get_json()

    assert health_body["data_mode"] == "synthetic"
    assert sources_body["data_mode"] == "synthetic"
    assert len(sources_body["sources"]) == 5
    assert {s["source"] for s in sources_body["sources"]} == {
        "calendar",
        "thermostat",
        "electrical",
        "weather",
        "human_report",
    }
    assert provider_body["mode"] == "mock"
    assert provider_body["key_present"] is False

    combined = (
        health.get_data(as_text=True)
        + sources.get_data(as_text=True)
        + provider.get_data(as_text=True)
    )
    for secret in secrets:
        assert secret not in combined
