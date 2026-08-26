"""Fail-safe RPi.GPIO adapter for isolated, polarity-reversing relays."""

import logging
import threading
import time
from types import ModuleType
from typing import Optional

from piblindhub.config import HardwareConfig
from piblindhub.domain import ButtonState, Direction, OutputState
from piblindhub.hardware.base import BlindHardware, HardwareFault

logger = logging.getLogger(__name__)


class RaspberryRelayHardware(BlindHardware):
    """Own GPIO setup and enforce break-before-make at the lowest software layer."""

    def __init__(
        self,
        config: HardwareConfig,
        gpio_module: Optional[ModuleType] = None,
        sleep=time.sleep,
    ) -> None:
        self.config = config
        self._gpio = gpio_module
        self._sleep = sleep
        self._lock = threading.Lock()
        self._initialized = False

    def _load_gpio(self):
        if self._gpio is None:
            try:
                import RPi.GPIO as gpio
            except ImportError as exc:
                raise HardwareFault("RPi.GPIO is unavailable on this host") from exc
            self._gpio = gpio
        return self._gpio

    def _level(self, active: bool) -> int:
        gpio = self._load_gpio()
        logical_high = active if self.config.relay_active_high else not active
        return gpio.HIGH if logical_high else gpio.LOW

    def _button_pressed(self, level: int) -> bool:
        gpio = self._load_gpio()
        return level == (gpio.HIGH if self.config.button_active_high else gpio.LOW)

    def initialize_safe(self) -> None:
        with self._lock:
            gpio = self._load_gpio()
            try:
                gpio.setwarnings(False)
                gpio.setmode(gpio.BCM)
                gpio.setup(
                    self.config.motor_up_pin,
                    gpio.OUT,
                    initial=self._level(False),
                )
                gpio.setup(
                    self.config.motor_down_pin,
                    gpio.OUT,
                    initial=self._level(False),
                )
                pull = gpio.PUD_DOWN if self.config.button_active_high else gpio.PUD_UP
                gpio.setup(self.config.button_up_pin, gpio.IN, pull_up_down=pull)
                gpio.setup(self.config.button_down_pin, gpio.IN, pull_up_down=pull)
                self._initialized = True
                self._write_stopped(gpio)
                self._verify_safe(gpio)
            except Exception as exc:
                self._best_effort_stop(gpio)
                raise HardwareFault(f"GPIO safe initialization failed: {exc}") from exc

    def _write_stopped(self, gpio) -> None:
        gpio.output(self.config.motor_up_pin, self._level(False))
        gpio.output(self.config.motor_down_pin, self._level(False))

    def _best_effort_stop(self, gpio) -> None:
        try:
            self._write_stopped(gpio)
        except Exception:
            logger.exception("Unable to force GPIO outputs inactive")

    def _read_outputs_unlocked(self, gpio) -> OutputState:
        up_active = gpio.input(self.config.motor_up_pin) == self._level(True)
        down_active = gpio.input(self.config.motor_down_pin) == self._level(True)
        return OutputState(up_active=up_active, down_active=down_active)

    def _verify_safe(self, gpio) -> OutputState:
        outputs = self._read_outputs_unlocked(gpio)
        if not outputs.safe:
            self._best_effort_stop(gpio)
            raise HardwareFault("GPIO readback detected both direction outputs active")
        return outputs

    def drive(self, direction: Direction) -> None:
        with self._lock:
            if not self._initialized:
                raise HardwareFault("GPIO has not been initialized")
            gpio = self._load_gpio()
            try:
                previous = self._verify_safe(gpio)
                self._write_stopped(gpio)
                stopped = self._verify_safe(gpio)
                if not stopped.stopped:
                    raise HardwareFault("A direction output remained active during neutral state")
                # The controller normally waits the dead time without blocking STOP.
                # Keep this low-level fallback for callers that request a direct reversal.
                if not previous.stopped:
                    self._sleep(self.config.switch_dead_time_ms / 1000.0)
                if direction == Direction.UP:
                    gpio.output(self.config.motor_down_pin, self._level(False))
                    gpio.output(self.config.motor_up_pin, self._level(True))
                else:
                    gpio.output(self.config.motor_up_pin, self._level(False))
                    gpio.output(self.config.motor_down_pin, self._level(True))
                outputs = self._verify_safe(gpio)
                expected = outputs.up_active if direction == Direction.UP else outputs.down_active
                if not expected:
                    raise HardwareFault("GPIO readback did not confirm requested direction")
            except Exception as exc:
                self._best_effort_stop(gpio)
                if isinstance(exc, HardwareFault):
                    raise
                raise HardwareFault(f"GPIO direction change failed: {exc}") from exc

    def stop(self) -> None:
        with self._lock:
            gpio = self._load_gpio()
            try:
                self._write_stopped(gpio)
                outputs = self._verify_safe(gpio)
                if not outputs.stopped:
                    raise HardwareFault("GPIO readback did not confirm stopped outputs")
            except Exception as exc:
                self._best_effort_stop(gpio)
                if isinstance(exc, HardwareFault):
                    raise
                raise HardwareFault(f"GPIO stop failed: {exc}") from exc

    def read_outputs(self) -> OutputState:
        with self._lock:
            return self._verify_safe(self._load_gpio())

    def read_buttons(self) -> ButtonState:
        with self._lock:
            if not self._initialized:
                raise HardwareFault("GPIO has not been initialized")
            gpio = self._load_gpio()
            return ButtonState(
                up_pressed=self._button_pressed(gpio.input(self.config.button_up_pin)),
                down_pressed=self._button_pressed(gpio.input(self.config.button_down_pin)),
            )

    def cleanup(self) -> None:
        with self._lock:
            gpio = self._load_gpio()
            try:
                self._write_stopped(gpio)
            finally:
                try:
                    gpio.cleanup(
                        [
                            self.config.motor_up_pin,
                            self.config.motor_down_pin,
                            self.config.button_up_pin,
                            self.config.button_down_pin,
                        ]
                    )
                finally:
                    self._initialized = False
