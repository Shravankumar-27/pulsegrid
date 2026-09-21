import pytest
from pydantic import ValidationError

from app.schemas.tracking_job import normalize_platform, TrackingJobCreate
from datetime import date, datetime, timezone


def test_normalize_platform_aliases():
    assert normalize_platform("BookMyShow") == "bookmyshow"
    assert normalize_platform("BMS") == "bookmyshow"
    assert normalize_platform("district.in") == "district"
    assert normalize_platform("District") == "district"
    assert normalize_platform("mock") == "mock"


def test_normalize_platform_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported platform"):
        normalize_platform("ticketnew")


def test_create_schema_normalizes_platform():
    job = TrackingJobCreate(
        target_name="ET123",
        platform="BookMyShow",
        city="Hyderabad",
        theater="Any",
        target_date=date(2026, 9, 21),
        start_at=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 21, 23, 59, tzinfo=timezone.utc),
        poll_interval_seconds=60,
    )
    assert job.platform == "bookmyshow"


def test_create_schema_rejects_bad_platform():
    with pytest.raises(ValidationError):
        TrackingJobCreate(
            target_name="ET123",
            platform="nope",
            city="Hyderabad",
            theater="Any",
            target_date=date(2026, 9, 21),
            start_at=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 21, 23, 59, tzinfo=timezone.utc),
        )
