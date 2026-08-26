import time

import pytest
from conftest import wait_until
from piblindhub.config import HardwareConfig
from piblindhub.controller import BlindController
from piblindhub.domain import (
    CommandLifecycle,
    CommandType,
    ControlCommand,
    ControlState,
    Direction,
    PositionConfidence,
)
from piblindhub.hardware.fake import FakeBlindHardware
from piblindhub.persistence import StateRepository


def make_controller(tmp_path, *, dead_time=0.1, max_runtime=1.0):
    config = HardwareConfig(
        backend="fake",
        switch_dead_time_ms=int(dead_time * 1000),
        max_movement_seconds=max_runtime,
        full_travel_seconds=1.0,
        poll_interval_ms=10,
    )
    hardware = FakeBlindHardware()
    repository = StateRepository(str(tmp_path / "state.db"))
    controller = BlindController(config, hardware, repository)
    return controller, hardware, repository


def result_is(controller, command, lifecycle):
    result = controller.get_command_result(command.id)
    return result is not None and result.lifecycle == lifecycle


@pytest.fixture
def running_controller(tmp_path):
    controller, hardware, repository = make_controller(tmp_path)
    controller.start()
    try:
        yield controller, hardware, repository
    finally:
        controller.stop()


def test_startup_is_inactive_unknown_and_does_not_move(running_controller):
    controller, hardware, _repository = running_controller

    status = controller.get_status()

    assert status.state == ControlState.IDLE
    assert status.outputs.stopped
    assert status.output_readback_confirmed is True
    assert status.position.confidence == PositionConfidence.UNKNOWN

    hardware.set_buttons()
    wait_until(lambda: not controller.get_status().physical_control_active)
    assert not any(event[0] == "drive" for event in hardware.history)


def test_stop_cancels_pending_reversal_before_it_can_energize(running_controller):
    controller, hardware, _repository = running_controller
    up = ControlCommand(CommandType.MOVE_UP)
    controller.submit(up)
    wait_until(lambda: result_is(controller, up, CommandLifecycle.COMPLETED))

    down = ControlCommand(CommandType.MOVE_DOWN)
    controller.submit(down)
    wait_until(lambda: controller.get_status().state == ControlState.REVERSING)

    stop = ControlCommand(CommandType.STOP)
    controller.submit(stop)
    wait_until(lambda: result_is(controller, stop, CommandLifecycle.COMPLETED))
    time.sleep(0.15)

    assert controller.get_status().outputs.stopped
    assert ("drive", Direction.DOWN.value) not in hardware.history
    assert result_is(controller, down, CommandLifecycle.CANCELLED)


def test_priority_stop_flushes_stale_queued_movements(tmp_path):
    config = HardwareConfig(
        backend="fake",
        switch_dead_time_ms=100,
        max_movement_seconds=1.0,
        full_travel_seconds=1.0,
        poll_interval_ms=100,
    )
    hardware = FakeBlindHardware()
    controller = BlindController(
        config,
        hardware,
        StateRepository(str(tmp_path / "state.db")),
    )
    controller.start()
    try:
        movements = [
            ControlCommand(CommandType.MOVE_UP if index % 2 == 0 else CommandType.MOVE_DOWN)
            for index in range(8)
        ]
        for movement in movements:
            controller.submit(movement)
        stop = ControlCommand(CommandType.STOP)
        controller.submit(stop)

        wait_until(lambda: result_is(controller, stop, CommandLifecycle.COMPLETED))
        drives_after_stop = len([event for event in hardware.history if event[0] == "drive"])
        time.sleep(0.25)

        lifecycles = {controller.get_command_result(command.id).lifecycle for command in movements}
        assert CommandLifecycle.ACCEPTED not in lifecycles
        assert CommandLifecycle.RUNNING not in lifecycles
        assert CommandLifecycle.CANCELLED in lifecycles
        assert controller.get_status().outputs.stopped
        assert (
            len([event for event in hardware.history if event[0] == "drive"]) == drives_after_stop
        )
    finally:
        controller.stop()


