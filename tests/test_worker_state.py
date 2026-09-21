from pathlib import Path

from app.worker.state import WorkerState


def test_same_job_returns_same_state():
    state = WorkerState()

    first = state.get_job_state(1)
    second = state.get_job_state(1)

    assert first is second


def test_different_jobs_have_different_state():
    state = WorkerState()

    first = state.get_job_state(1)
    second = state.get_job_state(2)

    assert first is not second


def test_state_persists_seen_sessions():
    state = WorkerState()

    job_state = state.get_job_state(1)
    job_state.mark_seen("session-1")

    same_job_state = state.get_job_state(1)

    assert "session-1" in same_job_state.seen_session_ids


def test_state_round_trips_to_disk(tmp_path: Path):
    path = tmp_path / "worker_state.json"
    state = WorkerState(persist_path=path)
    state.get_job_state(7).mark_seen("s-1")
    state.get_job_state(7).mark_seen("s-2")
    state.save()

    restored = WorkerState(persist_path=path)
    assert restored.get_job_state(7).seen_session_ids == {"s-1", "s-2"}
