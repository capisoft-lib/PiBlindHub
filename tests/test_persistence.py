from piblindhub.domain import Direction, PositionConfidence
from piblindhub.persistence import StateRepository


def test_interrupted_movement_marker_survives_and_can_be_invalidated(tmp_path):
    repository = StateRepository(str(tmp_path / "state.db"))
    repository.initialize()
    repository.set_estimated_position(42.0, "test")
    repository.mark_movement_started(Direction.DOWN)

    interrupted = repository.load()
    assert interrupted.movement_active is True
    assert interrupted.direction == Direction.DOWN

    position = repository.mark_position_unknown("power_loss")
    recovered = repository.load()
    assert position.confidence == PositionConfidence.UNKNOWN
    assert recovered.movement_active is False
    assert recovered.position.value is None
    assert recovered.last_stop_reason == "power_loss"


def test_event_log_is_bounded_by_requested_limit(tmp_path):
    repository = StateRepository(str(tmp_path / "state.db"))
    repository.initialize()
    for index in range(5):
        repository.append_event("test", {"index": index})

    events = repository.recent_events(2)

    assert [event["details"]["index"] for event in events] == [4, 3]


def test_stop_does_not_clear_latched_error_unless_explicitly_requested(tmp_path):
    repository = StateRepository(str(tmp_path / "state.db"))
    repository.initialize()
    repository.mark_fault("latched")

    repository.mark_stopped(
        repository.load().position,
        "stop_while_faulted",
        clear_error=False,
    )
    assert repository.load().last_error == "latched"

    repository.clear_fault("operator_reset")
    assert repository.load().last_error is None
