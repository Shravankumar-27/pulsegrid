from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.telegram_commands import (
    parse_command,
    route_command,
)
from app.services.telegram import send_message

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
        await send_message(
            chat_id,
            "You are not authorized to use PulseGrid.",
        )
        return {"ok": True}

    if pulsegrid_user.status != "ACTIVE":
        await send_message(
            chat_id,
            "Your PulseGrid account is not active.",
        )
        return {"ok": True}

    if not text:
        return {"ok": True}

    command, argument = parse_command(text)

    await route_command(
        command=command,
        argument=argument,
        chat_id=chat_id,
        db=db,
        user=pulsegrid_user,
    )

    return {"ok": True}

