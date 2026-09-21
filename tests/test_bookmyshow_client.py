import pytest

from app.services.providers.bookmyshow_client import (
    BookMyShowClient,
    BookMyShowClientError,
    BookMyShowResponseError,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeTransport:
    def __init__(self):
        self.calls = []

    async def get(self, url, *, params=None, headers=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
            }
        )
        return FakeResponse({"data": {}})


@pytest.mark.asyncio
async def test_fetch_showtimes_builds_request():
    transport = FakeTransport()
    client = BookMyShowClient(transport=transport)

    result = await client.fetch_showtimes(
        event_code="ET123",
        date_code="20260920",
        region_code="HYD",
        region_slug="hyderabad",
        latitude="17.3850",
        longitude="78.4867",
    )

    assert result == {"data": {}}
    assert len(transport.calls) == 1

    call = transport.calls[0]
    assert call["params"]["etCodes"] == "ET123"
    assert call["params"]["dateCode"] == "20260920"
    assert call["params"]["regionCode"] == "HYD"
    assert call["params"]["regionSlug"] == "hyderabad"
    assert call["params"]["appCode"] == "WEB"
    assert call["params"]["refEventCode"] == "ET123"

    assert call["headers"]["x-region-code"] == "HYD"
    assert call["headers"]["x-region-slug"] == "hyderabad"
    assert call["headers"]["x-app-code"] == "WEB"
    assert call["headers"]["x-latitude"] == "17.3850"
    assert call["headers"]["x-longitude"] == "78.4867"
    assert call["headers"]["x-location-selection"] == "manual"
    assert call["headers"]["accept"] == "application/json, text/plain, */*"
    assert "buytickets/ET123/20260920" in call["headers"]["referer"]


@pytest.mark.asyncio
async def test_fetch_showtimes_includes_language_when_set():
    transport = FakeTransport()
    client = BookMyShowClient(transport=transport)

    await client.fetch_showtimes(
        event_code="ET123",
        date_code="20260920",
        region_code="HYD",
        region_slug="hyderabad",
        latitude="17.3850",
        longitude="78.4867",
        language="telugu",
    )

    call = transport.calls[0]
    assert call["params"]["language"] == "telugu"
    assert "language=telugu" in call["headers"]["referer"]


class FailingTransport:
    async def get(self, url, *, params=None, headers=None):
        raise RuntimeError("connection failed")


@pytest.mark.asyncio
async def test_fetch_showtimes_wraps_transport_error():
    client = BookMyShowClient(transport=FailingTransport())

    with pytest.raises(BookMyShowClientError, match="connection failed"):
        await client.fetch_showtimes(
            event_code="ET123",
            date_code="20260920",
            region_code="HYD",
            region_slug="hyderabad",
            latitude="17.3850",
            longitude="78.4867",
        )


class InvalidJsonResponse:
    def json(self):
        raise ValueError("invalid json")


class InvalidJsonTransport:
    async def get(self, url, *, params=None, headers=None):
        return InvalidJsonResponse()


@pytest.mark.asyncio
async def test_fetch_showtimes_rejects_invalid_json():
    client = BookMyShowClient(transport=InvalidJsonTransport())

    with pytest.raises(BookMyShowResponseError, match="invalid JSON"):
        await client.fetch_showtimes(
            event_code="ET123",
            date_code="20260920",
            region_code="HYD",
            region_slug="hyderabad",
            latitude="17.3850",
            longitude="78.4867",
        )


def test_default_transport_is_curl_cffi():
    from app.services.providers.curl_cffi_transport import CurlCffiTransport

    client = BookMyShowClient()
    assert isinstance(client.transport, CurlCffiTransport)
