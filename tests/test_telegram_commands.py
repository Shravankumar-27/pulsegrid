import pytest

from app.services.telegram_commands import (
    handle_delete,
    handle_status,
    handle_track,
    parse_track_command,
    route_command,
    parse_command,
)

@pytest.mark.asyncio
async def test_route_start(monkeypatch, db_session):
    called = {}

    async def fake_handle_start(chat_id):
        called["chat_id"] = chat_id

    monkeypatch.setattr(
        "app.services.telegram_commands.handle_start",
        fake_handle_start,
    )

    await route_command(
        command="/start",
        argument="",
        chat_id=12345,
        db=db_session,
        user=None,
    )

    assert called == {
        "chat_id": 12345,
    }


@pytest.mark.asyncio
async def test_route_help(monkeypatch, db_session):
    called = {}

    async def fake_handle_help(chat_id):
        called["chat_id"] = chat_id

    monkeypatch.setattr(
        "app.services.telegram_commands.handle_help",
        fake_handle_help,
    )

    await route_command(
        command="/help",
        argument="",
        chat_id=12345,
        db=db_session,
        user=None,
    )

    assert called == {
        "chat_id": 12345,
    }


@pytest.mark.asyncio
async def test_route_job(monkeypatch, db_session):
    called = {}

    async def fake_handle_job(chat_id, db, user, argument):
        called.update(
            {
                "chat_id": chat_id,
                "db": db,
                "user": user,
                "argument": argument,
            }
        )

    monkeypatch.setattr(
        "app.services.telegram_commands.handle_job",
        fake_handle_job,
    )

    user = object()

    await route_command(
        command="/job",
        argument="42",
        chat_id=12345,
        db=db_session,
        user=user,
    )

    assert called["chat_id"] == 12345
    assert called["db"] is db_session
    assert called["user"] is user
    assert called["argument"] == "42"


@pytest.mark.asyncio
async def test_route_unknown_command(monkeypatch, db_session):
    called = {}

    async def fake_send_message(chat_id, message):
        called["chat_id"] = chat_id
        called["message"] = message

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    await route_command(
        command="/unknown",
        argument="",
        chat_id=12345,
        db=db_session,
        user=None,
    )

    assert called["chat_id"] == 12345
    assert "don't understand" in called["message"]
    assert "/help" in called["message"]

def test_parse_track_command():
    result = parse_track_command(
        "Panja\n"
        "BookMyShow\n"
        "Hyderabad\n"
        "AMB Cinemas\n"
        "2026-09-20\n"
        "18:00\n"
        "21:00\n"
        "60"
    )

    assert result.target_name == "Panja"
    assert result.platform == "bookmyshow"
    assert result.city == "Hyderabad"
    assert result.theater == "AMB Cinemas"
    assert result.target_date.isoformat() == "2026-09-20"
    assert result.poll_interval_seconds == 60
    assert result.start_at.hour == 18
    assert result.end_at.hour == 21



def test_parse_track_command_rejects_wrong_field_count():
    with pytest.raises(ValueError, match="Usage"):
        parse_track_command(
            "Panja\n"
            "BookMyShow\n"
            "Hyderabad"
        )


def test_parse_track_command_rejects_invalid_date():
    with pytest.raises(ValueError, match="Invalid date"):
        parse_track_command(
            "Panja \n BookMyShow \n Hyderabad \n AMB Cinemas \n "
            "20-09-2026 \n 18:00 \n 21:00 \n 60"
        )


def test_parse_track_command_rejects_invalid_time():
    with pytest.raises(ValueError, match="Invalid date"):
        parse_track_command(
            "Panja \n BookMyShow \n Hyderabad \n AMB Cinemas \n "
            "2026-09-20 \n 25:00 \n 21:00 \n 60"
        )


def test_parse_track_command_rejects_invalid_poll_interval():
    with pytest.raises(ValueError):
        parse_track_command(
            "Panja \n BookMyShow \n Hyderabad \n AMB Cinemas \n "
            "2026-09-20 \n 18:00 \n 21:00 \n abc"
        )

