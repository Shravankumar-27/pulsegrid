import httpx

from app.config import settings


NGROK_URL = "https://garter-twirl-rumbling.ngrok-free.dev"

url = (
    "https://api.telegram.org/"
    f"bot{settings.telegram_bot_token}/setWebhook"
)

webhook_url = f"{NGROK_URL}/api/v1/telegram/webhook"

response = httpx.post(
    url,
    json={"url": webhook_url},
    timeout=10,
)

print(response.json())