"""Small authenticated-local IPC boundary between gateway and control daemon."""

import json
import os
import socket
import socketserver
import stat
from pathlib import Path
from typing import Any

from piblindhub.controller import BlindController
from piblindhub.domain import CommandSource, CommandType, ControlCommand

MAX_MESSAGE_BYTES = 64 * 1024


class ControlUnavailable(ConnectionError):
    pass


class ControlRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
        if len(raw) > MAX_MESSAGE_BYTES:
            self._reply({"ok": False, "error": "request_too_large"})
            return
        try:
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            response = self.server.dispatch(request)  # type: ignore[attr-defined]
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
            response = {"ok": False, "error": "invalid_request", "detail": str(exc)}
        except Exception:
            response = {"ok": False, "error": "internal_control_error"}
        self._reply(response)

    def _reply(self, response: dict[str, Any]) -> None:
        self.wfile.write(json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n")


class _PortableUnixStreamServer(socketserver.TCPServer):
    """Unix stream server compatible with Python versions lacking the stdlib alias."""

    address_family = getattr(socket, "AF_UNIX", socket.AF_INET)


class UnixControlServer(socketserver.ThreadingMixIn, _PortableUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path: str, controller: BlindController) -> None:
        if not hasattr(socket, "AF_UNIX"):
            raise RuntimeError("Unix domain sockets are unavailable on this platform")
        self.socket_path = Path(socket_path)
        self.controller = controller
        self._prepare_socket_path()
        # TCPServer's types only model IP tuples, but its implementation supports
        # this AF_UNIX string address when address_family is overridden.
        super().__init__(str(self.socket_path), ControlRequestHandler)  # type: ignore[arg-type]
        os.chmod(self.socket_path, 0o660)

    def _prepare_socket_path(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.socket_path.exists() and not self.socket_path.is_symlink():
            return
        mode = self.socket_path.lstat().st_mode
        if not stat.S_ISSOCK(mode):
            raise RuntimeError(f"Refusing to replace non-socket path: {self.socket_path}")
        self.socket_path.unlink()

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        operation = request.get("operation")
        if operation == "status":
            return {"ok": True, "data": self.controller.get_status().to_dict()}
        if operation == "health":
            return {"ok": True, "data": self.controller.get_health()}
        if operation == "command_status":
            command_id = str(request.get("command_id", ""))
            result = self.controller.get_command_result(command_id)
            if result is None:
                return {"ok": False, "error": "command_not_found"}
            return {"ok": True, "data": result.to_dict()}
        if operation == "events":
            return {
                "ok": True,
                "data": self.controller.repository.recent_events(int(request.get("limit", 100))),
            }
        if operation == "command":
            command_type = CommandType(str(request["command"]))
            source_value = str(request.get("source", CommandSource.API.value))
            if source_value not in {CommandSource.API.value, CommandSource.MQTT.value}:
                raise ValueError("IPC command source must be api or mqtt")
            position = request.get("position")
            command = ControlCommand(
                type=command_type,
                source=CommandSource(source_value),
                position=float(position) if position is not None else None,
            )
            result = self.controller.submit(command)
            return {"ok": True, "data": result.to_dict()}
        raise ValueError("unknown operation")

    def server_close(self) -> None:
        super().server_close()
        try:
            if self.socket_path.exists() and stat.S_ISSOCK(self.socket_path.lstat().st_mode):
                self.socket_path.unlink()
        except FileNotFoundError:
            pass


class ControlClient:
    def __init__(self, socket_path: str, timeout_seconds: float = 2.0) -> None:
        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(socket, "AF_UNIX"):
            raise ControlUnavailable("Unix domain sockets are unavailable on this platform")
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(self.timeout_seconds)
        try:
            client.connect(self.socket_path)
            client.sendall(json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")
            response = self._read_line(client)
        except (OSError, socket.timeout) as exc:
            raise ControlUnavailable("Control daemon is unavailable") from exc
        finally:
            client.close()
        try:
            decoded = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ControlUnavailable("Control daemon returned an invalid response") from exc
        if not isinstance(decoded, dict):
            raise ControlUnavailable("Control daemon returned a non-object response")
        return decoded

    def _read_line(self, client: socket.socket) -> bytes:
        chunks = []
        length = 0
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
            if length > MAX_MESSAGE_BYTES:
                raise ControlUnavailable("Control daemon response is too large")
            if b"\n" in chunk:
                break
        return b"".join(chunks).split(b"\n", 1)[0]
