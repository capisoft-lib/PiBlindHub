"""Domain types shared by the control daemon and API gateway."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


class ControlState(str, Enum):
    BOOT_SAFE = "boot_safe"
    IDLE = "idle"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
    REVERSING = "reversing"
    FAULT = "fault"
    SHUTDOWN = "shutdown"


class CommandType(str, Enum):
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    STOP = "stop"
    RESET_FAULT = "reset_fault"
    SET_ESTIMATED_POSITION = "set_estimated_position"


class CommandSource(str, Enum):
    API = "api"
    MQTT = "mqtt"
    PHYSICAL_BUTTON = "physical_button"
    SYSTEM = "system"


class CommandLifecycle(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PositionConfidence(str, Enum):
    UNKNOWN = "unknown"
    ESTIMATED = "estimated"
    SENSOR_CONFIRMED = "sensor_confirmed"


@dataclass(frozen=True)
class PositionEstimate:
    value: Optional[float]
    confidence: PositionConfidence
    updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def unknown(cls) -> "PositionEstimate":
        return cls(value=None, confidence=PositionConfidence.UNKNOWN)

    @classmethod
    def estimated(cls, value: float) -> "PositionEstimate":
        return cls(
            value=max(0.0, min(100.0, float(value))),
            confidence=PositionConfidence.ESTIMATED,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence.value,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ButtonState:
    up_pressed: bool = False
    down_pressed: bool = False

    @property
    def any_pressed(self) -> bool:
        return self.up_pressed or self.down_pressed

    @property
    def both_pressed(self) -> bool:
        return self.up_pressed and self.down_pressed


@dataclass(frozen=True)
class OutputState:
    up_active: bool = False
    down_active: bool = False

    @property
    def safe(self) -> bool:
        return not (self.up_active and self.down_active)

    @property
    def stopped(self) -> bool:
        return not self.up_active and not self.down_active


@dataclass(frozen=True)
class ControllerStatus:
    state: ControlState
    direction: Optional[Direction]
    position: PositionEstimate
    outputs: OutputState
    output_readback_confirmed: bool
    physical_control_active: bool
    movement_started_at: Optional[str]
    movement_deadline_seconds: Optional[float]
    last_stop_reason: Optional[str]
    fault: Optional[str]
    sequence: int
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "direction": self.direction.value if self.direction else None,
            "position": self.position.to_dict(),
            "outputs": asdict(self.outputs),
            "output_readback_confirmed": self.output_readback_confirmed,
            "physical_control_active": self.physical_control_active,
            "movement_started_at": self.movement_started_at,
            "movement_deadline_seconds": self.movement_deadline_seconds,
            "last_stop_reason": self.last_stop_reason,
            "fault": self.fault,
            "sequence": self.sequence,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ControlCommand:
    type: CommandType
    source: CommandSource = CommandSource.API
    position: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def priority(self) -> int:
        if self.type == CommandType.STOP:
            return 0
        if self.source == CommandSource.PHYSICAL_BUTTON:
            return 1
        if self.type == CommandType.RESET_FAULT:
            return 5
        return 10


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    lifecycle: CommandLifecycle
    message: str
    created_at: str
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, str]:
        return {
            "command_id": self.command_id,
            "lifecycle": self.lifecycle.value,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
