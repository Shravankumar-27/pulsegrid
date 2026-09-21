"""
District provider.

Fetches SSR showtimes from district.in and returns AvailabilityResult
for the PulseGrid worker.
"""

from __future__ import annotations

from app.models.tracking_job import TrackingJob
from app.services.providers.base import BaseProvider
from app.services.providers.district_client import DistrictClient
from app.services.providers.district_config import get_city_config
from app.services.providers.district_response import (
    classify_response,
    extract_sessions,
)
from app.services.providers.matcher import matching_sessions
from app.services.providers.normalize import (
    session_dicts_from_shows,
    shows_from_district_sessions,
)
from app.services.providers.result import AvailabilityResult

_BOOKABLE = {"2", "3", "4"}


def is_session_available(session: dict) -> bool:
    return session.get("avail_status", "0") in _BOOKABLE


class DistrictProvider(BaseProvider):
    def __init__(self, client=None):
        self.client = client or DistrictClient()

    async def check(self, job: TrackingJob) -> dict:
        try:
            config = get_city_config(job.city)
        except ValueError as exc:
            return {
                "available": False,
                "error": True,
                "message": str(exc),
                "sessions": [],
            }

        try:
            page_props = await self.client.fetch_showtimes(
                movie_ref=job.target_name,
                city_slug=config.city_slug,
                date_code=job.target_date.isoformat(),
            )
        except Exception as exc:
            return {
                "available": False,
                "error": True,
                "message": f"District check failed: {exc}",
                "sessions": [],
            }

        response_type = classify_response(page_props)
        if response_type == "invalid":
            return AvailabilityResult(
                available=False,
                message="District returned an unexpected response.",
                sessions=[],
            ).to_dict()

        if response_type == "not_on_sale":
            return AvailabilityResult(
                available=False,
                message="District showtimes are not currently on sale.",
                sessions=[],
            ).to_dict()

        sessions = extract_sessions(page_props)
        matched = [
            session
            for session in matching_sessions(job, sessions)
            if is_session_available(session)
        ]

        if not matched:
            return AvailabilityResult(
                available=False,
                message="No matching showtimes currently available.",
                sessions=[],
            ).to_dict()

        shows = shows_from_district_sessions(
            matched,
            movie_id=job.target_name,
            city=job.city,
        )
        normalized = session_dicts_from_shows(shows)

        return AvailabilityResult(
            available=True,
            message=(
                f"{len(normalized)} matching showtime(s) found on District."
            ),
            sessions=normalized,
        ).to_dict()