@pytest.mark.asyncio
async def test_handle_track_creates_job(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(
            {
                "chat_id": chat_id,
                "message": message,
            }
        )

    def fake_create_tracking_job(db, user, job_data):
        return type(
            "FakeJob",
            (),
            {
                "id": 12,
                "target_name": job_data.target_name,
                "platform": job_data.platform,
                "city": job_data.city,
                "theater": job_data.theater,
                "target_date": job_data.target_date,
                "start_at": job_data.start_at,
                "end_at": job_data.end_at,
                "poll_interval_seconds": job_data.poll_interval_seconds,
                "status": "PENDING",
            },
        )()

    def fake_change_job_status(db, job, new_status):
        job.status = new_status
        return job

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.create_tracking_job",
        fake_create_tracking_job,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.change_job_status",
        fake_change_job_status,
    )

    await handle_track(
        chat_id=123,
        db=object(),
        user=object(),
        argument=(
            "Panja\n"
            "BookMyShow\n"
            "Hyderabad\n"
            "AMB Cinemas\n"
            "2026-09-20\n"
            "18:00\n"
            "21:00\n"
            "60"
        ),
    )

    assert len(sent_messages) == 1

    assert sent_messages[0]["chat_id"] == 123
    assert "Tracking job #12 created" in sent_messages[0]["message"]
    assert "Panja" in sent_messages[0]["message"]
    assert "bookmyshow" in sent_messages[0]["message"]
    assert "RUNNING" in sent_messages[0]["message"]

