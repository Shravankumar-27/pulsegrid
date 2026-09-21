"""
Provider-agnostic show / session model for PulseGrid.

BookMyShow, District, and future providers normalize into this shape
before change-detection and notifications.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Show:
    provider: str
    show_id: str
    venue_id: str
    venue_name: str
    start_time: str
    format: str
    availability: str
    movie_id: str = ""
    movie_name: str = ""
    city: str = ""
    language: str = ""
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_session_dict(self) -> dict:
        """Worker-compatible session payload used by notifications/dedupe."""
        return {
            "id": self.show_id,
            "cinema": self.venue_name,
            "venue_code": self.venue_id,
            "time": self.start_time,
            "format": self.format,
            "avail_status": self.availability,
            "provider": self.provider,
            "movie_id": self.movie_id,
            "city": self.city,
            "language": self.language,
        }

    def to_dict(self) -> dict:
        data = asdict(self)
        data["observed_at"] = self.observed_at.isoformat()
        return data
