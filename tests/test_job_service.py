import pytest
from datetime import date, datetime, timezone

from app.models.tracking_job import TrackingJob
from app.services.job_service import (
    InvalidJobTransition,
    change_job_status,
)


@pytest.fixture
def sample_job(db_session):
    job = TrackingJob(
        user_id=1,
        target_name="Test Target",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 20),
        start_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        poll_interval_seconds=60,
        status="PENDING",
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return job


def test_pending_to_running(db_session, sample_job):
    change_job_status(db_session, sample_job, "RUNNING")

    assert sample_job.status == "RUNNING"


def test_running_to_paused(db_session, sample_job):
    sample_job.status = "RUNNING"
    db_session.commit()

    change_job_status(db_session, sample_job, "PAUSED")

    assert sample_job.status == "PAUSED"


def test_paused_to_running(db_session, sample_job):
    sample_job.status = "PAUSED"
    db_session.commit()

    change_job_status(db_session, sample_job, "RUNNING")

    assert sample_job.status == "RUNNING"


def test_running_to_completed(db_session, sample_job):
    sample_job.status = "RUNNING"
    db_session.commit()

    change_job_status(db_session, sample_job, "COMPLETED")

    assert sample_job.status == "COMPLETED"


def test_invalid_pending_to_paused(db_session, sample_job):
    with pytest.raises(InvalidJobTransition):
        change_job_status(db_session, sample_job, "PAUSED")