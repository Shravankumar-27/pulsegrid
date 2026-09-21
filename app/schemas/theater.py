from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class TheaterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    bookmyshow_venue_id: str | None = Field(default=None, max_length=100)
    district_venue_id: str | None = Field(default=None, max_length=100)

    @field_validator("name", "city", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("bookmyshow_venue_id", "district_venue_id", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class TheaterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    bookmyshow_venue_id: str | None = Field(default=None, max_length=100)
    district_venue_id: str | None = Field(default=None, max_length=100)

    @field_validator("name", "city", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("bookmyshow_venue_id", "district_venue_id", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class TheaterResponse(BaseModel):
    id: int
    user_id: int
    name: str
    city: str
    bookmyshow_venue_id: str | None = None
    district_venue_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
