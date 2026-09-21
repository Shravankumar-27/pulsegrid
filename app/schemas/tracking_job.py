from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_PLATFORMS = frozenset({"bookmyshow", "district", "mock"})

_PLATFORM_ALIASES = {
    "bookmyshow": "bookmyshow",
    "bms": "bookmyshow",
    "district": "district",
    "districtin": "district",
    "mock": "mock",
}


def normalize_platform(value: str) -> str:
    key = (
        value.strip()
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
    )
    normalized = _PLATFORM_ALIASES.get(key)
    if normalized is None:
        allowed = ", ".join(sorted(ALLOWED_PLATFORMS))
        raise ValueError(
            f"Unsupported platform {value!r}. Use one of: {allowed}"
        )
    return normalized


class TrackingJobCreate(BaseModel):
    target_name: str = Field(min_length=1, max_length=200)
    platform: str = Field(min_length=1, max_length=30)
    city: str = Field(min_length=1, max_length=100)
    theater: str = Field(min_length=1, max_length=200)

    movie_name: str | None = Field(default=None, max_length=200)
    theater_id: int | None = None

    target_date: date

    start_at: datetime
    end_at: datetime

    poll_interval_seconds: int = Field(default=60, ge=10)

    @field_validator("platform", mode="before")
    @classmethod
    def validate_platform(cls, value):
        if value is None:
            return value
        return normalize_platform(str(value))

    @field_validator("movie_name", mode="before")
    @classmethod
    def empty_movie_name(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")

        return self


class TrackingJobResponse(BaseModel):
    id: int
    user_id: int

    target_name: str
    platform: str
    city: str
    theater: str
    movie_name: str | None = None
    theater_id: int | None = None

    target_date: date

    start_at: datetime
    end_at: datetime

    poll_interval_seconds: int
    status: str

    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None

    last_result_json: dict | None = None

    @property
    def created_at_ist(self) -> str | None:
        from app.utils.time import format_ist
        return format_ist(self.created_at)

    @property
    def last_checked_at_ist(self) -> str | None:
        from app.utils.time import format_ist
        return format_ist(self.last_checked_at)

    model_config = {
        "from_attributes": True,
    }


class TrackingJobUpdate(BaseModel):
    target_name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: str | None = Field(default=None, min_length=1, max_length=30)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    theater: str | None = Field(default=None, min_length=1, max_length=200)
    movie_name: str | None = Field(default=None, max_length=200)
    theater_id: int | None = None

    target_date: date | None = None

    start_at: datetime | None = None
    end_at: datetime | None = None

    poll_interval_seconds: int | None = Field(default=None, ge=10)

    status: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("platform", mode="before")
    @classmethod
    def validate_platform(cls, value):
        if value is None or value == "":
            return value
        return normalize_platform(str(value))
