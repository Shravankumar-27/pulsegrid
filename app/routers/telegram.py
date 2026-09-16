from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.telegram_commands import (
    handle_help,
    handle_job,
    handle_jobs,
    handle_pause,
    handle_resume,
    handle_start,
    handle_stop,
)

router = APIRouter(
    prefix="/api/v1/telegram",
    tags=["telegram"],
)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    update = await request.json()

    message = update.get("message")

    if message is None:
        return {"ok": True}

    user_data = message.get("from", {})
    chat = message.get("chat", {})

    telegram_user_id = user_data.get("id")
    chat_id = chat.get("id")
    text = message.get("text")

    if telegram_user_id is None or chat_id is None:
        return {"ok": True}

    pulsegrid_user = (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id)
        .first()
    )

    if pulsegrid_user is None:
        from app.services.telegram import send_message

        await send_message(
            chat_id,
            "You are not authorized to use PulseGrid.",
        )
        return {"ok": True}

    if pulsegrid_user.status != "ACTIVE":
        from app.services.telegram import send_message

        await send_message(
            chat_id,
            "Your PulseGrid account is not active.",
        )
        return {"ok": True}

    if not text:
        return {"ok": True}

    parts = text.strip().split(maxsplit=1)

    command = parts[0].lower()
    argument = parts[1] if len(parts) > 1 else ""

    if command == "/start":
        await handle_start(chat_id)

    elif command == "/help":
        await handle_help(chat_id)

    elif command == "/jobs":
        await handle_jobs(
            chat_id,
            db,
            pulsegrid_user,
        )

    elif command == "/job":
        await handle_job(
            chat_id,
            db,
            pulsegrid_user,
            argument,
        )

    elif command == "/stop":
        await handle_stop(
            chat_id,
            db,
            pulsegrid_user,
            argument,
        )
    elif command == "/pause":
        await handle_pause(
            chat_id,
            db,
            pulsegrid_user,
            argument,
        )

    elif command == "/resume":
        await handle_resume(
            chat_id,
            db,
            pulsegrid_user,
            argument,
        )
    else:
        from app.services.telegram import send_message

        await send_message(
            chat_id,
            "I don't understand that command.\n"
            "Use /help to see available commands.",
        )

    return {"ok": True}