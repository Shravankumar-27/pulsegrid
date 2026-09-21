"""
Set Telegram webhook URL from env.

    TELEGRAM_WEBHOOK_BASE=https://xxxx.ngrok-free.dev
    .\\.venv\\Scripts\\python.exe scripts/set_telegram_webhook.py
"""

from __future__ import annotations

import os
import sys

import httpx

from app.config import settings


def main() -> int:
    base = os.getenv("TELEGRAM_WEBHOOK_BASE", "").rstrip("/")
    if not base:
        print(
            "Set TELEGRAM_WEBHOOK_BASE to your public HTTPS origin "
            "(e.g. https://xxxx.ngrok-free.dev)"
        )
        return 1

    webhook_url = f"{base}/api/v1/telegram/webhook"
    api = (
        "https://api.telegram.org/"
        f"bot{settings.telegram_bot_token}/setWebhook"
    )

    response = httpx.post(api, json={"url": webhook_url}, timeout=10)
    print(f"Webhook → {webhook_url}")
    print(response.json())
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
