import pytest
from datetime import date, datetime, timezone

from app.models.tracking_job import TrackingJob
from app.services.job_service import (
    InvalidJobTransition,
    change_job_status,
)
from app.models.user import User
from app.schemas.tracking_job import TrackingJobCreate
from app.services.job_service import (
    create_tracking_job,
)

@pytest.fixture
def sample_job(db_session):
    job = TrackingJob(
        user_id=1,
        target_name="Test Target",
        platform="bookmyshow",
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

def test_create_tracking_job(db_session):
    user = User(
        telegram_user_id=987654321,
        name="Track Test User",
        role="USER",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()

    job_data = TrackingJobCreate(
        target_name="Panja",
        platform="bookmyshow",
        city="Hyderabad",
        theater="AMB Cinemas",
        target_date=date(2026, 9, 20),
        start_at=datetime(
            2026,
            9,
            20,
            18,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2026,
            9,
            20,
            21,
            0,
            tzinfo=timezone.utc,
        ),
        poll_interval_seconds=60,
    )

    job = create_tracking_job(
        db=db_session,
        user=user,
        job_data=job_data,
    )

    assert job.id is not None
    assert job.user_id == user.id
    assert job.target_name == "Panja"
    assert job.platform == "bookmyshow"
    assert job.city == "Hyderabad"
    assert job.theater == "AMB Cinemas"
    assert job.poll_interval_seconds == 60
    assert job.status == "PENDING"