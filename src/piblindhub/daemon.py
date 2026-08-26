"""PiBlindHub control daemon entry point."""

import argparse
import logging
import os
import signal
import threading
import time
from typing import Optional

from piblindhub.config import AppConfig
from piblindhub.controller import BlindController
from piblindhub.hardware import FakeBlindHardware, RaspberryRelayHardware
from piblindhub.hardware.base import BlindHardware
from piblindhub.ipc import UnixControlServer
from piblindhub.persistence import StateRepository
from piblindhub.systemd_notify import SystemdNotifier

logger = logging.getLogger(__name__)


class WatchdogHeartbeat:
    def __init__(self, notifier: SystemdNotifier, monotonic=time.monotonic) -> None:
        watchdog_usec = int(os.environ.get("WATCHDOG_USEC", "0") or "0")
        self.interval = watchdog_usec / 2_000_000.0 if watchdog_usec else 0.0
        self.notifier = notifier
        self.monotonic = monotonic
        self.last_sent = 0.0

    def __call__(self) -> None:
        if not self.notifier.enabled or not self.interval:
            return
        now = self.monotonic()
        if now - self.last_sent >= self.interval:
            self.notifier.watchdog()
            self.last_sent = now


def build_controller(
    config: AppConfig, notifier: Optional[SystemdNotifier] = None
) -> BlindController:
    hardware: BlindHardware
    if config.hardware.backend == "fake":
        hardware = FakeBlindHardware()
    else:
        hardware = RaspberryRelayHardware(config.hardware)
    repository = StateRepository(config.paths.state_database)
    heartbeat = WatchdogHeartbeat(notifier or SystemdNotifier())
    return BlindController(config.hardware, hardware, repository, heartbeat=heartbeat)


def run(config_path: Optional[str] = None) -> int:
    config = AppConfig.load(config_path)
    notifier = SystemdNotifier()
    controller = build_controller(config, notifier)
    stopping = threading.Event()

    def handle_signal(signum, _frame) -> None:
        logger.info("Received signal %s", signum)
        stopping.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server: Optional[UnixControlServer] = None
    try:
        controller.start()
        server = UnixControlServer(config.paths.control_socket, controller)
        server.timeout = 0.5
        notifier.ready("Control loop ready; outputs inactive")
        logger.info("Control daemon ready on %s", config.paths.control_socket)
        while not stopping.is_set():
            server.handle_request()
        return 0
    except Exception:
        logger.exception("Control daemon failed")
        return 1
    finally:
        notifier.stopping()
        if server is not None:
            server.server_close()
        controller.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="PiBlindHub fail-safe control daemon")
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
