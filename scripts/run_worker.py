"""
Continuous PulseGrid worker loop.

Polls RUNNING tracking jobs, checks providers (BookMyShow), dedupes
sessions, and sends Telegram alerts.

    .\\.venv\\Scripts\\python.exe scripts/run_worker.py
    .\\.venv\\Scripts\\python.exe scripts/run_worker.py --once
    .\\.venv\\Scripts\\python.exe scripts/run_worker.py --interval 30
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal
from app.services.notifications.telegram import TelegramNotification
from app.worker.runner import run_worker_cycle
from app.worker.state import WorkerState


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PulseGrid monitoring worker")
    p.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("WORKER_POLL_SECONDS", "15")),
        help="Seconds between cycles when looping (default: 15)",
    )
    p.add_argument(
        "--state-file",
        type=Path,
        default=Path(os.getenv("WORKER_STATE_PATH", "data/worker_state.json")),
        help="Path for persisted seen-session state",
    )
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    notification = TelegramNotification(settings.telegram_bot_token)
    worker_state = WorkerState(persist_path=args.state_file)
    print(f"Worker state → {args.state_file}")
    print("PulseGrid worker started.")

    while True:
        db = SessionLocal()
        try:
            result = await run_worker_cycle(
                db=db,
                notification_service=notification,
                worker_state=worker_state,
            )
            worker_state.save()
            print(
                f"cycle checked={result['checked']} "
                f"notified={result['notified']} "
                f"skipped={result['skipped']} "
                f"completed={result['completed']}"
            )
        except Exception as exc:
            print(f"cycle error: {exc}")
        finally:
            db.close()

        if args.once:
            break

        time.sleep(max(1.0, args.interval))

    print("Worker stopped.")
    return 0


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
