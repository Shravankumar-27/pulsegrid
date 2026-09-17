from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.tracking_job import TrackingJob
from app.services.providers.mock import MockProvider
from app.worker.runner import (
    build_notification_message,
    complete_expired_jobs,
    get_running_jobs,
    is_job_expired,
    process_job,
    run_worker_cycle,
    should_poll,
)
from tests.fakes import FakeNotificationService


def create_user(db_session, telegram_user_id=123456789):
    from app.models.user import User

    user = User(
        telegram_user_id=telegram_user_id,
        name="Test User",
        role="USER",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()

    return user


def create_running_job(
    db_session,
    user,
    target_name="Test Job",
    end_at=None,
    last_checked_at=None,
    poll_interval_seconds=60,
):
    if end_at is None:
        end_at = datetime.now(timezone.utc) + timedelta(hours=1)

    job = TrackingJob(
        user_id=user.id,
        target_name=target_name,
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime.now(timezone.utc),
        end_at=end_at,
        poll_interval_seconds=poll_interval_seconds,
        status="RUNNING",
        last_checked_at=last_checked_at,
    )

    db_session.add(job)
    db_session.commit()

    return job


def test_get_running_jobs(db_session, monkeypatch):
    running_job = TrackingJob(
        user_id=1,
        target_name="Running Job",
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=date(2026, 9, 16),
        start_at=datetime(
            2026,
            9,
            16,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2099,
            9,
            16,
            19,
            0,
            tzinfo=timezone.utc,
        ),
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
        start_at=datetime(
            2026,
            9,
            16,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2099,
            9,
            16,
            19,
            0,
            tzinfo=timezone.utc,
        ),
        poll_interval_seconds=60,
        status="PENDING",
    )

    db_session.add_all(
        [
            running_job,
            pending_job,
        ]
    )

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
        end_at=datetime.now(timezone.utc)
        - timedelta(minutes=1),
    )

    assert is_job_expired(job) is True


def test_job_is_not_expired():
    job = TrackingJob(
        end_at=datetime.now(timezone.utc)
        + timedelta(minutes=1),
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
            2026,
            9,
            16,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2026,
            9,
            16,
            18,
            0,
            tzinfo=timezone.utc,
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
            2026,
            9,
            16,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2099,
            9,
            16,
            19,
            0,
            tzinfo=timezone.utc,
        ),
        poll_interval_seconds=60,
        status="RUNNING",
    )

    db_session.add_all(
        [
            expired_job,
            active_job,
        ]
    )

    db_session.commit()

    monkeypatch.setattr(
        "app.worker.runner.SessionLocal",
        lambda: db_session,
    )

    completed_count = complete_expired_jobs()

    assert completed_count == 1
    assert expired_job.status == "COMPLETED"
    assert active_job.status == "RUNNING"


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
        last_checked_at=(
            datetime.now(timezone.utc)
            - timedelta(seconds=61)
        ),
        poll_interval_seconds=60,
    )

    assert should_poll(job) is True


@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockProvider()

    result = await provider.check(None)

    assert result == {
        "available": True,
        "message": "Mock provider check successful",
    }


@pytest.mark.asyncio
async def test_process_job_polls_job(db_session):
    user = create_user(db_session)

    job = create_running_job(
        db_session,
        user,
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await process_job(
        job,
        provider,
        notification,
    )

    assert result["available"] is True
    assert job.last_checked_at is not None

    assert len(notification.sent) == 1
    assert (
        notification.sent[0]["recipient"]
        == str(user.telegram_user_id)
    )


@pytest.mark.asyncio
async def test_process_job_skips_when_not_due(db_session):
    user = create_user(db_session)

    job = create_running_job(
        db_session,
        user,
        last_checked_at=datetime.now(timezone.utc),
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await process_job(
        job,
        provider,
        notification,
    )

    assert result == "skipped"
    assert notification.sent == []


@pytest.mark.asyncio
async def test_process_job_completes_expired_job(db_session):
    user = create_user(db_session)

    job = create_running_job(
        db_session,
        user,
        end_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await process_job(
        job,
        provider,
        notification,
    )

    assert result == "completed"
    assert job.status == "COMPLETED"
    assert notification.sent == []


def test_build_notification_message(db_session):
    user = create_user(db_session)

    job = create_running_job(
        db_session,
        user,
        target_name="Test Movie",
    )

    result = {
        "available": True,
        "message": "Tickets are available",
    }

    message = build_notification_message(
        job,
        result,
    )

    assert "PulseGrid Alert" in message
    assert "Test Movie" in message
    assert "platform_a" in message
    assert "Hyderabad" in message
    assert "Test Theater" in message
    assert "Tickets are available" in message


@pytest.mark.asyncio
async def test_worker_cycle_processes_due_job(db_session):
    user = create_user(db_session)

    create_running_job(
        db_session,
        user,
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await run_worker_cycle(
        db_session,
        provider,
        notification,
    )

    assert result["checked"] == 1
    assert result["notified"] == 1
    assert result["completed"] == 0
    assert result["skipped"] == 0

    assert len(notification.sent) == 1


@pytest.mark.asyncio
async def test_worker_cycle_skips_non_due_job(db_session):
    user = create_user(db_session)

    create_running_job(
        db_session,
        user,
        last_checked_at=datetime.now(timezone.utc),
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await run_worker_cycle(
        db_session,
        provider,
        notification,
    )

    assert result["checked"] == 0
    assert result["skipped"] == 1
    assert result["notified"] == 0

    assert notification.sent == []


@pytest.mark.asyncio
async def test_worker_cycle_completes_expired_job(db_session):
    user = create_user(db_session)

    job = create_running_job(
        db_session,
        user,
        end_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await run_worker_cycle(
        db_session,
        provider,
        notification,
    )

    assert result["completed"] == 1
    assert result["checked"] == 0
    assert result["notified"] == 0
    assert job.status == "COMPLETED"
    assert notification.sent == []


@pytest.mark.asyncio
async def test_multiple_jobs_are_processed_independently(
    db_session,
):
    user = create_user(db_session)

    due_job = create_running_job(
        db_session,
        user,
        target_name="Due Job",
    )

    skipped_job = create_running_job(
        db_session,
        user,
        target_name="Skipped Job",
        last_checked_at=datetime.now(timezone.utc),
    )

    expired_job = create_running_job(
        db_session,
        user,
        target_name="Expired Job",
        end_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    )

    provider = MockProvider()
    notification = FakeNotificationService()

    result = await run_worker_cycle(
        db_session,
        provider,
        notification,
    )

    assert result["checked"] == 1
    assert result["skipped"] == 1
    assert result["completed"] == 1
    assert result["notified"] == 1

    assert due_job.last_checked_at is not None
    assert skipped_job.status == "RUNNING"
    assert expired_job.status == "COMPLETED"

    assert len(notification.sent) == 1
    assert "Due Job" in notification.sent[0]["message"]