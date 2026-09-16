from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class TrackingJobCreate(BaseModel):
    target_name: str = Field(min_length=1, max_length=200)
    platform: str = Field(min_length=1, max_length=30)
    city: str = Field(min_length=1, max_length=100)
    theater: str = Field(min_length=1, max_length=200)

    target_date: date

    start_at: datetime
    end_at: datetime

    poll_interval_seconds: int = Field(default=60, ge=10)

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

    target_date: date

    start_at: datetime
    end_at: datetime

    poll_interval_seconds: int
    status: str

    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }

class TrackingJobUpdate(BaseModel):
    target_name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: str | None = Field(default=None, min_length=1, max_length=30)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    theater: str | None = Field(default=None, min_length=1, max_length=200)

    target_date: date | None = None

    start_at: datetime | None = None
    end_at: datetime | None = None

    poll_interval_seconds: int | None = Field(default=None, ge=10)

    status: str | None = Field(default=None, min_length=1, max_length=20)