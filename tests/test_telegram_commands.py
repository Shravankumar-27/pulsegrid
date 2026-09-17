import pytest

from app.services.telegram_commands import route_command


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