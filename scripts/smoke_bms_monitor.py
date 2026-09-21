"""
End-to-end smoke test: TrackingJob → BookMyShowProvider → optional Telegram.

Does not require the continuous worker. Useful to verify CF session +
provider + notification wiring before leaving the worker running.

    .\\.venv\\Scripts\\python.exe scripts/smoke_bms_monitor.py ET00514261
    .\\.venv\\Scripts\\python.exe scripts/smoke_bms_monitor.py ET00514261 --theater PVR --notify
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.notifications.telegram import TelegramNotification
from app.services.providers.factory import get_provider
from app.worker.runner import build_notification_message
from app.worker.state import WorkerState
from app.services.availability_tracker import get_new_sessions


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BMS monitor smoke test")
    p.add_argument("event_code", help="BMS event code, e.g. ET00514261")
    p.add_argument("--city", default="Hyderabad")
    p.add_argument("--theater", default="Any")
    p.add_argument(
        "--date",
        default=None,
        help="YYYY-MM-DD (default: today UTC)",
    )
    p.add_argument(
        "--notify",
        action="store_true",
        help="Send a real Telegram message to TELEGRAM_SMOKE_CHAT_ID",
    )
    p.add_argument(
        "--chat-id",
        default=os.getenv("TELEGRAM_SMOKE_CHAT_ID", ""),
        help="Telegram chat id for --notify",
    )
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    event = args.event_code.strip().upper()
    target_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(timezone.utc).date()
    )

    job = SimpleNamespace(
        id=0,
        target_name=event,
        platform="bookmyshow",
        city=args.city,
        theater=args.theater,
        target_date=target_date,
        poll_interval_seconds=60,
        last_checked_at=None,
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        user=SimpleNamespace(telegram_user_id=args.chat_id or "0"),
    )

    print("=" * 60)
    print("PulseGrid BMS smoke test")
    print("=" * 60)
    print(f"Event: {event}  City: {args.city}  Theater: {args.theater}")
    print(f"Date:  {target_date}")

    provider = get_provider("bookmyshow")
    result = await provider.check(job)

    if result.get("error"):
        print(f"FAIL: {result.get('message')}")
        return 1

    sessions = result.get("sessions", [])
    print(f"available={result.get('available')} sessions={len(sessions)}")
    print(f"message: {result.get('message')}")

    for session in sessions[:5]:
        print(
            f"  - {session.get('time')} | {session.get('format')} | "
            f"{session.get('cinema')} | id={session.get('id')}"
        )
    if len(sessions) > 5:
        print(f"  … {len(sessions) - 5} more")

    # Dedupe path
    state = WorkerState()
    job_state = state.get_job_state(job.id)
    new_sessions = get_new_sessions(sessions, job_state)
    print(f"new_sessions (first pass)={len(new_sessions)}")
    new_again = get_new_sessions(sessions, job_state)
    print(f"new_sessions (second pass)={len(new_again)} (expect 0)")

    if args.notify:
        if not args.chat_id:
            print("FAIL: --notify requires --chat-id or TELEGRAM_SMOKE_CHAT_ID")
            return 1
        notify_result = {
            "available": bool(new_sessions),
            "sessions": new_sessions[:10],
            "message": result.get("message", ""),
        }
        message = build_notification_message(job, notify_result)
        await TelegramNotification(settings.telegram_bot_token).send(
            recipient=str(args.chat_id),
            message=message,
        )
        print("Telegram notification sent.")

    if not result.get("available") and not sessions:
        print("WARN: no matching bookable sessions (still a valid API path).")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
