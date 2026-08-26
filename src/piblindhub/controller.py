"""Single-owner blind controller with deterministic safety invariants."""

import itertools
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from piblindhub.config import HardwareConfig
from piblindhub.domain import (
    ButtonState,
    CommandLifecycle,
    CommandResult,
    CommandSource,
    CommandType,
    ControlCommand,
    ControllerStatus,
    ControlState,
    Direction,
    OutputState,
    PositionEstimate,
    utc_now_iso,
)
from piblindhub.hardware.base import BlindHardware, HardwareFault
from piblindhub.persistence import StateRepository

logger = logging.getLogger(__name__)


@dataclass
class PendingDirection:
    direction: Direction
    source: CommandSource
    due_monotonic: float
    command: Optional[ControlCommand]


class BlindController:
    """Own all mutable control state and all post-start hardware access in one worker."""

    def __init__(
        self,
        config: HardwareConfig,
        hardware: BlindHardware,
        repository: StateRepository,
        monotonic: Callable[[], float] = time.monotonic,
        heartbeat: Optional[Callable[[], None]] = None,
    ) -> None:
        self.config = config
        self.hardware = hardware
        self.repository = repository
        self._monotonic = monotonic
        self._heartbeat = heartbeat or (lambda: None)
        self._queue: queue.PriorityQueue[tuple[int, int, ControlCommand]] = queue.PriorityQueue()
        self._queue_sequence = itertools.count()
        self._status_lock = threading.Lock()
        self._result_lock = threading.Lock()
        self._shutdown = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._last_heartbeat = 0.0
        self._state_sequence = 0
        self._status = ControllerStatus(
            state=ControlState.BOOT_SAFE,
            direction=None,
            position=PositionEstimate.unknown(),
            outputs=OutputState(),
            output_readback_confirmed=False,
            physical_control_active=False,
            movement_started_at=None,
            movement_deadline_seconds=None,
            last_stop_reason="not_started",
            fault=None,
            sequence=0,
        )
        self._results: dict[str, CommandResult] = {}
        self._direction: Optional[Direction] = None
        self._movement_source: Optional[CommandSource] = None
        self._movement_started_monotonic: Optional[float] = None
        self._movement_started_at: Optional[str] = None
        self._movement_deadline: Optional[float] = None
        self._position = PositionEstimate.unknown()
        self._pending: Optional[PendingDirection] = None
        self._buttons = ButtonState()
        self._fault: Optional[str] = None
        self._last_stop_reason: Optional[str] = "not_started"

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.repository.initialize()
        persisted = self.repository.load()
        try:
            self.hardware.initialize_safe()
            self.hardware.stop()
            outputs = self.hardware.read_outputs()
            if not outputs.safe or not outputs.stopped:
                raise HardwareFault("Outputs are not inactive after safe initialization")
        except Exception:
            try:
                self.hardware.stop()
            except Exception:
                logger.exception("Emergency stop failed during startup")
            raise

        if persisted.movement_active:
            self._position = self.repository.mark_position_unknown(
                "recovery_after_interrupted_motion"
            )
            self._last_stop_reason = "recovery_after_interrupted_motion"
        else:
            self._position = persisted.position
            self._last_stop_reason = persisted.last_stop_reason or "safe_startup"
        self._fault = persisted.last_error
        initial_state = ControlState.FAULT if self._fault else ControlState.IDLE
        self._publish_status(initial_state, OutputState())
        self._shutdown.clear()
        self._worker = threading.Thread(
            target=self._run,
            name="piblindhub-control-loop",
            daemon=False,
        )
        self._worker.start()

    def submit(self, command: ControlCommand) -> CommandResult:
        if not self.is_running:
            raise RuntimeError("Controller is not running")
        result = CommandResult(
            command_id=command.id,
            lifecycle=CommandLifecycle.ACCEPTED,
            message="Command accepted by control queue",
            created_at=command.created_at,
        )
        self._store_result(result)
        self._queue.put((command.priority, next(self._queue_sequence), command))
        return result

    @property
    def is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive() and not self._shutdown.is_set())

    def get_status(self) -> ControllerStatus:
        with self._status_lock:
            return self._status

    def get_command_result(self, command_id: str) -> Optional[CommandResult]:
        with self._result_lock:
            return self._results.get(command_id)

    def get_health(self) -> dict[str, object]:
        age = None
        if self._last_heartbeat:
            age = max(0.0, self._monotonic() - self._last_heartbeat)
        status = self.get_status()
        healthy = (
            self.is_running
            and status.fault is None
            and status.outputs.safe
            and status.output_readback_confirmed
        )
        return {
            "healthy": healthy,
            "control_loop_running": self.is_running,
            "heartbeat_age_seconds": age,
            "state": status.state.value,
            "outputs_safe": status.outputs.safe,
            "output_readback_confirmed": status.output_readback_confirmed,
            "fault": status.fault,
        }

    def stop(self, join_timeout: float = 5.0) -> None:
        self._shutdown.set()
        worker = self._worker
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=join_timeout)
        if worker and worker.is_alive():
            logger.critical("Control worker did not stop in time; forcing hardware stop")
            try:
                self.hardware.stop()
            except Exception:
                logger.exception("Forced hardware stop failed")

    def _run(self) -> None:
        poll_seconds = self.config.poll_interval_ms / 1000.0
        try:
            while not self._shutdown.is_set():
                try:
                    self._last_heartbeat = self._monotonic()
                    self._heartbeat()
                    self._handle_physical_buttons(self.hardware.read_buttons())
                    self._process_next_command()
                    # STOP has queue priority and must cancel pending reversals before
                    # a timer is allowed to energize another direction.
                    self._tick_timers()
                    self._verify_outputs()
                except Exception as exc:
                    self._enter_fault(f"control_loop_error: {exc}")
                self._shutdown.wait(poll_seconds)
        finally:
            self._shutdown_hardware()

    def _process_next_command(self) -> None:
        try:
            _, _, command = self._queue.get_nowait()
        except queue.Empty:
            return
        self._update_result(command, CommandLifecycle.RUNNING, "Command execution started")
        try:
            if command.type == CommandType.STOP:
                self._cancel_queued_commands("Cancelled by priority STOP")
                self._stop_motion("command_stop")
                self._complete(command, "Outputs confirmed inactive")
            elif command.type == CommandType.MOVE_UP:
                self._request_direction(Direction.UP, command.source, command)
            elif command.type == CommandType.MOVE_DOWN:
                self._request_direction(Direction.DOWN, command.source, command)
            elif command.type == CommandType.RESET_FAULT:
                self._reset_fault(command)
            elif command.type == CommandType.SET_ESTIMATED_POSITION:
                self._set_estimated_position(command)
        except Exception as exc:
            self._fail(command, str(exc))
            self._enter_fault(f"command_failed: {exc}")

    def _request_direction(
        self,
        direction: Direction,
        source: CommandSource,
        command: Optional[ControlCommand],
    ) -> None:
        if self._fault:
            if command:
                self._fail(command, "Controller is in fault state")
            return
        if self._buttons.any_pressed and source != CommandSource.PHYSICAL_BUTTON:
            if command:
                self._fail(command, "Physical controls have priority")
            return
        status = self.get_status()
        if status.state in {ControlState.MOVING_UP, ControlState.MOVING_DOWN}:
            if self._direction == direction:
                if source == CommandSource.PHYSICAL_BUTTON:
                    self._movement_source = CommandSource.PHYSICAL_BUTTON
                    self._republish_current_status()
                if command:
                    self._complete(command, "Already moving in requested direction")
                return
            self._stop_motion("direction_change")
            self._pending = PendingDirection(
                direction=direction,
                source=source,
                due_monotonic=self._monotonic() + self.config.switch_dead_time_ms / 1000.0,
                command=command,
            )
            self._publish_status(ControlState.REVERSING, OutputState())
            return
        if self._pending:
            if self._pending.command:
                self._cancel(self._pending.command, "Superseded by a newer direction request")
            self._pending = PendingDirection(
                direction=direction,
                source=source,
                due_monotonic=self._monotonic() + self.config.switch_dead_time_ms / 1000.0,
                command=command,
            )
            self._publish_status(ControlState.REVERSING, OutputState())
            return
        self._start_motion(direction, source, command)

    def _cancel_queued_commands(self, reason: str) -> None:
        while True:
            try:
                _, _, queued = self._queue.get_nowait()
            except queue.Empty:
                return
            self._cancel(queued, reason)

    def _start_motion(
        self,
        direction: Direction,
        source: CommandSource,
        command: Optional[ControlCommand],
    ) -> None:
        started_at = self.repository.mark_movement_started(direction)
        try:
            self.hardware.drive(direction)
            outputs = self.hardware.read_outputs()
            expected = outputs.up_active if direction == Direction.UP else outputs.down_active
            if not outputs.safe or not expected:
                raise HardwareFault("Output readback rejected movement start")
        except Exception:
            try:
                self.hardware.stop()
            finally:
                self.repository.mark_fault("movement_start_failed")
            raise
        now = self._monotonic()
        self._direction = direction
        self._movement_source = source
        self._movement_started_monotonic = now
        self._movement_started_at = started_at
        self._movement_deadline = now + self.config.max_movement_seconds
        self._pending = None
        state = ControlState.MOVING_UP if direction == Direction.UP else ControlState.MOVING_DOWN
        self._publish_status(state, outputs)
        if command:
            self._complete(command, "Movement started and output readback confirmed")

    def _stop_motion(self, reason: str) -> None:
        if self._pending and self._pending.command:
            self._cancel(self._pending.command, "Direction change cancelled by stop")
        self._pending = None
        direction = self._direction
        elapsed = 0.0
        if self._movement_started_monotonic is not None:
            elapsed = max(0.0, self._monotonic() - self._movement_started_monotonic)
        try:
            self.hardware.stop()
            outputs = self.hardware.read_outputs()
            if not outputs.stopped:
                raise HardwareFault("Output readback rejected stop")
        except Exception as exc:
            self._enter_fault(f"stop_failed: {exc}")
            raise
        self._position = self._estimate_position(direction, elapsed)
        self.repository.mark_stopped(
            self._position,
            reason,
            clear_error=self._fault is None,
        )
        self._direction = None
        self._movement_source = None
        self._movement_started_monotonic = None
        self._movement_started_at = None
        self._movement_deadline = None
        self._last_stop_reason = reason
        state = ControlState.FAULT if self._fault else ControlState.IDLE
        self._publish_status(state, OutputState())

    def _estimate_position(
        self,
        direction: Optional[Direction],
        elapsed: float,
    ) -> PositionEstimate:
        if direction is None or self._position.value is None:
            return PositionEstimate.unknown()
        delta = elapsed / self.config.full_travel_seconds * 100.0
        value = (
            self._position.value - delta
            if direction == Direction.UP
            else self._position.value + delta
        )
        return PositionEstimate.estimated(value)

    def _tick_timers(self) -> None:
        now = self._monotonic()
        if self._pending and now >= self._pending.due_monotonic:
            pending = self._pending
            self._pending = None
            if pending.source == CommandSource.PHYSICAL_BUTTON and not self._buttons.any_pressed:
                if pending.command:
                    self._cancel(pending.command, "Physical button released during dead time")
            else:
                self._start_motion(pending.direction, pending.source, pending.command)
        if self._movement_deadline is not None and now >= self._movement_deadline:
            self._stop_motion("max_runtime_timeout")
            self.repository.append_event(
                "safety_timeout",
                {"max_movement_seconds": self.config.max_movement_seconds},
            )

    def _handle_physical_buttons(self, buttons: ButtonState) -> None:
        previous = self._buttons
        self._buttons = buttons
        if buttons.both_pressed:
            if not previous.both_pressed or not self._fault:
                self._enter_fault("both_physical_buttons_pressed")
            return
        if buttons.up_pressed:
            if not previous.up_pressed or self._movement_source != CommandSource.PHYSICAL_BUTTON:
                self._request_direction(Direction.UP, CommandSource.PHYSICAL_BUTTON, None)
            return
        if buttons.down_pressed:
            if not previous.down_pressed or self._movement_source != CommandSource.PHYSICAL_BUTTON:
                self._request_direction(Direction.DOWN, CommandSource.PHYSICAL_BUTTON, None)
            return
        if previous.any_pressed:
            if self._movement_source == CommandSource.PHYSICAL_BUTTON or (
                self._pending and self._pending.source == CommandSource.PHYSICAL_BUTTON
            ):
                self._stop_motion("physical_button_released")
            else:
                self._republish_current_status()
        elif buttons != previous:
            self._republish_current_status()

    def _set_estimated_position(self, command: ControlCommand) -> None:
        if self._buttons.any_pressed or self._direction or self._pending:
            self._fail(command, "Position can only be set while safely idle")
            return
        if command.position is None or not 0.0 <= command.position <= 100.0:
            self._fail(command, "Estimated position must be between 0 and 100")
            return
        self._position = self.repository.set_estimated_position(
            command.position,
            "manual_authenticated_command",
        )
        self._republish_current_status()
        self._complete(command, "Estimated position updated; no sensor confirmation is claimed")

    def _reset_fault(self, command: ControlCommand) -> None:
        if not self._fault:
            self._complete(command, "Controller is not in fault state")
            return
        if self._buttons.any_pressed:
            self._fail(command, "Release all physical buttons before resetting fault")
            return
        self.hardware.stop()
        outputs = self.hardware.read_outputs()
        if not outputs.stopped:
            self._fail(command, "Outputs are not inactive")
            return
        self._last_stop_reason = "fault_reset"
        self._position = self.repository.clear_fault("fault_reset")
        self._fault = None
        self._publish_status(ControlState.IDLE, outputs)
        self._complete(command, "Fault reset with outputs confirmed inactive")

    def _verify_outputs(self) -> None:
        outputs = self.hardware.read_outputs()
        if not outputs.safe:
            raise HardwareFault("Both direction outputs are active")
        if self._direction == Direction.UP and not outputs.up_active:
            raise HardwareFault("UP movement state disagrees with GPIO readback")
        if self._direction == Direction.DOWN and not outputs.down_active:
            raise HardwareFault("DOWN movement state disagrees with GPIO readback")
        if self._direction is None and not outputs.stopped:
            raise HardwareFault("Idle controller has an active GPIO output")

    def _enter_fault(self, message: str) -> None:
        logger.error("Controller fault: %s", message)
        outputs = OutputState()
        readback_confirmed = False
        try:
            self.hardware.stop()
            outputs = self.hardware.read_outputs()
            readback_confirmed = outputs.stopped
        except Exception:
            logger.exception("Emergency stop failed while entering fault")
        self._fault = message
        self._direction = None
        self._movement_source = None
        self._movement_started_monotonic = None
        self._movement_started_at = None
        self._movement_deadline = None
        if self._pending and self._pending.command:
            self._fail(self._pending.command, "Cancelled by controller fault")
        self._pending = None
        self._position = PositionEstimate.unknown()
        try:
            self.repository.mark_fault(message)
        except Exception:
            logger.exception("Unable to persist controller fault")
        self._publish_status(
            ControlState.FAULT,
            outputs,
            output_readback_confirmed=readback_confirmed,
        )

    def _shutdown_hardware(self) -> None:
        self._pending = None
        output_readback_confirmed = False
        try:
            self.hardware.stop()
            outputs = self.hardware.read_outputs()
            if not outputs.stopped:
                raise HardwareFault("Output readback rejected shutdown stop")
            output_readback_confirmed = True
            self._last_stop_reason = "service_shutdown"
            self._position = self._estimate_position(
                self._direction,
                max(
                    0.0,
                    self._monotonic() - self._movement_started_monotonic,
                )
                if self._movement_started_monotonic is not None
                else 0.0,
            )
            self.repository.mark_stopped(
                self._position,
                self._last_stop_reason,
                clear_error=self._fault is None,
            )
        except Exception as exc:
            logger.exception("Hardware stop failed during shutdown")
            try:
                self.repository.mark_fault(f"shutdown_stop_failed: {exc}")
            except Exception:
                logger.exception("Unable to persist shutdown fault")
        finally:
            try:
                self.hardware.cleanup()
            except Exception:
                logger.exception("Hardware cleanup failed")
            self._direction = None
            self._movement_source = None
            self._movement_started_monotonic = None
            self._movement_started_at = None
            self._movement_deadline = None
            self._publish_status(
                ControlState.SHUTDOWN,
                OutputState(),
                output_readback_confirmed=output_readback_confirmed,
            )

    def _publish_status(
        self,
        state: ControlState,
        outputs: OutputState,
        output_readback_confirmed: bool = True,
    ) -> None:
        self._state_sequence += 1
        deadline_remaining = None
        if self._movement_deadline is not None:
            deadline_remaining = max(0.0, self._movement_deadline - self._monotonic())
        status = ControllerStatus(
            state=state,
            direction=self._direction,
            position=self._position,
            outputs=outputs,
            output_readback_confirmed=output_readback_confirmed,
            physical_control_active=self._buttons.any_pressed,
            movement_started_at=self._movement_started_at,
            movement_deadline_seconds=deadline_remaining,
            last_stop_reason=self._last_stop_reason,
            fault=self._fault,
            sequence=self._state_sequence,
            updated_at=utc_now_iso(),
        )
        with self._status_lock:
            self._status = status

    def _republish_current_status(self) -> None:
        current = self.get_status()
        self._publish_status(
            current.state,
            current.outputs,
            output_readback_confirmed=current.output_readback_confirmed,
        )

    def _store_result(self, result: CommandResult) -> None:
        with self._result_lock:
            self._results[result.command_id] = result
            if len(self._results) > 500:
                oldest = next(iter(self._results))
                del self._results[oldest]

    def _update_result(
        self,
        command: ControlCommand,
        lifecycle: CommandLifecycle,
        message: str,
    ) -> None:
        self._store_result(
            CommandResult(
                command_id=command.id,
                lifecycle=lifecycle,
                message=message,
                created_at=command.created_at,
            )
        )

    def _complete(self, command: ControlCommand, message: str) -> None:
        self._update_result(command, CommandLifecycle.COMPLETED, message)

    def _fail(self, command: ControlCommand, message: str) -> None:
        self._update_result(command, CommandLifecycle.FAILED, message)

    def _cancel(self, command: ControlCommand, message: str) -> None:
        self._update_result(command, CommandLifecycle.CANCELLED, message)
