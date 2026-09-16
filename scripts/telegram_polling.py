import time

import httpx

from app.config import settings


BASE_URL = (
    "https://api.telegram.org/"
    f"bot{settings.telegram_bot_token}"
)


offset = None


while True:
    params = {
        "timeout": 30,
    }

    if offset is not None:
        params["offset"] = offset

    response = httpx.get(
        f"{BASE_URL}/getUpdates",
        params=params,
        timeout=35,
    )

    data = response.json()

    if not data.get("ok"):
        print(data)
        time.sleep(2)
        continue

    for update in data["result"]:
        offset = update["update_id"] + 1

        message = update.get("message")

        if message is None:
            continue

        user = message.get("from", {})
        chat = message.get("chat", {})

        print("----- New Telegram Message -----")
        print("User ID:", user.get("id"))
        print("Name:", user.get("first_name"))
        print("Chat ID:", chat.get("id"))
        print("Text:", message.get("text"))