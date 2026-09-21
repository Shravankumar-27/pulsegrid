"""
BookMyShow curl_cffi transport.

Primary retrieval path (Strategy C — fast API):

1. Load a saved Cloudflare session (``cf_clearance``).
2. GET ``primary-dynamic`` with Chrome TLS impersonation.
3. On 403/503 (or missing clearance), bootstrap a fresh headed session
   and retry once.

This is the production default for ``BookMyShowClient``. Playwright XHR
interception remains available as an injectable fallback, but is unreliable
because BMS often SSR's showtimes and does not re-fire the API on load.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from curl_cffi import requests as cf_requests

from app.services.providers.bms_session import (
    bootstrap_cf_session,
    load_cookies,
    rgn_cookie_value,
    save_cookies,
)
from app.services.providers.http_transport import HttpTransport

IMPERSONATE = "chrome131"


class CurlCffiTransport(HttpTransport):
    """
    HTTP transport that mimics Chrome's TLS fingerprint and reuses a
    Cloudflare clearance cookie to call BMS APIs directly.
    """

    def __init__(
        self,
        *,
        cookie_path: Path | None = None,
        auto_bootstrap: bool = True,
        timeout: float = 30.0,
        impersonate: str = IMPERSONATE,
    ):
        self.cookie_path = cookie_path
        self.auto_bootstrap = auto_bootstrap
        self.timeout = timeout
        self.impersonate = impersonate

    async def get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
    ):
        params = dict(params or {})
        headers = dict(headers or {})

        region_slug = params.pop("regionSlug", headers.get("x-region-slug", "hyderabad"))
        region_code = params.get("regionCode") or headers.get("x-region-code", "HYD")
        latitude = headers.get("x-latitude", "17.3850")
        longitude = headers.get("x-longitude", "78.4867")
        event_code = params.get("etCodes", "")
        date_code = params.get("dateCode", "")
        language = params.get("language", "")

        # Buytickets referer matches what the real SPA sends.
        if "referer" not in {k.lower() for k in headers}:
            qs = f"etCodes={event_code}&refEventCode={event_code}"
            if language:
                qs += f"&language={language}"
            headers["referer"] = (
                f"https://in.bookmyshow.com/movies/{region_slug}/buytickets/"
                f"{event_code}/{date_code}?{qs}"
            )

        headers.setdefault("x-location-selection", "manual")
        headers.setdefault("accept-language", "en-GB,en-US;q=0.9,en;q=0.8")

        cookies = load_cookies(self.cookie_path)
        if self.auto_bootstrap and "cf_clearance" not in cookies:
            cookies = await self._bootstrap(
                region_slug, region_code, latitude, longitude
            )

        status, data, head = await asyncio.to_thread(
            self._request,
            url,
            params,
            headers,
            cookies,
            region_slug,
            region_code,
            latitude,
            longitude,
        )

        if status in (403, 503) or data is None:
            if not self.auto_bootstrap:
                raise RuntimeError(
                    f"BookMyShow API rejected the request (HTTP {status}): {head}"
                )
            cookies = await self._bootstrap(
                region_slug, region_code, latitude, longitude
            )
            status, data, head = await asyncio.to_thread(
                self._request,
                url,
                params,
                headers,
                cookies,
                region_slug,
                region_code,
                latitude,
                longitude,
            )

        if data is None:
            raise RuntimeError(
                f"BookMyShow primary-dynamic failed (HTTP {status}): {head}"
            )

        return _JsonResponse(data)

    async def _bootstrap(
        self,
        region_slug: str,
        region_code: str,
        latitude: str,
        longitude: str,
    ) -> dict[str, str]:
        return await bootstrap_cf_session(
            region_slug,
            region_code,
            latitude,
            longitude,
            cookie_path=self.cookie_path,
        )

    def _request(
        self,
        url: str,
        params: dict,
        headers: dict,
        cookies: dict[str, str],
        region_slug: str,
        region_code: str,
        latitude: str,
        longitude: str,
    ) -> tuple[int, dict | None, str]:
        jar = dict(cookies)
        jar.setdefault(
            "rgn",
            rgn_cookie_value(region_slug, region_code, latitude, longitude),
        )
        jar.setdefault("RCODE", region_code)

        response = cf_requests.get(
            url,
            params=params,
            headers=headers,
            cookies=jar,
            impersonate=self.impersonate,
            timeout=self.timeout,
        )

        # Persist any Set-Cookie refresh from a successful call.
        if response.cookies:
            jar.update({k: v for k, v in response.cookies.items()})
            save_cookies(jar, path=self.cookie_path)

        text = response.text
        data = None
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = None
        return response.status_code, data, text[:300]


class _JsonResponse:
    def __init__(self, data: dict):
        self._data = data

    def json(self) -> dict:
        return self._data
