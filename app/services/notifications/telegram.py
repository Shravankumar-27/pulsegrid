import httpx

from app.services.notifications.base import NotificationService


class TelegramNotification(NotificationService):
    """Telegram implementation of the notification service."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, recipient: str, message: str) -> None:
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": recipient,
            "text": message,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                timeout=10.0,
            )

        response.raise_for_status()