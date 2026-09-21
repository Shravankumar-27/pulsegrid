"""
BookMyShow Playwright transport (experimental fallback).

Production default is ``CurlCffiTransport``. This transport remains available
for experiments: open a browser, navigate to buytickets, intercept
``primary-dynamic`` if the SPA fires it.

Note: BMS often SSR's showtimes into ``__INITIAL_STATE__`` and does not
re-fire ``primary-dynamic`` on load, so XHR interception is unreliable.
"""

import asyncio
import json

from playwright.async_api import async_playwright

from app.services.providers.http_transport import HttpTransport


# The buytickets URL without movie slug — BMS handles the redirect internally.
# This is simpler and doesn't require discovering the slug.
_BUYTICKETS_TEMPLATE = (
    "https://in.bookmyshow.com/movies/{region_slug}/buytickets/{event_code}/{date_code}"
)

# Some versions of BMS redirect to a slug-based URL.
# We also try navigating directly to the event on the explore page.
_MOVIE_EVENT_TEMPLATE = (
    "https://in.bookmyshow.com/events/{event_code}"
)

_PRIMARY_DYNAMIC_FRAGMENT = "showtimes-by-event/primary-dynamic"


class PlaywrightTransport(HttpTransport):
    """
    Retrieves BookMyShow showtime data by launching a real Firefox browser,
    navigating to the buytickets page, and intercepting the API response
    the page itself fires.
    """

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    async def get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
    ):
        """
        Navigate to the BMS buytickets page and capture the primary-dynamic
        API response via network interception.

        Params used:
            - ``etCodes``     → event code e.g. ``ET00514261``
            - ``dateCode``    → date in ``YYYYMMDD``
            - ``regionSlug``  → city slug e.g. ``hyderabad``
        """
        params = params or {}

        event_code  = params.get("etCodes", "")
        date_code   = params.get("dateCode", "")
        region_slug = params.get("regionSlug", "hyderabad")

        response_data = await self._intercept_primary_dynamic(
            event_code=event_code,
            date_code=date_code,
            region_slug=region_slug,
        )
        return _JsonResponse(response_data)

    async def _intercept_primary_dynamic(
        self,
        event_code: str,
        date_code: str,
        region_slug: str,
    ) -> dict:
        """
        Launch Firefox, navigate to BMS, wait for the primary-dynamic request.

        Tries two navigation strategies in sequence:
          1. Direct buytickets URL (no slug required — BMS resolves it)
          2. Movie event page → look for buytickets link in rendered HTML
        """
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=self.headless)

            context = await browser.new_context(
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) "
                    "Gecko/20100101 Firefox/142.0"
                ),
                viewport={"width": 1280, "height": 900},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )

            page = await context.new_page()

            # ---- Register network interceptor BEFORE navigating ----
            loop = asyncio.get_event_loop()
            captured_future: asyncio.Future = loop.create_future()

            async def handle_response(response):
                if _PRIMARY_DYNAMIC_FRAGMENT in response.url:
                    if not captured_future.done():
                        try:
                            body = await response.body()
                            data = json.loads(body)
                            captured_future.set_result(data)
                        except Exception as exc:
                            if not captured_future.done():
                                captured_future.set_exception(exc)

            page.on("response", handle_response)

            # ---- Strategy 1: Direct buytickets URL ----
            buytickets_url = _BUYTICKETS_TEMPLATE.format(
                region_slug=region_slug,
                event_code=event_code,
                date_code=date_code,
            )

            try:
                await page.goto(
                    buytickets_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                # Give the page some time to fire XHRs
                await page.wait_for_timeout(3000)
            except Exception:
                pass  # Don't fail here — check if future was resolved

            # Check if we captured the response
            if captured_future.done() and not captured_future.cancelled():
                try:
                    result = captured_future.result()
                    await browser.close()
                    return result
                except Exception:
                    pass

            # ---- Strategy 2: Movie event page fallback ----
            # Reset the future
            captured_future = loop.create_future()
            page.on("response", handle_response)

            event_page_url = _MOVIE_EVENT_TEMPLATE.format(event_code=event_code)

            try:
                await page.goto(
                    event_page_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            # After landing on the movie page, look for a buytickets link
            # that includes the event code and navigate to it
            try:
                current_url = page.url

                # Try to find the buytickets link from the page HTML
                buytickets_links = await page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a[href*="buytickets"]'));
                    return links.map(l => l.href).filter(h => h.includes('buytickets'));
                }""")

                if buytickets_links:
                    # Navigate to the first buytickets link
                    bt_link = buytickets_links[0]
                    # Append the date code if not present
                    if date_code and date_code not in bt_link:
                        bt_link = bt_link.rstrip("/") + f"/{date_code}"

                    await page.goto(
                        bt_link,
                        wait_until="domcontentloaded",
                        timeout=self.timeout_ms,
                    )
                    await page.wait_for_timeout(3000)

            except Exception:
                pass

            # Wait for the primary-dynamic response
            try:
                captured = await asyncio.wait_for(
                    captured_future,
                    timeout=20,  # 20 second window after all navigation
                )
                await browser.close()
                return captured

            except asyncio.TimeoutError:
                await browser.close()
                raise RuntimeError(
                    f"Timed out waiting for BookMyShow primary-dynamic API response.\n"
                    f"Tried:\n"
                    f"  1. {buytickets_url}\n"
                    f"  2. {event_page_url}\n"
                    f"The page may not have loaded correctly or the event may not be on sale."
                )
            except Exception as exc:
                await browser.close()
                raise RuntimeError(
                    f"Failed to capture primary-dynamic API response: {exc}"
                ) from exc


class _JsonResponse:
    """Thin wrapper so PlaywrightTransport.get() returns an object with .json()."""

    def __init__(self, data: dict):
        self._data = data

    def json(self) -> dict:
        return self._data