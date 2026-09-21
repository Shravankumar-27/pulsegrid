"""
BookMyShow API client.

Fetches showtime data from:
    /api/movies-data/v5/showtimes-by-event/primary-dynamic

Retrieval is delegated to a transport layer. The default is
``CurlCffiTransport`` (Chrome TLS impersonation + Cloudflare session),
which is the proven production path. ``PlaywrightTransport`` remains
injectable as an experimental fallback.
"""

from app.services.providers.curl_cffi_transport import CurlCffiTransport


class BookMyShowClientError(Exception):
    pass


class BookMyShowResponseError(BookMyShowClientError):
    pass


class BookMyShowClient:
    """
    High-level client for BookMyShow showtime data.

    fetch_showtimes() returns the raw parsed JSON from BMS.
    """

    BASE_URL = (
        "https://in.bookmyshow.com/api/movies-data/v5/"
        "showtimes-by-event/primary-dynamic"
    )

    def __init__(self, transport=None):
        self.transport = transport or CurlCffiTransport()

    async def fetch_showtimes(
        self,
        event_code: str,
        date_code: str,
        region_code: str,
        region_slug: str,
        latitude: str,
        longitude: str,
        language: str = "",
    ) -> dict:
        """
        Retrieve showtime data for the given event and date.

        Parameters
        ----------
        event_code  : BMS event code, e.g. ``ET00514261``
        date_code   : Date in ``YYYYMMDD`` format, e.g. ``20260919``
        region_code : BMS region code, e.g. ``HYD``
        region_slug : BMS region slug, e.g. ``hyderabad``
        latitude    : City latitude as string, e.g. ``17.3850``
        longitude   : City longitude as string, e.g. ``78.4867``
        language    : Optional language filter, e.g. ``telugu``
        """
        params = {
            # Transport may use these for referer / region cookies.
            "etCodes": event_code,
            "dateCode": date_code,
            "regionSlug": region_slug,
            # Actual API query-string parameters the BMS SPA fires.
            "regionCode": region_code,
            "isDesktop": "true",
            "xLocationShared": "false",
            "memberId": "",
            "lsId": "",
            "subCode": "",
            "appCode": "WEB",
            "refEventCode": event_code,
            **({"language": language} if language else {}),
        }

        qs = f"etCodes={event_code}&refEventCode={event_code}"
        if language:
            qs += f"&language={language}"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "referer": (
                f"https://in.bookmyshow.com/movies/{region_slug}/buytickets/"
                f"{event_code}/{date_code}?{qs}"
            ),
            "x-region-code": region_code,
            "x-region-slug": region_slug,
            "x-latitude": latitude,
            "x-longitude": longitude,
            "x-location-selection": "manual",
            "x-app-code": "WEB",
            "x-platform": "WEB",
            "x-platform-code": "WEB",
        }

        try:
            response = await self.transport.get(
                self.BASE_URL,
                params=params,
                headers=headers,
            )
            return response.json()

        except BookMyShowClientError:
            raise

        except ValueError as exc:
            raise BookMyShowResponseError(
                "BookMyShow returned invalid JSON"
            ) from exc

        except Exception as exc:
            raise BookMyShowClientError(
                f"BookMyShow request failed: {exc}"
            ) from exc
