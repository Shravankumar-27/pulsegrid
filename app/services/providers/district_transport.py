"""
District HTTP transport.

Fetches a District movie page with Chrome TLS impersonation and returns
parsed ``__NEXT_DATA__`` pageProps (SSR showtimes).
"""

from __future__ import annotations

import asyncio
import json
import re

from curl_cffi import requests as cf_requests

from app.services.providers.http_transport import HttpTransport

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
IMPERSONATE = "chrome131"


class DistrictTransport(HttpTransport):
    def __init__(self, *, timeout: float = 30.0, impersonate: str = IMPERSONATE):
        self.timeout = timeout
        self.impersonate = impersonate

    async def get(self, url: str, *, params=None, headers=None):
        data = await asyncio.to_thread(self._fetch_page_props, url, headers or {})
        return _JsonResponse(data)

    def _fetch_page_props(self, url: str, headers: dict) -> dict:
        response = cf_requests.get(
            url,
            headers=headers,
            impersonate=self.impersonate,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"District page fetch failed (HTTP {response.status_code})"
            )

        match = _NEXT_DATA_RE.search(response.text)
        if not match:
            raise RuntimeError("District page missing __NEXT_DATA__ payload")

        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise RuntimeError("District __NEXT_DATA__ was not valid JSON") from exc

        page_props = (payload.get("props") or {}).get("pageProps")
        if not isinstance(page_props, dict):
            raise RuntimeError("District __NEXT_DATA__ missing pageProps")
        return page_props


class _JsonResponse:
    def __init__(self, data: dict):
        self._data = data

    def json(self) -> dict:
        return self._data
