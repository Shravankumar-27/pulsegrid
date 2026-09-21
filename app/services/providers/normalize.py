"""
Normalize provider-specific session dicts into PulseGrid ``Show`` objects.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.show import Show


def shows_from_bms_sessions(
    sessions: list[dict],
    *,
    movie_id: str = "",
    movie_name: str = "",
    city: str = "",
    language: str = "",
    observed_at: datetime | None = None,
) -> list[Show]:
    """
    Convert BookMyShow ``extract_sessions`` output into ``Show`` models.
    """
    observed = observed_at or datetime.now(timezone.utc)
    shows: list[Show] = []

    for session in sessions:
        show_id = session.get("id")
        if not show_id:
            continue

        shows.append(
            Show(
                provider="bookmyshow",
                show_id=str(show_id),
                venue_id=str(session.get("venue_code") or ""),
                venue_name=str(session.get("cinema") or ""),
                start_time=str(session.get("time") or ""),
                format=str(session.get("format") or ""),
                availability=str(session.get("avail_status") or "0"),
                movie_id=movie_id,
                movie_name=movie_name,
                city=city,
                language=language,
                observed_at=observed,
            )
        )

    return shows


def session_dicts_from_shows(shows: list[Show]) -> list[dict]:
    return [show.to_session_dict() for show in shows]