def test_reversal_passes_through_confirmed_neutral(running_controller):
    controller, hardware, _repository = running_controller
    up = ControlCommand(CommandType.MOVE_UP)
    controller.submit(up)
    wait_until(lambda: result_is(controller, up, CommandLifecycle.COMPLETED))

    down = ControlCommand(CommandType.MOVE_DOWN)
    controller.submit(down)
    wait_until(lambda: result_is(controller, down, CommandLifecycle.COMPLETED))

    up_index = hardware.history.index(("drive", Direction.UP.value))
    down_index = hardware.history.index(("drive", Direction.DOWN.value))
    between = hardware.history[up_index + 1 : down_index]
    assert ("stop", None) in between
    assert controller.get_status().state == ControlState.MOVING_DOWN


def test_local_timeout_stops_without_api(tmp_path):
    controller, hardware, _repository = make_controller(tmp_path, max_runtime=0.08)
    controller.start()
    try:
        command = ControlCommand(CommandType.MOVE_UP)
        controller.submit(command)
        wait_until(lambda: controller.get_status().last_stop_reason == "max_runtime_timeout")

        assert controller.get_status().outputs.stopped
        assert hardware.read_outputs().stopped
    finally:
        controller.stop()


def test_physical_button_adopts_same_direction_and_release_stops(running_controller):
    controller, hardware, _repository = running_controller
    remote = ControlCommand(CommandType.MOVE_UP)
    controller.submit(remote)
    wait_until(lambda: result_is(controller, remote, CommandLifecycle.COMPLETED))

    hardware.set_buttons(up_pressed=True)
    wait_until(lambda: controller.get_status().physical_control_active)
    hardware.set_buttons()
    wait_until(lambda: controller.get_status().last_stop_reason == "physical_button_released")

    assert controller.get_status().outputs.stopped


def test_both_physical_buttons_force_fault_and_stop(running_controller):
    controller, hardware, _repository = running_controller
    command = ControlCommand(CommandType.MOVE_DOWN)
    controller.submit(command)
    wait_until(lambda: result_is(controller, command, CommandLifecycle.COMPLETED))

    hardware.set_buttons(up_pressed=True, down_pressed=True)
    wait_until(lambda: controller.get_status().state == ControlState.FAULT)

    status = controller.get_status()
    assert status.outputs.stopped
    assert status.output_readback_confirmed is True
    assert status.position.confidence == PositionConfidence.UNKNOWN


def test_interrupted_persistent_motion_recovers_unknown_without_movement(tmp_path):
    controller, hardware, repository = make_controller(tmp_path)
    repository.initialize()
    repository.set_estimated_position(60.0, "old_calibration")
    repository.mark_movement_started(Direction.UP)

    controller.start()
    try:
        status = controller.get_status()
        assert status.position.confidence == PositionConfidence.UNKNOWN
        assert status.last_stop_reason == "recovery_after_interrupted_motion"
        assert status.outputs.stopped
        assert not any(event[0] == "drive" for event in hardware.history)
    finally:
        controller.stop()


def test_fault_is_latched_across_restart_until_explicit_safe_reset(tmp_path):
    controller, hardware, repository = make_controller(tmp_path)
    repository.initialize()
    repository.mark_fault("previous_output_fault")

    controller.start()
    try:
        assert controller.get_status().state == ControlState.FAULT
        assert controller.get_status().fault == "previous_output_fault"

        movement = ControlCommand(CommandType.MOVE_UP)
        controller.submit(movement)
        wait_until(lambda: result_is(controller, movement, CommandLifecycle.FAILED))
        assert not any(event[0] == "drive" for event in hardware.history)

        reset = ControlCommand(CommandType.RESET_FAULT)
        controller.submit(reset)
        wait_until(lambda: result_is(controller, reset, CommandLifecycle.COMPLETED))
        assert controller.get_status().state == ControlState.IDLE
        assert controller.get_status().fault is None
        assert repository.load().last_error is None
    finally:
        controller.stop()
