"""Strict JSON configuration for PiBlindHub."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

TOKEN_HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class HardwareConfig:
    backend: str = "raspberry"
    motor_up_pin: int = 23
    motor_down_pin: int = 24
    button_up_pin: int = 25
    button_down_pin: int = 27
    relay_active_high: bool = True
    button_active_high: bool = True
    switch_dead_time_ms: int = 300
    max_movement_seconds: float = 30.0
    full_travel_seconds: float = 30.0
    poll_interval_ms: int = 20

    def validate(self) -> None:
        pins = [
            self.motor_up_pin,
            self.motor_down_pin,
            self.button_up_pin,
            self.button_down_pin,
        ]
        if len(set(pins)) != len(pins):
            raise ConfigurationError("GPIO pins must be unique")
        if any(pin < 0 or pin > 27 for pin in pins):
            raise ConfigurationError("GPIO pins must use valid BCM numbers between 0 and 27")
        if self.backend not in {"raspberry", "fake"}:
            raise ConfigurationError("hardware.backend must be 'raspberry' or 'fake'")
        if not 100 <= self.switch_dead_time_ms <= 5000:
            raise ConfigurationError("switch_dead_time_ms must be between 100 and 5000")
        if not 1.0 <= self.max_movement_seconds <= 120.0:
            raise ConfigurationError("max_movement_seconds must be between 1 and 120")
        if not 1.0 <= self.full_travel_seconds <= 300.0:
            raise ConfigurationError("full_travel_seconds must be between 1 and 300")
        if not 10 <= self.poll_interval_ms <= 250:
            raise ConfigurationError("poll_interval_ms must be between 10 and 250")


@dataclass(frozen=True)
class PathsConfig:
    state_database: str = "/var/lib/piblindhub/state.db"
    control_socket: str = "/run/piblindhub/control.sock"


@dataclass(frozen=True)
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    api_token_sha256: Optional[str] = None
    tls_certificate: Optional[str] = None
    tls_private_key: Optional[str] = None

    def validate(self, require_token: bool = False) -> None:
        if not 1 <= self.port <= 65535:
            raise ConfigurationError("api.port must be between 1 and 65535")
        token_hash = self.resolved_token_hash()
        if require_token and not token_hash:
            raise ConfigurationError(
                "An API token hash is required via PIBLINDHUB_API_TOKEN_SHA256 or configuration"
            )
        if token_hash and not TOKEN_HASH_RE.fullmatch(token_hash):
            raise ConfigurationError("API token hash must be a 64-character SHA-256 hex digest")
        if bool(self.tls_certificate) != bool(self.tls_private_key):
            raise ConfigurationError("TLS certificate and private key must be configured together")

    def resolved_token_hash(self) -> Optional[str]:
        value = os.environ.get("PIBLINDHUB_API_TOKEN_SHA256") or self.api_token_sha256
        return value.lower() if value else None


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 8883
    client_id: str = "piblindhub"
    base_topic: str = "piblindhub"
    username: Optional[str] = None
    password_environment: Optional[str] = None
    tls: bool = True
    ca_certificate: Optional[str] = None

    def validate(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ConfigurationError("mqtt.port must be between 1 and 65535")
        if not self.host.strip():
            raise ConfigurationError("mqtt.host cannot be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.client_id):
            raise ConfigurationError("mqtt.client_id contains unsupported characters")
        if not re.fullmatch(r"[A-Za-z0-9/_-]{1,128}", self.base_topic):
            raise ConfigurationError("mqtt.base_topic contains unsupported characters")
        if self.base_topic.startswith("/") or self.base_topic.endswith("/"):
            raise ConfigurationError("mqtt.base_topic cannot start or end with '/'")
        if self.password_environment and not re.fullmatch(
            r"[A-Z][A-Z0-9_]{1,127}", self.password_environment
        ):
            raise ConfigurationError("mqtt.password_environment must name an environment variable")

    def resolved_password(self) -> Optional[str]:
        if not self.password_environment:
            return None
        return os.environ.get(self.password_environment)


@dataclass(frozen=True)
class AppConfig:
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        config_path = Path(
            path or os.environ.get("PIBLINDHUB_CONFIG", "/etc/piblindhub/config.json")
        )
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Cannot load configuration: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigurationError("Configuration root must be a JSON object")
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AppConfig":
        try:
            config = cls(
                hardware=HardwareConfig(**raw.get("hardware", {})),
                paths=PathsConfig(**raw.get("paths", {})),
                api=ApiConfig(**raw.get("api", {})),
                mqtt=MqttConfig(**raw.get("mqtt", {})),
            )
        except TypeError as exc:
            raise ConfigurationError(f"Unknown or invalid configuration field: {exc}") from exc
        config.hardware.validate()
        config.api.validate(require_token=False)
        config.mqtt.validate()
        return config
