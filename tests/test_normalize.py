from datetime import datetime, timezone

from app.models.show import Show
from app.services.providers.normalize import (
    session_dicts_from_shows,
    shows_from_bms_sessions,
)


def test_shows_from_bms_sessions():
    sessions = [
        {
            "id": "118781",
            "cinema": "AMB Cinemas: Gachibowli",
            "venue_code": "AMBH",
            "time": "04:20 PM",
            "format": "DOLBY ATMOS",
            "avail_status": "3",
        }
    ]

    shows = shows_from_bms_sessions(
        sessions,
        movie_id="ET00514261",
        city="Hyderabad",
        language="telugu",
        observed_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
    )

    assert len(shows) == 1
    show = shows[0]
    assert isinstance(show, Show)
    assert show.provider == "bookmyshow"
    assert show.show_id == "118781"
    assert show.venue_id == "AMBH"
    assert show.availability == "3"
    assert show.movie_id == "ET00514261"

    session = show.to_session_dict()
    assert session["id"] == "118781"
    assert session["cinema"] == "AMB Cinemas: Gachibowli"

    assert session_dicts_from_shows(shows)[0]["id"] == "118781"


def test_skips_sessions_without_id():
    assert shows_from_bms_sessions([{"cinema": "PVR"}]) == []
