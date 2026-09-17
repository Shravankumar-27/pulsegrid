from datetime import date, datetime,timezone

from app.database import SessionLocal
from app.models.tracking_job import TrackingJob
from app.worker.runner import (
    complete_expired_jobs,
    get_running_jobs,
    is_job_expired,
    process_job,
    run_worker_cycle,
    should_poll,
)
import pytest

from app.services.providers.mock import MockProvider

from datetime import date, datetime, timedelta, timezone

from tests.conftest import db_session

def test_get_running_jobs(db_session, monkeypatch):
    running_job = TrackingJob(
        user_id=1,
        target_name="Running Job",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 16, 19, 0, tzinfo=timezone.utc),
        poll_interval_seconds=60,
        status="RUNNING",
    )

    pending_job = TrackingJob(
        user_id=1,
        target_name="Pending Job",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 9, 16, 19, 0, tzinfo=timezone.utc),
        poll_interval_seconds=60,
        status="PENDING",
    )

    db_session.add_all([running_job, pending_job])
    db_session.commit()

    monkeypatch.setattr(
        "app.worker.runner.SessionLocal",
        lambda: db_session,
    )

    jobs = get_running_jobs()

    assert len(jobs) == 1
    assert jobs[0].status == "RUNNING"
    assert jobs[0].target_name == "Running Job"

def test_job_is_expired():
    job = TrackingJob(
    end_at=datetime.now(timezone.utc) - timedelta(minutes=1),
)

    assert is_job_expired(job) is True


def test_job_is_not_expired():
    job = TrackingJob(
        end_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )

    assert is_job_expired(job) is False


def test_complete_expired_jobs(db_session, monkeypatch):
    expired_job = TrackingJob(
        user_id=1,
        target_name="Expired Job",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime(
            2026, 9, 16, 17, 0, tzinfo=timezone.utc
        ),
        end_at=datetime(
            2026, 9, 16, 18, 0, tzinfo=timezone.utc
        ),
        poll_interval_seconds=60,
        status="RUNNING",
    )

    active_job = TrackingJob(
        user_id=1,
        target_name="Active Job",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime(
            2026, 9, 16, 17, 0, tzinfo=timezone.utc
        ),
        end_at=datetime(
            2099, 9, 16, 19, 0, tzinfo=timezone.utc
        ),
        poll_interval_seconds=60,
        status="RUNNING",
    )

    db_session.add_all([expired_job, active_job])
    db_session.commit()

    expired_job_id = expired_job.id
    active_job_id = active_job.id

    monkeypatch.setattr(
        "app.worker.runner.SessionLocal",
        lambda: db_session,
    )

    completed_count = complete_expired_jobs()

    assert completed_count == 1

def test_run_worker_cycle(monkeypatch):
    monkeypatch.setattr(
        "app.worker.runner.complete_expired_jobs",
        lambda: 3,
    )

    result = run_worker_cycle()

    assert result == {
        "completed": 3,
    }

@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockProvider()

    result = await provider.check(None)

    assert result == {
        "available": True,
        "message": "Mock provider check successful",
    }

def test_should_poll_when_never_checked():
    job = TrackingJob(
        last_checked_at=None,
        poll_interval_seconds=60,
    )

    assert should_poll(job) is True

def test_should_not_poll_before_interval():
    job = TrackingJob(
        last_checked_at=datetime.now(timezone.utc),
        poll_interval_seconds=60,
    )

    assert should_poll(job) is False

def test_should_poll_after_interval():
    job = TrackingJob(
        last_checked_at=datetime.now(timezone.utc) - timedelta(seconds=61),
        poll_interval_seconds=60,
    )

    assert should_poll(job) is True

@pytest.mark.asyncio
async def test_process_job_polls_job():
    job = TrackingJob(
        status="RUNNING",
        poll_interval_seconds=60,
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    provider = MockProvider()

    result = await process_job(job, provider)

    assert result["available"] is True
    assert job.last_checked_at is not None

@pytest.mark.asyncio
async def test_process_job_skips_when_not_due():
    job = TrackingJob(
        status="RUNNING",
        poll_interval_seconds=60,
        last_checked_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    
    provider = MockProvider()

    result = await process_job(job, provider)

    assert result == "skipped"

@pytest.mark.asyncio
async def test_process_job_completes_expired_job():
    job = TrackingJob(
        status="RUNNING",
        poll_interval_seconds=60,
        end_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    provider = MockProvider()

    result = await process_job(job, provider)

    assert result == "completed"
    assert job.status == "COMPLETED"