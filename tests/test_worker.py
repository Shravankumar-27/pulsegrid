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
    process_running_job,
)
from tests.fakes import FakeNotificationService

from types import SimpleNamespace

from app.worker.state import WorkerState

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




@pytest.mark.asyncio
async def test_process_running_job_uses_provider_factory(monkeypatch):
    calls = {}

    class FakeProvider:
        async def check(self, job):
            calls["job"] = job
            return {
                "available": False,
                "message": "No availability",
            }

    def fake_get_provider(platform):
        calls["platform"] = platform
        return FakeProvider()

    async def fake_process_job(job, provider, notification_service):
        calls["provider"] = provider
        return "checked"

    monkeypatch.setattr(
        "app.worker.runner.get_provider",
        fake_get_provider,
    )
    monkeypatch.setattr(
        "app.worker.runner.process_job",
        fake_process_job,
    )

    job = type("Job", (), {"platform": "bookmyshow"})()

    result = await process_running_job(
        job,
        notification_service=None,
    )

    assert result == "checked"
    assert calls["platform"] == "bookmyshow"
    assert isinstance(calls["provider"], FakeProvider)

@pytest.mark.asyncio
async def test_process_job_notifies_only_new_sessions():
    from app.models.availability_state import AvailabilityState
    from app.worker.runner import process_job

    class FakeProvider:
        async def check(self, job):
            return {
                "available": True,
                "message": "Showtime available",
                "sessions": [
                    {
                        "id": "session-1",
                        "cinema": "PVR Hyderabad",
                        "time": "19:30",
                    }
                ],
            }

    class FakeNotificationService:
        def __init__(self):
            self.messages = []

        async def send(self, recipient, message):
            self.messages.append((recipient, message))

    job = SimpleNamespace(
        id=1,
        status="RUNNING",
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_checked_at=None,
        poll_interval_seconds=0,
        user=SimpleNamespace(telegram_user_id=123),
        target_name="ET123",
        platform="bookmyshow",
        city="Hyderabad",
        theater="PVR",
    )

    notifications = FakeNotificationService()
    state = WorkerState()

    await process_job(
        job,
        FakeProvider(),
        notifications,
        worker_state=state,
    )

    await process_job(
        job,
        FakeProvider(),
        notifications,
        worker_state=state,
    )

    assert len(notifications.messages) == 1

@pytest.mark.asyncio
async def test_process_job_notifies_when_new_session_appears():
    from app.worker.runner import process_job

    class FakeProvider:
        def __init__(self):
            self.calls = 0

        async def check(self, job):
            self.calls += 1

            if self.calls == 1:
                sessions = [
                    {
                        "id": "session-1",
                        "cinema": "PVR Hyderabad",
                        "time": "19:30",
                    }
                ]
            else:
                sessions = [
                    {
                        "id": "session-1",
                        "cinema": "PVR Hyderabad",
                        "time": "19:30",
                    },
                    {
                        "id": "session-2",
                        "cinema": "PVR Hyderabad",
                        "time": "21:30",
                    },
                ]

            return {
                "available": True,
                "message": "Showtime available",
                "sessions": sessions,
            }

    class FakeNotificationService:
        def __init__(self):
            self.messages = []

        async def send(self, recipient, message):
            self.messages.append(message)

    job = SimpleNamespace(
        id=1,
        status="RUNNING",
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_checked_at=None,
        poll_interval_seconds=0,
        user=SimpleNamespace(telegram_user_id=123),
        target_name="ET123",
        platform="bookmyshow",
        city="Hyderabad",
        theater="PVR",
    )

    provider = FakeProvider()
    notifications = FakeNotificationService()
    state = WorkerState()

    await process_job(
        job,
        provider,
        notifications,
        worker_state=state,
    )

    await process_job(
        job,
        provider,
        notifications,
        worker_state=state,
    )

    assert len(notifications.messages) == 2
    assert "21:30" in notifications.messages[1]

def test_notification_message_contains_session_details():
    job = SimpleNamespace(
        target_name="ET123",
        platform="bookmyshow",
        city="Hyderabad",
        theater="PVR",
    )

    result = {
        "available": True,
        "sessions": [
            {
                "id": "session-123",
                "cinema": "PVR Nexus Mall",
                "time": "19:30",
                "format": "IMAX",
            }
        ],
    }

    message = build_notification_message(job, result)

    assert "ET123" in message
    assert "bookmyshow" in message
    assert "Hyderabad" in message
    assert "PVR Nexus Mall" in message
    assert "19:30" in message
    assert "IMAX" in message
    assert "session-123" in message

@pytest.mark.asyncio
async def test_worker_cycle_uses_provider_factory(
    monkeypatch,
):
    from app.services.providers.mock import MockProvider

    calls = []

    class FakeProvider:
        async def check(self, job):
            calls.append(job.platform)

            return {
                "available": False,
                "message": "No availability",
                "sessions": [],
            }

    def fake_get_provider(platform):
        calls.append(f"factory:{platform}")
        return FakeProvider()

    monkeypatch.setattr(
        "app.worker.runner.get_provider",
        fake_get_provider,
    )

    job = SimpleNamespace(
        id=1,
        status="RUNNING",
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_checked_at=None,
        poll_interval_seconds=0,
        platform="bookmyshow",
    )

    class FakeQuery:
        def filter(self, *args):
            return self

        def all(self):
            return [job]

    class FakeDB:
        def query(self, model):
            return FakeQuery()

        def commit(self):
            pass

    result = await run_worker_cycle(
        FakeDB(),
        provider=None,
        notification_service=None,
    )

    assert result["checked"] == 1
    assert calls == [
        "factory:bookmyshow",
        "bookmyshow",
    ]

@pytest.mark.asyncio
async def test_worker_cycle_deduplicates_sessions():
    state = WorkerState()

    class FakeProvider:
        async def check(self, job):
            return {
                "available": True,
                "message": "Showtime available",
                "sessions": [
                    {
                        "id": "session-1",
                        "cinema": "PVR Hyderabad",
                        "time": "19:30",
                        "format": "IMAX",
                    }
                ],
            }

    class FakeNotificationService:
        def __init__(self):
            self.messages = []

        async def send(self, recipient, message):
            self.messages.append(message)

    job = SimpleNamespace(
        id=1,
        status="RUNNING",
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_checked_at=None,
        poll_interval_seconds=0,
        user=SimpleNamespace(telegram_user_id=123),
        target_name="ET123",
        platform="bookmyshow",
        city="Hyderabad",
        theater="PVR",
    )

    class FakeQuery:
        def filter(self, *args):
            return self

        def all(self):
            return [job]

    class FakeDB:
        def query(self, model):
            return FakeQuery()

        def commit(self):
            pass

    notifications = FakeNotificationService()
    provider = FakeProvider()

    first = await run_worker_cycle(
        FakeDB(),
        provider=provider,
        notification_service=notifications,
        worker_state=state,
    )

    job.last_checked_at = None

    second = await run_worker_cycle(
        FakeDB(),
        provider=provider,
        notification_service=notifications,
        worker_state=state,
    )

    assert first["checked"] == 1
    assert first["notified"] == 1

    assert second["checked"] == 1
    assert second["notified"] == 0

    assert len(notifications.messages) == 1