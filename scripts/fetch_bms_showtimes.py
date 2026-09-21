"""
CLI: fetch BookMyShow showtime JSON via the app provider stack.

Uses ``BookMyShowClient`` + ``CurlCffiTransport`` (Chrome TLS + CF session).

    .\\.venv\\Scripts\\python.exe scripts/fetch_bms_showtimes.py ET00514261
    .\\.venv\\Scripts\\python.exe scripts/fetch_bms_showtimes.py ET00442702 --city hyderabad
    .\\.venv\\Scripts\\python.exe scripts/fetch_bms_showtimes.py ET00514261 --date 20260922 --language telugu
    .\\.venv\\Scripts\\python.exe scripts/fetch_bms_showtimes.py ET00514261 --bootstrap
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.providers.bookmyshow import extract_sessions
from app.services.providers.bookmyshow_client import BookMyShowClient
from app.services.providers.bookmyshow_config import get_city_config
from app.services.providers.bms_session import bootstrap_cf_session
from app.services.providers.curl_cffi_transport import CurlCffiTransport

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = SCRIPTS_DIR / "bms_live_response.json"
IST = timezone(timedelta(hours=5, minutes=30))


def _today_ist() -> str:
    return datetime.now(IST).strftime("%Y%m%d")


def print_sessions(sessions: list[dict]) -> None:
    avail_map = {"2": "AVAIL", "3": "FAST ", "4": "LAST ", "1": "SOLD "}
    venues: dict[str, list[dict]] = {}
    for s in sessions:
        venues.setdefault(s["cinema"], []).append(s)

    print(f"\nSessions: {len(sessions)} across {len(venues)} venues")
    for venue, shows in venues.items():
        avail = sum(1 for s in shows if s["avail_status"] in ("2", "3", "4"))
        code = shows[0].get("venue_code", "")
        print(f"\n  [{code}] {venue} ({avail}/{len(shows)} bookable)")
        for s in shows:
            lb = avail_map.get(s["avail_status"], "???  ")
            t = (s.get("time") or "")[:12]
            fmt = (s.get("format") or "")[:30]
            print(f"    [{lb}] {t:12s}  {fmt:30s}  id={s.get('id')}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch BMS showtime JSON")
    p.add_argument("event_code", help="BMS event code, e.g. ET00514261")
    p.add_argument("--city", default="hyderabad")
    p.add_argument("--date", dest="date_code", default=None, help="YYYYMMDD")
    p.add_argument("--language", default="")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--bootstrap",
        action="store_true",
        help="Force a fresh headed Chromium CF bootstrap before fetching",
    )
    return p.parse_args()


async def _run(args: argparse.Namespace) -> int:
    event = args.event_code.strip().upper()
    cfg = get_city_config(args.city)
    date_code = args.date_code or _today_ist()

    print("=" * 60)
    print("BookMyShow showtime fetch")
    print("=" * 60)

    if args.bootstrap:
        print("Forcing CF session bootstrap…")
        await bootstrap_cf_session(
            cfg.region_slug,
            cfg.region_code,
            cfg.latitude,
            cfg.longitude,
        )

    client = BookMyShowClient(transport=CurlCffiTransport())
    data = await client.fetch_showtimes(
        event_code=event,
        date_code=date_code,
        region_code=cfg.region_code,
        region_slug=cfg.region_slug,
        latitude=cfg.latitude,
        longitude=cfg.longitude,
        language=args.language,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nRaw JSON → {args.out}")

    sessions = extract_sessions(data)
    print_sessions(sessions)
    print("\nDone.")
    return 0


def main() -> int:
    return asyncio.run(_run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
