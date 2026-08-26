import pytest
from piblindhub.config import HardwareConfig
from piblindhub.domain import Direction
from piblindhub.hardware.base import HardwareFault
from piblindhub.hardware.raspberry import RaspberryRelayHardware


class FakeGpio:
    BCM = 11
    OUT = 1
    IN = 0
    HIGH = 1
    LOW = 0
    PUD_DOWN = 21
    PUD_UP = 22

    def __init__(self):
        self.levels = {}
        self.history = []
        self.ignore_high_on = None

    def setwarnings(self, value):
        self.history.append(("setwarnings", value))

    def setmode(self, mode):
        self.history.append(("setmode", mode))

    def setup(self, pin, mode, initial=None, pull_up_down=None):
        if initial is not None:
            self.levels[pin] = initial
        elif mode == self.IN:
            self.levels[pin] = self.LOW if pull_up_down == self.PUD_DOWN else self.HIGH
        self.history.append(("setup", pin, mode, initial, pull_up_down))

    def output(self, pin, level):
        if not (self.ignore_high_on == pin and level == self.HIGH):
            self.levels[pin] = level
        self.history.append(("output", pin, level))

    def input(self, pin):
        return self.levels[pin]

    def cleanup(self, pins):
        self.history.append(("cleanup", tuple(pins)))


def config():
    return HardwareConfig(backend="raspberry", switch_dead_time_ms=100)


def test_initialization_and_cleanup_are_inactive():
    gpio = FakeGpio()
    hardware = RaspberryRelayHardware(config(), gpio_module=gpio, sleep=lambda _value: None)

    hardware.initialize_safe()
    assert hardware.read_outputs().stopped
    hardware.drive(Direction.UP)
    assert hardware.read_outputs().up_active
    hardware.cleanup()

    assert gpio.levels[23] == gpio.LOW
    assert gpio.levels[24] == gpio.LOW


def test_direct_reversal_enforces_low_level_dead_time():
    gpio = FakeGpio()
    sleeps = []
    hardware = RaspberryRelayHardware(config(), gpio_module=gpio, sleep=sleeps.append)
    hardware.initialize_safe()
    hardware.drive(Direction.UP)

    hardware.drive(Direction.DOWN)

    assert sleeps == [0.1]
    assert hardware.read_outputs().down_active
    assert not hardware.read_outputs().up_active


def test_failed_output_readback_fails_closed():
    gpio = FakeGpio()
    hardware = RaspberryRelayHardware(config(), gpio_module=gpio, sleep=lambda _value: None)
    hardware.initialize_safe()
    gpio.ignore_high_on = 23

    with pytest.raises(HardwareFault, match="did not confirm"):
        hardware.drive(Direction.UP)

    assert hardware.read_outputs().stopped
