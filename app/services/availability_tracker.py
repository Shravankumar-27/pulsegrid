from app.models.availability_state import AvailabilityState


def get_new_sessions(
    sessions: list[dict],
    state: AvailabilityState,
) -> list[dict]:
    new_sessions = []

    for session in sessions:
        session_id = session.get("id")

        if not session_id:
            continue

        if state.is_new(session_id):
            new_sessions.append(session)
            state.mark_seen(session_id)

    return new_sessions