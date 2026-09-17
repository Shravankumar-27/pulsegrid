from datetime import date, datetime,timezone

from app.database import SessionLocal
from app.models.tracking_job import TrackingJob
from app.worker.runner import (
    complete_expired_jobs,
    get_running_jobs,
    is_job_expired,
    run_worker_cycle,
)


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