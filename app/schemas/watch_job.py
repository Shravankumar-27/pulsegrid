from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.tracking_job import (
    TrackingJobResponse,
    normalize_platform,
)
from app.schemas.theater import TheaterResponse


class WatchJobCreate(BaseModel):
    """Dashboard create payload: one movie, one or both platforms."""

    movie_name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)

    start_at: datetime
    end_at: datetime

    platforms: list[str] = Field(min_length=1)

    bookmyshow_target: str | None = Field(default=None, max_length=200)
    district_target: str | None = Field(default=None, max_length=200)

    theater_id: int | None = None
    theater_name: str | None = Field(default=None, max_length=200)
    bookmyshow_venue_id: str | None = Field(default=None, max_length=100)
    district_venue_id: str | None = Field(default=None, max_length=100)

    poll_interval_seconds: int = Field(default=60, ge=10)
    start_immediately: bool = True

    @field_validator("movie_name", "city", mode="before")
    @classmethod
    def strip_required(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "bookmyshow_target",
        "district_target",
        "theater_name",
        "bookmyshow_venue_id",
        "district_venue_id",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("platforms", mode="before")
    @classmethod
    def normalize_platforms(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = [value]
        return [normalize_platform(str(item)) for item in value]

    @model_validator(mode="after")
    def validate_payload(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")

        platforms = list(dict.fromkeys(self.platforms))
        if not platforms:
            raise ValueError("Select at least one platform")
        for platform in platforms:
            if platform not in {"bookmyshow", "district"}:
                raise ValueError(
                    "Dashboard watch supports bookmyshow and district only"
                )
        self.platforms = platforms

        if "bookmyshow" in platforms and not self.bookmyshow_target:
            raise ValueError("bookmyshow_target (ET code) is required")
        if "district" in platforms and not self.district_target:
            raise ValueError("district_target (MV code) is required")

        if self.theater_id is None and not self.theater_name:
            self.theater_name = "Any"

        return self


class WatchJobResponse(BaseModel):
    jobs: list[TrackingJobResponse]
    theater: TheaterResponse | None = None
