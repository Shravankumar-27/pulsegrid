"""
BookMyShow Cloudflare session management.

Strategy C (hybrid) needs a valid ``cf_clearance`` cookie before the
API transport can call ``primary-dynamic``. This module:

1. Loads / saves the cookie jar from disk
2. Bootstraps a fresh jar via headed Chromium + playwright-stealth
   when clearance is missing or rejected

Cookie path defaults (override with env):
    BMS_COOKIE_PATH   → data/bms_session_cookies.json
    BMS_PROFILE_DIR   → data/bms_browser_profile
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.parse
from pathlib import Path


def default_cookie_path() -> Path:
    return Path(os.getenv("BMS_COOKIE_PATH", "data/bms_session_cookies.json"))


def default_profile_dir() -> Path:
    return Path(os.getenv("BMS_PROFILE_DIR", "data/bms_browser_profile"))


def rgn_cookie_value(
    region_slug: str,
    region_code: str,
    latitude: str,
    longitude: str,
) -> str:
    payload = {
        "regionNameSlug": region_slug,
        "regionCodeSlug": region_code.lower(),
        "regionCode": region_code,
        "Lat": latitude,
        "Long": longitude,
    }
    return urllib.parse.quote(json.dumps(payload, separators=(",", ":")))


def load_cookies(path: Path | None = None) -> dict[str, str]:
    cookie_path = path or default_cookie_path()

    # Convenience: reuse the script-era cookie file if the app path is empty.
    legacy = Path("scripts/bms_session_cookies.json")
    if not cookie_path.exists() and legacy.exists():
        cookie_path = legacy

    if not cookie_path.exists():
        return {}

    raw = json.loads(cookie_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "cookies" in raw:
        return {c["name"]: c["value"] for c in raw["cookies"]}
    if isinstance(raw, list):
        return {c["name"]: c["value"] for c in raw}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def save_cookies(
    cookies: list[dict] | dict[str, str],
    path: Path | None = None,
) -> Path:
    cookie_path = path or default_cookie_path()
    cookie_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(cookies, dict):
        payload = [{"name": k, "value": v} for k, v in cookies.items()]
    else:
        payload = list(cookies)

    cookie_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return cookie_path


async def bootstrap_cf_session(
    region_slug: str,
    region_code: str,
    latitude: str,
    longitude: str,
    *,
    cookie_path: Path | None = None,
    profile_dir: Path | None = None,
) -> dict[str, str]:
    """
    Open headed Chromium, pass Cloudflare on the BMS home page, persist cookies.

    Requires a display (or virtual display). Headless Chromium is rejected by CF.
    """
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    profile = profile_dir or default_profile_dir()
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)

    home = f"https://in.bookmyshow.com/explore/home/{region_slug}"

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await Stealth(navigator_webdriver=True).apply_stealth_async(page)

        await context.add_cookies(
            [
                {
                    "name": "rgn",
                    "value": rgn_cookie_value(
                        region_slug, region_code, latitude, longitude
                    ),
                    "domain": "in.bookmyshow.com",
                    "path": "/",
                },
                {
                    "name": "RCODE",
                    "value": region_code,
                    "domain": ".bookmyshow.com",
                    "path": "/",
                },
            ]
        )

        await page.goto(home, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(4000)

        cookies = await context.cookies()
        await context.close()

    jar = {c["name"]: c["value"] for c in cookies}
    if "cf_clearance" not in jar:
        raise RuntimeError(
            "Cloudflare bootstrap finished but cf_clearance was not set. "
            "The challenge may still be active — retry with a visible browser."
        )

    save_cookies(cookies, path=cookie_path)
    return jar
