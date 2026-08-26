import json
from hashlib import sha256

import pytest

from piblindhub.config import AppConfig, ConfigurationError


def valid_mapping():
    return {
        "hardware": {"backend": "fake"},
        "paths": {"state_database": "state.db", "control_socket": "control.sock"},
        "api": {"api_token_sha256": sha256(b"test-token").hexdigest()},
    }


def test_configuration_rejects_duplicate_gpio_pins():
    raw = valid_mapping()
    raw["hardware"].update({"motor_up_pin": 23, "motor_down_pin": 23})

    with pytest.raises(ConfigurationError, match="unique"):
        AppConfig.from_mapping(raw)


def test_configuration_rejects_unknown_fields():
    raw = valid_mapping()
    raw["hardware"]["surprise"] = True

    with pytest.raises(ConfigurationError, match="Unknown"):
        AppConfig.from_mapping(raw)


def test_api_hash_can_come_from_environment(monkeypatch):
    digest = sha256(b"environment-token").hexdigest()
    monkeypatch.setenv("PIBLINDHUB_API_TOKEN_SHA256", digest.upper())
    config = AppConfig.from_mapping(valid_mapping())

    assert config.api.resolved_token_hash() == digest


def test_load_requires_an_object(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="root"):
        AppConfig.load(str(path))


def test_mqtt_password_is_environment_only(monkeypatch):
    raw = valid_mapping()
    raw["mqtt"] = {
        "enabled": True,
        "password_environment": "PIBLINDHUB_MQTT_PASSWORD",
    }
    monkeypatch.setenv("PIBLINDHUB_MQTT_PASSWORD", "private")

    config = AppConfig.from_mapping(raw)

    assert config.mqtt.resolved_password() == "private"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"motor_up_pin": 28}, "BCM"),
        ({"backend": "unknown"}, "backend"),
        ({"switch_dead_time_ms": 99}, "switch_dead_time"),
        ({"max_movement_seconds": 0.5}, "max_movement"),
        ({"full_travel_seconds": 0.5}, "full_travel"),
        ({"poll_interval_ms": 5}, "poll_interval"),
    ],
)
def test_invalid_hardware_ranges_are_rejected(values, message):
    raw = valid_mapping()
    raw["hardware"].update(values)

    with pytest.raises(ConfigurationError, match=message):
        AppConfig.from_mapping(raw)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"port": 0}, "api.port"),
        ({"api_token_sha256": "not-a-digest"}, "SHA-256"),
        ({"tls_certificate": "cert.pem"}, "configured together"),
    ],
)
def test_invalid_api_configuration_is_rejected(values, message):
    raw = valid_mapping()
    raw["api"].update(values)

    with pytest.raises(ConfigurationError, match=message):
        AppConfig.from_mapping(raw)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"port": 0}, "mqtt.port"),
        ({"host": ""}, "host"),
        ({"client_id": "spaces are invalid"}, "client_id"),
        ({"base_topic": "/leading"}, "base_topic"),
        ({"password_environment": "lowercase"}, "password_environment"),
    ],
)
def test_invalid_mqtt_configuration_is_rejected(values, message):
    raw = valid_mapping()
    raw["mqtt"] = values

    with pytest.raises(ConfigurationError, match=message):
        AppConfig.from_mapping(raw)
