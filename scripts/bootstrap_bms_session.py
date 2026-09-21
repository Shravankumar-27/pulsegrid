"""
Bootstrap / refresh BookMyShow Cloudflare session cookies.

Needs a visible browser (headed Chromium). Run once when cookies expire.

    .\\.venv\\Scripts\\python.exe scripts/bootstrap_bms_session.py
    .\\.venv\\Scripts\\python.exe scripts/bootstrap_bms_session.py --city mumbai
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.providers.bms_session import (
    bootstrap_cf_session,
    default_cookie_path,
)
from app.services.providers.bookmyshow_config import get_city_config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bootstrap BMS Cloudflare session")
    p.add_argument("--city", default="hyderabad")
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    cfg = get_city_config(args.city)
    print(f"Bootstrapping CF session for {cfg.region_slug} ({cfg.region_code})")
    print("A Chromium window will open — wait until home page loads.")
    jar = await bootstrap_cf_session(
        cfg.region_slug,
        cfg.region_code,
        cfg.latitude,
        cfg.longitude,
    )
    path = default_cookie_path()
    print(f"Saved {len(jar)} cookies → {path}")
    print("cf_clearance" in jar and "cf_clearance: OK" or "cf_clearance: MISSING")
    return 0 if "cf_clearance" in jar else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
