import socket
import threading

import pytest
from conftest import wait_until
from piblindhub.config import HardwareConfig
from piblindhub.controller import BlindController
from piblindhub.domain import CommandLifecycle
from piblindhub.hardware.fake import FakeBlindHardware
from piblindhub.ipc import ControlClient, UnixControlServer
from piblindhub.persistence import StateRepository


def test_dispatch_covers_control_operations_without_network(tmp_path):
    controller = BlindController(
        HardwareConfig(backend="fake"),
        FakeBlindHardware(),
        StateRepository(str(tmp_path / "state.db")),
    )
    controller.start()
    server = object.__new__(UnixControlServer)
    server.controller = controller
    try:
        assert server.dispatch({"operation": "status"})["data"]["state"] == "idle"
        assert server.dispatch({"operation": "health"})["data"]["healthy"] is True

        accepted = server.dispatch({"operation": "command", "command": "move_up", "source": "api"})
        command_id = accepted["data"]["command_id"]

        def completed():
            result = controller.get_command_result(command_id)
            return result is not None and result.lifecycle == CommandLifecycle.COMPLETED

        wait_until(completed)
        response = server.dispatch({"operation": "command_status", "command_id": command_id})
        assert response["data"]["lifecycle"] == "completed"
        assert server.dispatch({"operation": "events", "limit": 10})["ok"] is True
        assert server.dispatch({"operation": "command_status", "command_id": "missing"}) == {
            "ok": False,
            "error": "command_not_found",
        }
        with pytest.raises(ValueError, match="source"):
            server.dispatch({"operation": "command", "command": "stop", "source": "system"})
        with pytest.raises(ValueError, match="unknown"):
            server.dispatch({"operation": "unsupported"})
    finally:
        controller.stop()


def test_control_client_fails_cleanly_without_unix_socket_support(monkeypatch):
    monkeypatch.delattr("piblindhub.ipc.socket.AF_UNIX", raising=False)

    with pytest.raises(ConnectionError, match="unavailable"):
        ControlClient("control.sock").request({"operation": "status"})


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="Unix sockets unavailable")
def test_unix_socket_exposes_status_without_exposing_hardware(tmp_path):
    socket_path = str(tmp_path / "control.sock")
    controller = BlindController(
        HardwareConfig(backend="fake"),
        FakeBlindHardware(),
        StateRepository(str(tmp_path / "state.db")),
    )
    controller.start()
    server = UnixControlServer(socket_path, controller)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = ControlClient(socket_path).request({"operation": "status"})

        assert response["ok"] is True
        assert response["data"]["state"] == "idle"
        assert response["data"]["outputs"] == {
            "up_active": False,
            "down_active": False,
        }
    finally:
        server.shutdown()
        server.server_close()
        controller.stop()