@pytest.mark.asyncio
async def test_handle_track_without_argument(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    await handle_track(
        chat_id=123,
        db=object(),
        user=object(),
        argument="",
    )

    assert len(sent_messages) == 1
    assert "Usage" in sent_messages[0]

@pytest.mark.asyncio
async def test_route_track_command(monkeypatch):
    captured = {}

    async def fake_handle_track(
        chat_id,
        db,
        user,
        argument,
    ):
        captured["chat_id"] = chat_id
        captured["db"] = db
        captured["user"] = user
        captured["argument"] = argument

    monkeypatch.setattr(
        "app.services.telegram_commands.handle_track",
        fake_handle_track,
    )

    db = object()
    user = object()

    await route_command(
        command="/track",
        argument=(
            "Panja\n"
            "BookMyShow\n"
            "Hyderabad\n"
            "AMB Cinemas\n"
            "2026-09-20\n"
            "18:00\n"
            "21:00\n"
            "60"
        ),
        chat_id=123,
        db=db,
        user=user,
    )

    assert captured["chat_id"] == 123
    assert captured["db"] is db
    assert captured["user"] is user

    assert captured["argument"] == (
        "Panja\n"
        "BookMyShow\n"
        "Hyderabad\n"
        "AMB Cinemas\n"
        "2026-09-20\n"
        "18:00\n"
        "21:00\n"
        "60"
    )

@pytest.mark.asyncio
async def test_handle_delete_requires_confirmation(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    def fake_get_job_for_user(db, job_id, user):
        return type(
            "FakeJob",
            (),
            {
                "id": 12,
                "target_name": "Panja",
                "theater": "AMB Cinemas",
            },
        )()

    deleted = {}

    def fake_delete_tracking_job(db, job_id, user):
        deleted["job_id"] = job_id
        deleted["user"] = user

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.get_job_for_user",
        fake_get_job_for_user,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.delete_tracking_job",
        fake_delete_tracking_job,
    )

    user = object()

    await handle_delete(
        chat_id=123,
        db=object(),
        user=user,
        argument="12",
    )

    assert "job_id" not in deleted
    assert len(sent_messages) == 1
    assert "#12" in sent_messages[0]
    assert "confirm" in sent_messages[0].lower()

@pytest.mark.asyncio
async def test_handle_delete_rejects_invalid_id(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    await handle_delete(
        chat_id=123,
        db=object(),
        user=object(),
        argument="abc",
    )

    assert len(sent_messages) == 1
    assert "must be a number" in sent_messages[0]

@pytest.mark.asyncio
async def test_handle_delete_not_found(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    def fake_get_job_for_user(db, job_id, user):
        raise ValueError("Job not found")

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.get_job_for_user",
        fake_get_job_for_user,
    )

    await handle_delete(
        chat_id=123,
        db=object(),
        user=object(),
        argument="999",
    )

    assert sent_messages == [
        "❌ Job not found.",
    ]

@pytest.mark.asyncio
async def test_handle_delete_requires_confirmation(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    def fake_get_job_for_user(db, job_id, user):
        return type(
            "FakeJob",
            (),
            {
                "id": 12,
                "target_name": "Panja",
                "theater": "AMB Cinemas",
            },
        )()

    deleted = {}

    def fake_delete_tracking_job(db, job_id, user):
        deleted["job_id"] = job_id
        deleted["user"] = user

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.get_job_for_user",
        fake_get_job_for_user,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.delete_tracking_job",
        fake_delete_tracking_job,
    )

    user = object()

    await handle_delete(
        chat_id=123,
        db=object(),
        user=user,
        argument="12",
    )

    assert "job_id" not in deleted
    assert len(sent_messages) == 1
    assert "#12" in sent_messages[0]
    assert "confirm" in sent_messages[0].lower()

@pytest.mark.asyncio
async def test_handle_delete_with_confirmation(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    def fake_get_job_for_user(db, job_id, user):
        return type(
            "FakeJob",
            (),
            {
                "id": 12,
                "target_name": "Panja",
                "theater": "AMB Cinemas",
            },
        )()

    deleted = {}

    def fake_delete_tracking_job(db, job_id, user):
        deleted["job_id"] = job_id

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.get_job_for_user",
        fake_get_job_for_user,
    )

    monkeypatch.setattr(
        "app.services.telegram_commands.delete_tracking_job",
        fake_delete_tracking_job,
    )

    await handle_delete(
        chat_id=123,
        db=object(),
        user=object(),
        argument="12 confirm",
    )

    assert deleted["job_id"] == 12
    assert len(sent_messages) == 1
    assert "deleted" in sent_messages[0].lower()

def test_parse_command_without_argument():
    command, argument = parse_command("/jobs")

    assert command == "/jobs"
    assert argument == ""

def test_parse_command_with_argument():
    command, argument = parse_command("/job 12")

    assert command == "/job"
    assert argument == "12"

def test_parse_command_with_multiline_argument():
    text = (
        "/track\n"
        "Panja\n"
        "BookMyShow\n"
        "Hyderabad\n"
        "AMB Cinemas\n"
        "2026-09-20\n"
        "18:00\n"
        "21:00\n"
        "60"
    )

    command, argument = parse_command(text)

    assert command == "/track"

    assert argument == (
        "Panja\n"
        "BookMyShow\n"
        "Hyderabad\n"
        "AMB Cinemas\n"
        "2026-09-20\n"
        "18:00\n"
        "21:00\n"
        "60"
    )

def test_parse_command_empty_text():
    command, argument = parse_command("")

    assert command == ""
    assert argument == ""

@pytest.mark.asyncio
async def test_handle_status_for_user(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id, message):
        sent_messages.append(message)

    class FakeJob:
        def __init__(self, status):
            self.status = status
            self.user_id = 10

    class FakeResult:
        def scalars(self):
            return self

        def all(self):
            return [
                FakeJob("RUNNING"),
                FakeJob("RUNNING"),
                FakeJob("PAUSED"),
                FakeJob("COMPLETED"),
            ]

    class FakeDB:
        def execute(self, query):
            return FakeResult()

    user = type(
        "FakeUser",
        (),
        {
            "id": 10,
            "role": "USER",
        },
    )()

    monkeypatch.setattr(
        "app.services.telegram_commands.send_message",
        fake_send_message,
    )

    await handle_status(
        chat_id=123,
        db=FakeDB(),
        user=user,
    )

    assert len(sent_messages) == 1

    message = sent_messages[0]

    assert "Total jobs: 4" in message
    assert "🟢 Running: 2" in message
    assert "⏸️ Paused: 1" in message
    assert "✅ Completed: 1" in message
    assert "🛑 Stopped: 0" in message

@pytest.mark.asyncio
async def test_route_status_command(monkeypatch):
    captured = {}

    async def fake_handle_status(chat_id, db, user):
        captured["chat_id"] = chat_id
        captured["db"] = db
        captured["user"] = user

    monkeypatch.setattr(
        "app.services.telegram_commands.handle_status",
        fake_handle_status,
    )

    db = object()
    user = object()

    await route_command(
        command="/status",
        argument="",
        chat_id=123,
        db=db,
        user=user,
    )

    assert captured["chat_id"] == 123
    assert captured["db"] is db
    assert captured["user"] is user

def test_parse_command_normalizes_whitespace():
    command, argument = parse_command(
        "   /STATUS   "
    )

    assert command == "/status"
    assert argument == ""

def test_parse_command_preserves_multiline_argument():
    command, argument = parse_command(
        "  /track  \n"
        "Panja\n"
        "BookMyShow\n"
        "Hyderabad\n"
        "AMB Cinemas\n"
        "2026-09-20\n"
        "18:00\n"
        "21:00\n"
        "60"
    )

    assert command == "/track"
    assert argument.startswith("Panja\n")
    assert argument.endswith("60")