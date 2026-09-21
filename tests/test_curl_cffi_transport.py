"""Unit tests for CurlCffiTransport — no real network."""

from pathlib import Path

import pytest

from app.services.providers.curl_cffi_transport import CurlCffiTransport


class _FakeCfResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text else ("" if payload is None else str(payload))
        self.cookies = {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.mark.asyncio
async def test_curl_transport_returns_json(monkeypatch, tmp_path: Path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        '[{"name": "cf_clearance", "value": "abc"}]',
        encoding="utf-8",
    )

    def fake_get(*args, **kwargs):
        return _FakeCfResponse(200, {"data": {"showtimeWidgets": [{"type": "adtech"}]}})

    monkeypatch.setattr(
        "app.services.providers.curl_cffi_transport.cf_requests.get",
        fake_get,
    )

    transport = CurlCffiTransport(
        cookie_path=cookie_file,
        auto_bootstrap=False,
    )

    response = await transport.get(
        "https://in.bookmyshow.com/api/movies-data/v5/showtimes-by-event/primary-dynamic",
        params={
            "etCodes": "ET123",
            "dateCode": "20260921",
            "regionSlug": "hyderabad",
            "regionCode": "HYD",
            "appCode": "WEB",
            "refEventCode": "ET123",
        },
        headers={
            "x-region-code": "HYD",
            "x-region-slug": "hyderabad",
            "x-latitude": "17.3850",
            "x-longitude": "78.4867",
            "x-app-code": "WEB",
        },
    )

    assert response.json()["data"]["showtimeWidgets"][0]["type"] == "adtech"


@pytest.mark.asyncio
async def test_curl_transport_raises_without_bootstrap_on_403(
    monkeypatch, tmp_path: Path
):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        '[{"name": "cf_clearance", "value": "abc"}]',
        encoding="utf-8",
    )

    def fake_get(*args, **kwargs):
        return _FakeCfResponse(403, text="Just a moment...")

    monkeypatch.setattr(
        "app.services.providers.curl_cffi_transport.cf_requests.get",
        fake_get,
    )

    transport = CurlCffiTransport(
        cookie_path=cookie_file,
        auto_bootstrap=False,
    )

    with pytest.raises(RuntimeError, match="HTTP 403"):
        await transport.get(
            "https://in.bookmyshow.com/api/movies-data/v5/showtimes-by-event/primary-dynamic",
            params={
                "etCodes": "ET123",
                "dateCode": "20260921",
                "regionSlug": "hyderabad",
                "regionCode": "HYD",
            },
            headers={
                "x-region-code": "HYD",
                "x-region-slug": "hyderabad",
                "x-latitude": "17.3850",
                "x-longitude": "78.4867",
            },
        )


@pytest.mark.asyncio
async def test_curl_transport_bootstraps_then_retries(monkeypatch, tmp_path: Path):
    cookie_file = tmp_path / "cookies.json"
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeCfResponse(403, text="challenge")
        return _FakeCfResponse(200, {"data": {"showtimeWidgets": []}})

    async def fake_bootstrap(*args, **kwargs):
        return {"cf_clearance": "fresh"}

    monkeypatch.setattr(
        "app.services.providers.curl_cffi_transport.cf_requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "app.services.providers.curl_cffi_transport.bootstrap_cf_session",
        fake_bootstrap,
    )
    monkeypatch.setattr(
        "app.services.providers.curl_cffi_transport.load_cookies",
        lambda path=None: {},
    )

    transport = CurlCffiTransport(
        cookie_path=cookie_file,
        auto_bootstrap=True,
    )

    response = await transport.get(
        "https://in.bookmyshow.com/api/movies-data/v5/showtimes-by-event/primary-dynamic",
        params={
            "etCodes": "ET123",
            "dateCode": "20260921",
            "regionSlug": "hyderabad",
            "regionCode": "HYD",
        },
        headers={
            "x-region-code": "HYD",
            "x-region-slug": "hyderabad",
            "x-latitude": "17.3850",
            "x-longitude": "78.4867",
        },
    )

    assert calls["n"] == 2
    assert response.json() == {"data": {"showtimeWidgets": []}}
