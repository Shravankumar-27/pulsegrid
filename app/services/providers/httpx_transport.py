import httpx

from app.services.providers.http_transport import HttpTransport


class HttpxTransport(HttpTransport):

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def get(self, url: str, *, params=None, headers=None):
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                params=params,
                headers=headers,
            )

            response.raise_for_status()

            return response