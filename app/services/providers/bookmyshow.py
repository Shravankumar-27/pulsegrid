"""
BookMyShow provider.

Wraps BookMyShowClient, parses the raw API response, and returns an
AvailabilityResult for the PulseGrid worker.
"""

from app.models.tracking_job import TrackingJob
from app.services.providers.base import BaseProvider
from app.services.providers.bookmyshow_client import BookMyShowClient
from app.services.providers.result import AvailabilityResult
from app.services.providers.matcher import matching_sessions
from app.services.providers.bookmyshow_config import get_city_config
from app.services.providers.bookmyshow_response import classify_response
from app.services.providers.normalize import (
    session_dicts_from_shows,
    shows_from_bms_sessions,
)


# ---------------------------------------------------------------------------
# availStatus codes as returned by BMS (string values in additionalData)
# ---------------------------------------------------------------------------
#  "2" → Available          (green pill)
#  "3" → Fast filling       (orange pill)
#  "4" → Almost full        (red pill)
#  "1" → Sold out / closed  (grey — not bookable)
_BOOKABLE_AVAIL_STATUSES = {"2", "3", "4"}


def collect_venue_cards(value):
    """
    Recursively walk the BMS widget tree and collect every node whose
    ``type`` is ``"venue-card"``.
    """
    cards = []

    if isinstance(value, dict):
        if value.get("type") == "venue-card":
            cards.append(value)

        for child in value.values():
            cards.extend(collect_venue_cards(child))

    elif isinstance(value, list):
        for item in value:
            cards.extend(collect_venue_cards(item))

    return cards


def extract_sessions(data: dict) -> list[dict]:
    """
    Extract normalised session dicts from a raw BMS primary-dynamic response.

    BMS response structure (relevant part):
    ::

        data.showtimeWidgets[]
          type == "groupList"
            data[]                         ← venueGroup items
              data[]                       ← venue-card items
                additionalData.venueName   ← theatre name
                additionalData.venueCode   ← theatre code
                showtimesSections[]
                  showtimes[]
                    title                  ← display time e.g. "10:50 PM"
                    screenAttr             ← format e.g. "DOLBY ATMOS"
                    additionalData
                      sessionId            ← unique session identifier
                      availStatus          ← "1" sold / "2" avail / "3" fast / "4" almost
                      showTime             ← "10:50 PM"
                      showDateTime         ← "202609182250"
                      attributes           ← format description
    """
    widgets = data.get("data", {}).get("showtimeWidgets", [])

    sessions = []

    for venue_card in collect_venue_cards(widgets):
        add = venue_card.get("additionalData") or {}
        venue_name = add.get("venueName") or "Unknown Theater"
        venue_code = add.get("venueCode") or ""

        for section in venue_card.get("showtimesSections", []):
            for showtime in section.get("showtimes", []):
                if not isinstance(showtime, dict):
                    continue

                st_add = showtime.get("additionalData") or {}

                session_id   = st_add.get("sessionId")
                show_time    = st_add.get("showTime") or showtime.get("title")
                show_dt      = st_add.get("showDateTime")
                avail_status = str(st_add.get("availStatus", "0"))
                fmt          = (
                    st_add.get("attributes")
                    or showtime.get("screenAttr")
                    or ""
                )

                sessions.append(
                    {
                        "id":           session_id,
                        "cinema":       venue_name,
                        "venue_code":   venue_code,
                        "time":         show_time,
                        "show_dt":      show_dt,
                        "format":       fmt,
                        "avail_status": avail_status,
                    }
                )

    return sessions


def is_session_available(session: dict) -> bool:
    """
    Return True if the session has seats available for booking.

    Uses the ``avail_status`` field extracted from BMS ``additionalData``:
    - "2" Available
    - "3" Fast filling
    - "4" Almost full
    """
    return session.get("avail_status", "0") in _BOOKABLE_AVAIL_STATUSES


class BookMyShowProvider(BaseProvider):

    def __init__(self, client=None):
        self.client = client or BookMyShowClient()

    async def check(self, job: TrackingJob) -> dict:
        config = get_city_config(job.city)

        try:
            data = await self.client.fetch_showtimes(
                event_code=job.target_name,
                date_code=job.target_date.strftime("%Y%m%d"),
                region_code=config.region_code,
                region_slug=config.region_slug,
                latitude=config.latitude,
                longitude=config.longitude,
            )
        except Exception as exc:
            return {
                "available": False,
                "error":     True,
                "message":   f"BookMyShow check failed: {exc}",
                "sessions":  [],
            }

        response_type = classify_response(data)

        if response_type == "invalid":
            return AvailabilityResult(
                available=False,
                message="BookMyShow returned an unexpected response.",
                sessions=[],
            ).to_dict()

        if response_type == "not_on_sale":
            return AvailabilityResult(
                available=False,
                message="BookMyShow showtimes are not currently on sale.",
                sessions=[],
            ).to_dict()

        sessions = extract_sessions(data)

        matched_sessions = [
            session
            for session in matching_sessions(job, sessions)
            if is_session_available(session)
        ]

        if not matched_sessions:
            return AvailabilityResult(
                available=False,
                message="No matching showtimes currently available.",
                sessions=[],
            ).to_dict()

        shows = shows_from_bms_sessions(
            matched_sessions,
            movie_id=job.target_name,
            city=job.city,
        )
        normalized_sessions = session_dicts_from_shows(shows)

        return AvailabilityResult(
            available=True,
            message=(
                f"{len(normalized_sessions)} matching showtime(s) "
                f"found on BookMyShow."
            ),
            sessions=normalized_sessions,
        ).to_dict()
