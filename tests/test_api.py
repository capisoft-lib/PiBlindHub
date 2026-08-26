from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from piblindhub import api
from piblindhub.api import create_app
from piblindhub.config import (
    ApiConfig,
    AppConfig,
    ConfigurationError,
    HardwareConfig,
    PathsConfig,
)
from piblindhub.ipc import ControlClient, ControlUnavailable

TOKEN = "unit-test-token"


def app_config(tmp_path):
    return AppConfig(
        hardware=HardwareConfig(backend="fake"),
        paths=PathsConfig(
            state_database=str(tmp_path / "state.db"),
            control_socket=str(tmp_path / "control.sock"),
        ),
        api=ApiConfig(api_token_sha256=sha256(TOKEN.encode()).hexdigest()),
    )


def test_api_requires_token_and_reports_acceptance_truthfully(tmp_path, monkeypatch):
    def fake_request(_self, payload):
        if payload["operation"] == "status":
            return {"ok": True, "data": {"state": "idle"}}
        if payload["operation"] == "command":
            return {
                "ok": True,
                "data": {
                    "command_id": "command-1",
                    "lifecycle": "accepted",
                    "message": "queued",
                },
            }
        raise AssertionError(payload)

    monkeypatch.setattr(ControlClient, "request", fake_request)
    client = TestClient(create_app(app_config(tmp_path)))

    assert client.get("/api/v1/status").status_code == 401
    headers = {"Authorization": f"Bearer {TOKEN}"}
    assert client.get("/api/v1/status", headers=headers).status_code == 200
    response = client.post(
        "/api/v1/commands",
        headers=headers,
        json={"command": "move_up"},
    )
    assert response.status_code == 202
    assert response.json()["lifecycle"] == "accepted"


def test_security_headers_and_no_openapi(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ControlClient,
        "request",
        lambda _self, _payload: {"ok": True, "data": {"healthy": True}},
    )
    client = TestClient(create_app(app_config(tmp_path)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/openapi.json").status_code == 404


def test_remaining_api_routes_and_unhealthy_states(tmp_path, monkeypatch):
    def fake_request(_self, payload):
        operation = payload["operation"]
        if operation == "health":
            return {"ok": True, "data": {"healthy": False}}
        if operation == "events":
            return {"ok": True, "data": [{"event_type": "test"}]}
        if operation == "command_status":
            return {"ok": False, "error": "command_not_found"}
        raise AssertionError(payload)

    monkeypatch.setattr(ControlClient, "request", fake_request)
    client = TestClient(create_app(app_config(tmp_path)))
    headers = {"Authorization": f"Bearer {TOKEN}"}

    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 503
    assert client.get("/health").json()["control_daemon"] is True
    assert client.get("/api/v1/events", headers=headers).status_code == 200
    assert client.get("/api/v1/commands/missing", headers=headers).status_code == 404
    assert (
        client.get("/api/v1/events", headers={"Authorization": "Bearer wrong"}).status_code == 401
    )


def test_health_hides_control_exception(tmp_path, monkeypatch):
    def unavailable(_self, _payload):
        raise ControlUnavailable("offline")

    monkeypatch.setattr(ControlClient, "request", unavailable)
    response = TestClient(create_app(app_config(tmp_path))).get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "control_daemon": False}


def test_api_refuses_cleartext_non_loopback_binding(tmp_path, monkeypatch):
    config = app_config(tmp_path)
    unsafe_config = AppConfig(
        hardware=config.hardware,
        paths=config.paths,
        api=ApiConfig(
            host="0.0.0.0",
            api_token_sha256=sha256(TOKEN.encode()).hexdigest(),
        ),
    )
    monkeypatch.setattr(api.AppConfig, "load", lambda _path: unsafe_config)

    with pytest.raises(ConfigurationError, match="Refusing"):
        api.run("config.json")


def test_api_run_passes_loopback_configuration_to_uvicorn(tmp_path, monkeypatch):
    config = app_config(tmp_path)
    recorded = {}
    monkeypatch.setattr(api.AppConfig, "load", lambda _path: config)
    monkeypatch.setattr(api.uvicorn, "run", lambda app, **kwargs: recorded.update(kwargs))

    api.run("config.json")

    assert recorded["host"] == "127.0.0.1"
    assert recorded["port"] == 8080
