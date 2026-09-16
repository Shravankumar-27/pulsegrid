import httpx

from app.config import settings


BASE_URL = (
    "https://api.telegram.org/"
    f"bot{settings.telegram_bot_token}"
)


async def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            timeout=10,
        )

    response.raise_for_status()

    return response.json()