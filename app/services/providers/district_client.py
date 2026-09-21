"""
District API/client.

Resolves a movie page URL for a city and returns SSR pageProps JSON
via ``DistrictTransport``.
"""

from __future__ import annotations

import asyncio
import re

from curl_cffi import requests as cf_requests

from app.services.providers.district_config import movies_base_url
from app.services.providers.district_transport import DistrictTransport

_MV_RE = re.compile(r"^(?:MV)?(\d{4,})$", re.IGNORECASE)
_PATH_RE = re.compile(r"/movies/([\w-]+-MV\d+)", re.IGNORECASE)


class DistrictClientError(Exception):
    pass


class DistrictClient:
    def __init__(self, transport=None):
        self.transport = transport or DistrictTransport()

    async def fetch_showtimes(
        self,
        *,
        movie_ref: str,
        city_slug: str,
        date_code: str = "",
    ) -> dict:
        """
        Parameters
        ----------
        movie_ref : full URL, ``/movies/...-MV181196`` path, or bare ``MV181196``
        city_slug : e.g. ``hyderabad``
        date_code : reserved (YYYY-MM-DD); SSR page defaults to first available date
        """
        del date_code  # page currently SSR's the selected/default date
        url = await self._resolve_movie_url(movie_ref, city_slug)
        try:
            response = await self.transport.get(
                url,
                headers={
                    "accept": "text/html,application/xhtml+xml",
                    "accept-language": "en-IN,en;q=0.9",
                },
            )
            return response.json()
        except DistrictClientError:
            raise
        except Exception as exc:
            raise DistrictClientError(f"District request failed: {exc}") from exc

    async def _resolve_movie_url(self, movie_ref: str, city_slug: str) -> str:
        ref = (movie_ref or "").strip()
        base = movies_base_url()

        if ref.startswith("http://") or ref.startswith("https://"):
            return ensure_city_in_url(ref, city_slug)

        if "/movies/" in ref:
            path = ref if ref.startswith("/") else f"/{ref.lstrip('/')}"
            return ensure_city_in_url(f"{base}{path}", city_slug)

        path_match = _PATH_RE.search(ref)
        if path_match:
            return ensure_city_in_url(
                f"{base}/movies/{path_match.group(1)}",
                city_slug,
            )

        mv = _MV_RE.fullmatch(ref.replace(" ", ""))
        if not mv:
            raise DistrictClientError(
                "District target must be a movie URL/path or MV code "
                "(e.g. MV181196)."
            )

        discovered = await discover_movie_path(mv.group(1))
        return ensure_city_in_url(f"{base}{discovered}", city_slug)


def ensure_city_in_url(url: str, city_slug: str) -> str:
    """
    Prefer city-scoped URLs that SSR showtimes:

        ...-movie-tickets-in-{city}-MV123
    """
    if re.search(rf"-in-{re.escape(city_slug)}-MV\d+", url, re.IGNORECASE):
        return url
    return re.sub(
        r"-(MV\d+)",
        f"-in-{city_slug}-\\1",
        url,
        count=1,
        flags=re.IGNORECASE,
    )


async def discover_movie_path(movie_id: str) -> str:
    listing = f"{movies_base_url()}/movies/"
    html_resp = await asyncio.to_thread(
        cf_requests.get,
        listing,
        impersonate="chrome131",
        timeout=30,
    )
    if html_resp.status_code != 200:
        raise DistrictClientError("Failed to load District movies listing")

    match = re.search(
        rf"/movies/([\w-]+-MV{re.escape(movie_id)})",
        html_resp.text,
        re.IGNORECASE,
    )
    if not match:
        raise DistrictClientError(
            f"Could not find District movie MV{movie_id} on the listing page. "
            "Pass a full District movie URL instead."
        )
    return "/movies/" + match.group(1)
