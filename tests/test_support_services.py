import json
import signal
from hashlib import sha256

from piblindhub import daemon, token_cli
from piblindhub.config import AppConfig
from piblindhub.daemon import WatchdogHeartbeat
from piblindhub.systemd_notify import SystemdNotifier
from piblindhub.token_cli import generate_token


class RecordingNotifier:
    enabled = True

    def __init__(self):
        self.messages = []

    def watchdog(self):
        self.messages.append("watchdog")


def test_watchdog_uses_half_systemd_interval(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "2000000")
    notifier = RecordingNotifier()
    times = iter([0.5, 1.1, 1.5, 2.2])
    heartbeat = WatchdogHeartbeat(notifier, monotonic=lambda: next(times))

    heartbeat()
    heartbeat()
    heartbeat()
    heartbeat()

    assert notifier.messages == ["watchdog", "watchdog"]


def test_watchdog_is_disabled_without_systemd_environment(monkeypatch):
    monkeypatch.delenv("WATCHDOG_USEC", raising=False)
    notifier = RecordingNotifier()

    WatchdogHeartbeat(notifier)()

    assert notifier.messages == []


def test_systemd_notifier_sends_abstract_socket_messages(monkeypatch):
    sent = []

    class FakeSocket:
        def connect(self, address):
            sent.append(("connect", address))

        def sendall(self, payload):
            sent.append(("send", payload.decode()))

        def close(self):
            sent.append(("close", None))

    monkeypatch.setattr("piblindhub.systemd_notify.socket.AF_UNIX", 1, raising=False)
    monkeypatch.setattr(
        "piblindhub.systemd_notify.socket.socket", lambda _family, _kind: FakeSocket()
    )
    notifier = SystemdNotifier("@notify")

    notifier.ready("ready")
    notifier.watchdog()
    notifier.stopping()

    assert notifier.enabled is True
    assert ("connect", "\0notify") in sent
    assert ("send", "READY=1\nSTATUS=ready") in sent
    assert ("send", "WATCHDOG=1") in sent
    assert ("send", "STOPPING=1\nSTATUS=Stopping with outputs inactive") in sent


def test_systemd_notifier_without_socket_is_noop():
    notifier = SystemdNotifier("")
    notifier.notify("ignored")
    assert notifier.enabled is False


def test_generated_token_matches_stored_digest():
    generated = generate_token()

    assert len(generated["token"]) >= 40
    assert sha256(generated["token"].encode()).hexdigest() == generated["sha256"]


def test_token_cli_json_and_human_output(monkeypatch, capsys):
    monkeypatch.setattr(
        token_cli,
        "generate_token",
        lambda: {"token": "shown-once", "sha256": "a" * 64},
    )
    monkeypatch.setattr("sys.argv", ["piblindhub-token", "--json"])
    token_cli.main()
    assert json.loads(capsys.readouterr().out)["token"] == "shown-once"

    monkeypatch.setattr("sys.argv", ["piblindhub-token"])
    token_cli.main()
    output = capsys.readouterr().out
    assert "shown-once" in output
    assert "PIBLINDHUB_API_TOKEN_SHA256=" in output


class FakeDaemonController:
    def __init__(self, fail_start=False):
        self.fail_start = fail_start
        self.started = False
        self.stopped = False

    def start(self):
        if self.fail_start:
            raise RuntimeError("startup failed")
        self.started = True

    def stop(self):
        self.stopped = True


class FakeDaemonNotifier:
    enabled = True

    def __init__(self):
        self.ready_status = None
        self.stopping_called = False

    def ready(self, status):
        self.ready_status = status

    def stopping(self):
        self.stopping_called = True


def daemon_config(tmp_path):
    return AppConfig.from_mapping(
        {
            "hardware": {"backend": "fake"},
            "paths": {
                "state_database": str(tmp_path / "state.db"),
                "control_socket": str(tmp_path / "control.sock"),
            },
        }
    )


def test_daemon_run_starts_notifies_and_stops(tmp_path, monkeypatch):
    config = daemon_config(tmp_path)
    controller = FakeDaemonController()
    notifier = FakeDaemonNotifier()
    callbacks = {}

    class FakeServer:
        timeout = None

        def __init__(self, path, actual_controller):
            assert path == config.paths.control_socket
            assert actual_controller is controller
            self.closed = False

        def handle_request(self):
            callbacks[signal.SIGTERM](signal.SIGTERM, None)

        def server_close(self):
            self.closed = True

    monkeypatch.setattr(daemon.AppConfig, "load", lambda _path: config)
    monkeypatch.setattr(daemon, "SystemdNotifier", lambda: notifier)
    monkeypatch.setattr(daemon, "build_controller", lambda _config, _notifier: controller)
    monkeypatch.setattr(daemon, "UnixControlServer", FakeServer)
    monkeypatch.setattr(
        daemon.signal,
        "signal",
        lambda number, callback: callbacks.setdefault(number, callback),
    )

    result = daemon.run("config.json")

    assert result == 0
    assert controller.started is True
    assert controller.stopped is True
    assert notifier.ready_status == "Control loop ready; outputs inactive"
    assert notifier.stopping_called is True


def test_daemon_failure_still_stops_controller(tmp_path, monkeypatch):
    config = daemon_config(tmp_path)
    controller = FakeDaemonController(fail_start=True)
    notifier = FakeDaemonNotifier()
    monkeypatch.setattr(daemon.AppConfig, "load", lambda _path: config)
    monkeypatch.setattr(daemon, "SystemdNotifier", lambda: notifier)
    monkeypatch.setattr(daemon, "build_controller", lambda _config, _notifier: controller)
    monkeypatch.setattr(daemon.signal, "signal", lambda _number, _callback: None)

    assert daemon.run("config.json") == 1
    assert controller.stopped is True
    assert notifier.stopping_called is True


def test_build_controller_selects_fake_hardware(tmp_path):
    controller = daemon.build_controller(daemon_config(tmp_path), FakeDaemonNotifier())

    assert controller.hardware.__class__.__name__ == "FakeBlindHardware"
