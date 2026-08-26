"""Optional MQTT adapter; all motor commands still cross the local IPC boundary."""

import argparse
import json
import logging
import signal
import threading
from typing import Any, Optional

from piblindhub.config import AppConfig, ConfigurationError
from piblindhub.domain import CommandType
from piblindhub.ipc import ControlClient, ControlUnavailable

logger = logging.getLogger(__name__)
ALLOWED_COMMANDS = {
    CommandType.MOVE_UP.value,
    CommandType.MOVE_DOWN.value,
    CommandType.STOP.value,
}


class MqttBridge:
    def __init__(self, config: AppConfig, client: Any = None) -> None:
        if not config.mqtt.enabled:
            raise ConfigurationError("MQTT bridge is disabled in configuration")
        self.config = config
        self.control = ControlClient(config.paths.control_socket)
        self.stop_event = threading.Event()
        self.client = client or self._new_client()
        self.command_topic = f"{config.mqtt.base_topic}/command"
        self.status_topic = f"{config.mqtt.base_topic}/status"
        self.availability_topic = f"{config.mqtt.base_topic}/availability"

    def _new_client(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise ConfigurationError("Install the 'mqtt' extra to enable MQTT") from exc

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.config.mqtt.client_id,
            protocol=mqtt.MQTTv5,
        )
        password = self.config.mqtt.resolved_password()
        if self.config.mqtt.username:
            if self.config.mqtt.password_environment and password is None:
                raise ConfigurationError(
                    "MQTT password environment variable is configured but unavailable"
                )
            client.username_pw_set(self.config.mqtt.username, password)
        if self.config.mqtt.tls:
            client.tls_set(ca_certs=self.config.mqtt.ca_certificate)
        return client

    def configure(self) -> None:
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.will_set(self.availability_topic, "offline", qos=1, retain=True)
        reconnect = getattr(self.client, "reconnect_delay_set", None)
        if reconnect:
            reconnect(min_delay=1, max_delay=60)

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if int(reason_code) != 0:
            logger.error("MQTT connection rejected: %s", reason_code)
            return
        client.subscribe(self.command_topic, qos=1)
        client.publish(self.availability_topic, "online", qos=1, retain=True)
        self.publish_status()

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties) -> None:
        if not self.stop_event.is_set():
            logger.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, client, _userdata, message) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be an object")
            command = str(payload.get("command", ""))
            if command not in ALLOWED_COMMANDS:
                raise ValueError("command must be move_up, move_down, or stop")
            response = self.control.request(
                {"operation": "command", "command": command, "source": "mqtt"}
            )
            if not response.get("ok"):
                raise RuntimeError(str(response.get("error", "control_request_failed")))
            acknowledgement: dict[str, Any] = {
                "accepted": True,
                "command": command,
                "command_id": response["data"]["command_id"],
                "lifecycle": response["data"]["lifecycle"],
            }
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
            acknowledgement = {"accepted": False, "error": str(exc)}
        except ControlUnavailable:
            acknowledgement = {"accepted": False, "error": "control_daemon_unavailable"}
        client.publish(
            f"{self.config.mqtt.base_topic}/command_result",
            json.dumps(acknowledgement, separators=(",", ":")),
            qos=1,
            retain=False,
        )
        self.publish_status()

    def publish_status(self) -> None:
        try:
            response = self.control.request({"operation": "status"})
            if not response.get("ok"):
                return
            self.client.publish(
                self.status_topic,
                json.dumps(response["data"], separators=(",", ":")),
                qos=1,
                retain=True,
            )
        except ControlUnavailable:
            logger.warning("Cannot publish status: control daemon unavailable")

    def run(self) -> None:
        self.configure()
        self.client.connect(self.config.mqtt.host, self.config.mqtt.port, keepalive=30)
        self.client.loop_start()
        try:
            while not self.stop_event.wait(5.0):
                self.publish_status()
        finally:
            self.client.publish(self.availability_topic, "offline", qos=1, retain=True)
            self.client.disconnect()
            self.client.loop_stop()

    def stop(self) -> None:
        self.stop_event.set()


def run(config_path: Optional[str] = None) -> int:
    config = AppConfig.load(config_path)
    try:
        bridge = MqttBridge(config)
    except ConfigurationError:
        logger.exception("MQTT configuration is invalid")
        return 2

    def handle_signal(_signum, _frame) -> None:
        bridge.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    try:
        bridge.run()
        return 0
    except Exception:
        logger.exception("MQTT bridge failed")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="PiBlindHub optional MQTT bridge")
    parser.add_argument("--config", help="Path to private runtime config.json")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    raise SystemExit(run(args.config))


if __name__ == "__main__":
    main()
