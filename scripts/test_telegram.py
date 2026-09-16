import httpx

from app.config import settings


url = (
    "https://api.telegram.org/"
    f"bot{settings.telegram_bot_token}/getMe"
)

response = httpx.get(url)

print(response.json())