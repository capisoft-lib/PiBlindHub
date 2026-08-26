"""Deterministic fake hardware used by tests and development."""

import threading
from typing import Optional

from piblindhub.domain import ButtonState, Direction, OutputState
from piblindhub.hardware.base import BlindHardware, HardwareFault


class FakeBlindHardware(BlindHardware):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._outputs = OutputState()
        self._buttons = ButtonState()
        self.initialized = False
        self.cleaned_up = False
        self.fail_next_operation: Optional[str] = None
        self.history: list[tuple[str, Optional[str]]] = []

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_next_operation == operation:
            self.fail_next_operation = None
            raise HardwareFault(f"Injected {operation} failure")

    def initialize_safe(self) -> None:
        with self._lock:
            self._maybe_fail("initialize")
            self._outputs = OutputState()
            self.initialized = True
            self.cleaned_up = False
            self.history.append(("initialize_safe", None))

    def drive(self, direction: Direction) -> None:
        with self._lock:
            self._maybe_fail("drive")
            if not self.initialized:
                raise HardwareFault("Hardware has not been initialized")
            self._outputs = OutputState()
            self.history.append(("neutral", None))
            if direction == Direction.UP:
                self._outputs = OutputState(up_active=True)
            else:
                self._outputs = OutputState(down_active=True)
            if not self._outputs.safe:
                self._outputs = OutputState()
                raise HardwareFault("Both direction outputs became active")
            self.history.append(("drive", direction.value))

    def stop(self) -> None:
        with self._lock:
            self._maybe_fail("stop")
            self._outputs = OutputState()
            self.history.append(("stop", None))

    def read_outputs(self) -> OutputState:
        with self._lock:
            self._maybe_fail("read_outputs")
            return self._outputs

    def read_buttons(self) -> ButtonState:
        with self._lock:
            self._maybe_fail("read_buttons")
            return self._buttons

    def set_buttons(self, up_pressed: bool = False, down_pressed: bool = False) -> None:
        with self._lock:
            self._buttons = ButtonState(up_pressed=up_pressed, down_pressed=down_pressed)
            self.history.append(("buttons", f"{up_pressed}:{down_pressed}"))

    def cleanup(self) -> None:
        with self._lock:
            self._outputs = OutputState()
            self.cleaned_up = True
            self.history.append(("cleanup", None))
