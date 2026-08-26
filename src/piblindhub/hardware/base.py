"""Hardware boundary for the two-wire, polarity-reversing blind interface."""

from abc import ABC, abstractmethod

from piblindhub.domain import ButtonState, Direction, OutputState


class HardwareFault(RuntimeError):
    pass


class BlindHardware(ABC):
    @abstractmethod
    def initialize_safe(self) -> None:
        """Initialize hardware with both directions inactive."""

    @abstractmethod
    def drive(self, direction: Direction) -> None:
        """Apply one direction after enforcing a neutral dead time."""

    @abstractmethod
    def stop(self) -> None:
        """Deactivate both direction outputs."""

    @abstractmethod
    def read_outputs(self) -> OutputState:
        """Return logical output state, not inferred motion state."""

    @abstractmethod
    def read_buttons(self) -> ButtonState:
        """Read physical control buttons."""

    @abstractmethod
    def cleanup(self) -> None:
        """Leave outputs inactive and release GPIO resources."""
