"""
Smoke-check District provider (calls live district.in).

    .\\.venv\\Scripts\\python.exe scripts/smoke_district_monitor.py MV181196
    .\\.venv\\Scripts\\python.exe scripts/smoke_district_monitor.py MV181196 --city Hyderabad --theater PVR
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.providers.factory import get_provider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="District provider smoke test")
    p.add_argument("movie_ref", help="MV code or District movie URL")
    p.add_argument("--city", default="Hyderabad")
    p.add_argument("--theater", default="Any")
    p.add_argument("--date", default=None, help="YYYY-MM-DD")
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    job = SimpleNamespace(
        target_name=args.movie_ref.strip(),
        platform="district",
        city=args.city,
        theater=args.theater,
        target_date=(
            date.fromisoformat(args.date)
            if args.date
            else datetime.now(timezone.utc).date()
        ),
    )

    print("=" * 60)
    print("PulseGrid District smoke test")
    print("=" * 60)

    result = await get_provider("district").check(job)
    if result.get("error"):
        print("FAIL:", result.get("message"))
        return 1

    sessions = result.get("sessions") or []
    print("available=", result.get("available"), "sessions=", len(sessions))
    print("message:", result.get("message"))
    for s in sessions[:8]:
        print(
            f"  - {s.get('time')} | {s.get('format')} | "
            f"{s.get('cinema')} | id={s.get('id')}"
        )
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
