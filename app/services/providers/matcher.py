_MATCH_ALL_THEATERS = {"", "any", "all", "*"}


def matches_job(job, session: dict) -> bool:
    theater = (job.theater or "").strip().lower()
    cinema = (session.get("cinema") or "").strip().lower()

    # Empty / "Any" / "All" → every venue
    if theater in _MATCH_ALL_THEATERS:
        return True

    if theater not in cinema:
        return False

    return True


def matching_sessions(job, sessions: list[dict]) -> list[dict]:
    return [
        session
        for session in sessions
        if matches_job(job, session)
    ]