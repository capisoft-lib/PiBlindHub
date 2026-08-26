"""Minimal systemd notification support without a runtime dependency."""

import os
import socket
from typing import Optional


class SystemdNotifier:
    def __init__(self, notify_socket: Optional[str] = None) -> None:
        self.notify_socket = notify_socket or os.environ.get("NOTIFY_SOCKET")

    @property
    def enabled(self) -> bool:
        return bool(self.notify_socket)

    def notify(self, message: str) -> None:
        if not self.notify_socket:
            return
        address = self.notify_socket
        if address.startswith("@"):
            address = "\0" + address[1:]
        unix_family = getattr(socket, "AF_UNIX", None)
        if unix_family is None:
            raise OSError("systemd notifications require Unix domain sockets")
        client = socket.socket(unix_family, socket.SOCK_DGRAM)
        try:
            client.connect(address)
            client.sendall(message.encode("utf-8"))
        finally:
            client.close()

    def ready(self, status: str) -> None:
        self.notify(f"READY=1\nSTATUS={status}")

    def watchdog(self) -> None:
        self.notify("WATCHDOG=1")

    def stopping(self) -> None:
        self.notify("STOPPING=1\nSTATUS=Stopping with outputs inactive")
