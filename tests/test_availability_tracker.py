from app.models.availability_state import AvailabilityState
from app.services.availability_tracker import get_new_sessions


def test_new_sessions_are_returned():
    state = AvailabilityState(seen_session_ids=set())

    sessions = [
        {"id": "session-1"},
        {"id": "session-2"},
    ]

    result = get_new_sessions(sessions, state)

    assert len(result) == 2
    assert result[0]["id"] == "session-1"
    assert result[1]["id"] == "session-2"


def test_seen_sessions_are_not_returned_again():
    state = AvailabilityState(
        seen_session_ids={"session-1"},
    )

    sessions = [
        {"id": "session-1"},
        {"id": "session-2"},
    ]

    result = get_new_sessions(sessions, state)

    assert len(result) == 1
    assert result[0]["id"] == "session-2"


def test_new_session_is_marked_seen():
    state = AvailabilityState(seen_session_ids=set())

    sessions = [
        {"id": "session-1"},
    ]

    get_new_sessions(sessions, state)

    assert "session-1" in state.seen_session_ids


def test_sessions_without_id_are_ignored():
    state = AvailabilityState(seen_session_ids=set())

    sessions = [
        {"id": None},
        {"time": "19:30"},
    ]

    result = get_new_sessions(sessions, state)

    assert result == []