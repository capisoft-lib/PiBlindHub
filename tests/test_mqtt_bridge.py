import json
from types import SimpleNamespace

import pytest
from piblindhub import mqtt_bridge
from piblindhub.config import AppConfig, ConfigurationError
from piblindhub.ipc import ControlUnavailable
from piblindhub.mqtt_bridge import MqttBridge


class FakeMqttClient:
    def __init__(self):
        self.published = []
        self.subscribed = []

    def publish(self, topic, payload, qos, retain):
        self.published.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos):
        self.subscribed.append((topic, qos))

    def will_set(self, *_args, **_kwargs):
        pass

    def reconnect_delay_set(self, **_kwargs):
        pass

    def connect(self, host, port, keepalive):
        self.connection = (host, port, keepalive)

    def loop_start(self):
        self.loop_started = True

    def disconnect(self):
        self.disconnected = True

    def loop_stop(self):
        self.loop_stopped = True


def config(tmp_path):
    return AppConfig.from_mapping(
        {
            "hardware": {"backend": "fake"},
            "paths": {
                "state_database": str(tmp_path / "state.db"),
                "control_socket": str(tmp_path / "control.sock"),
            },
            "mqtt": {"enabled": True, "tls": False},
        }
    )


def test_mqtt_command_is_validated_and_sent_through_ipc(tmp_path, monkeypatch):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)
    requests = []

    def request(payload):
        requests.append(payload)
        if payload["operation"] == "status":
            return {"ok": True, "data": {"state": "moving_up"}}
        return {
            "ok": True,
            "data": {"command_id": "mqtt-1", "lifecycle": "accepted"},
        }

    monkeypatch.setattr(bridge.control, "request", request)
    message = SimpleNamespace(payload=json.dumps({"command": "move_up"}).encode())

    bridge._on_message(client, None, message)

    assert requests[0] == {
        "operation": "command",
        "command": "move_up",
        "source": "mqtt",
    }
    result = json.loads(client.published[0][1])
    assert result["accepted"] is True


def test_mqtt_rejects_extended_commands(tmp_path, monkeypatch):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)
    monkeypatch.setattr(
        bridge.control,
        "request",
        lambda _payload: {"ok": True, "data": {"state": "idle"}},
    )
    message = SimpleNamespace(payload=b'{"command":"reset_fault"}')

    bridge._on_message(client, None, message)

    result = json.loads(client.published[0][1])
    assert result["accepted"] is False


def test_mqtt_connects_subscribes_and_publishes_availability(tmp_path, monkeypatch):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)
    monkeypatch.setattr(
        bridge.control,
        "request",
        lambda _payload: {"ok": True, "data": {"state": "idle"}},
    )
    bridge.configure()

    bridge._on_connect(client, None, None, 0, None)

    assert client.subscribed == [("piblindhub/command", 1)]
    assert ("piblindhub/availability", "online", 1, True) in client.published
    assert any(item[0] == "piblindhub/status" for item in client.published)


def test_mqtt_unavailable_control_is_reported_without_crash(tmp_path, monkeypatch):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)
    monkeypatch.setattr(
        bridge.control,
        "request",
        lambda _payload: (_ for _ in ()).throw(ControlUnavailable("offline")),
    )
    message = SimpleNamespace(payload=b'{"command":"stop"}')

    bridge._on_message(client, None, message)

    result = json.loads(client.published[0][1])
    assert result == {"accepted": False, "error": "control_daemon_unavailable"}


def test_mqtt_run_always_publishes_offline_and_disconnects(tmp_path, monkeypatch):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)
    monkeypatch.setattr(
        bridge.control,
        "request",
        lambda _payload: {"ok": True, "data": {"state": "idle"}},
    )
    bridge.stop()

    bridge.run()

    assert client.connection == ("localhost", 8883, 30)
    assert client.disconnected is True
    assert client.loop_stopped is True
    assert ("piblindhub/availability", "offline", 1, True) in client.published


def test_disabled_mqtt_cannot_be_constructed(tmp_path):
    disabled = AppConfig.from_mapping(
        {
            "hardware": {"backend": "fake"},
            "paths": {
                "state_database": str(tmp_path / "state.db"),
                "control_socket": str(tmp_path / "control.sock"),
            },
        }
    )

    with pytest.raises(ValueError, match="disabled"):
        MqttBridge(disabled, client=FakeMqttClient())


def test_mqtt_client_requires_configured_password_environment(tmp_path, monkeypatch):
    raw = {
        "hardware": {"backend": "fake"},
        "paths": {
            "state_database": str(tmp_path / "state.db"),
            "control_socket": str(tmp_path / "control.sock"),
        },
        "mqtt": {
            "enabled": True,
            "tls": False,
            "username": "automation",
            "password_environment": "PIBLINDHUB_MISSING_PASSWORD",
        },
    }
    monkeypatch.delenv("PIBLINDHUB_MISSING_PASSWORD", raising=False)

    with pytest.raises(ConfigurationError, match="unavailable"):
        MqttBridge(AppConfig.from_mapping(raw))


def test_mqtt_rejected_connection_does_not_subscribe(tmp_path):
    client = FakeMqttClient()
    bridge = MqttBridge(config(tmp_path), client=client)

    bridge._on_connect(client, None, None, 1, None)
    bridge._on_disconnect(client, None, None, 1, None)

    assert client.subscribed == []


def test_mqtt_runner_reports_disabled_configuration(tmp_path, monkeypatch):
    disabled = AppConfig.from_mapping(
        {
            "hardware": {"backend": "fake"},
            "paths": {
                "state_database": str(tmp_path / "state.db"),
                "control_socket": str(tmp_path / "control.sock"),
            },
        }
    )
    monkeypatch.setattr(mqtt_bridge.AppConfig, "load", lambda _path: disabled)

    assert mqtt_bridge.run("config.json") == 2


def test_mqtt_runner_reports_bridge_failure(tmp_path, monkeypatch):
    class FailingBridge:
        def __init__(self, _config):
            pass

        def stop(self):
            pass

        def run(self):
            raise RuntimeError("broker unavailable")

    monkeypatch.setattr(mqtt_bridge.AppConfig, "load", lambda _path: config(tmp_path))
    monkeypatch.setattr(mqtt_bridge, "MqttBridge", FailingBridge)
    monkeypatch.setattr(mqtt_bridge.signal, "signal", lambda _number, _handler: None)

    assert mqtt_bridge.run("config.json") == 1
