"""
Tests for BookMyShowProvider.

All tests use fake clients — no real browser or network calls.
Fixture data uses the actual BMS API response structure (as captured from HAR).
"""

from datetime import date
from types import SimpleNamespace

import pytest
import json
from pathlib import Path

from app.services.providers.bookmyshow import (
    BookMyShowProvider,
    extract_sessions,
    is_session_available,
    collect_venue_cards,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def fetch_showtimes(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_job(theater="PVR"):
    return SimpleNamespace(
        target_name="ET123",
        target_date=date(2026, 9, 20),
        theater=theater,
        city="Hyderabad",
    )


def venue_card(venue_name="PVR Hyderabad", venue_code="PVRHYD", sessions=None):
    """
    Build a minimal venue-card dict matching the real BMS API structure.
    ``sessions`` is a list of (time, avail_status, session_id, fmt) tuples.
    """
    if sessions is None:
        sessions = [("6:30 PM", "2", "session-001", "IMAX")]

    showtimes = [
        {
            "title": t,
            "screenAttr": fmt,
            "styleId": "green-pill" if avail_status in ("2", "3") else "grey-pill",
            "additionalData": {
                "sessionId": sid,
                "availStatus": avail_status,
                "showDateTime": "202609201830",
                "showTimeCode": "1830",
                "showTime": t,
                "attributes": fmt,
            },
        }
        for t, avail_status, sid, fmt in sessions
    ]

    return {
        "type": "venue-card",
        "additionalData": {
            "venueCode": venue_code,
            "venueName": venue_name,
        },
        "showtimesSections": [
            {"showtimes": showtimes}
        ],
    }


def bms_response(*venue_cards):
    """Wrap venue cards in a minimal BMS showtimeWidgets response."""
    return {
        "data": {
            "showtimeWidgets": [
                {
                    "type": "groupList",
                    "data": [
                        {
                            "type": "venueGroup",
                            "id": "Venue_GROUP_1",
                            "data": list(venue_cards),
                        }
                    ],
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Unit tests for extract_sessions()
# ---------------------------------------------------------------------------

def test_extract_sessions_parses_venue_name():
    data = bms_response(venue_card("AMB Cinemas: Gachibowli", "AMBH"))
    sessions = extract_sessions(data)
    assert sessions
    assert sessions[0]["cinema"] == "AMB Cinemas: Gachibowli"


def test_extract_sessions_parses_session_id():
    data = bms_response(venue_card(sessions=[("7:00 PM", "2", "s-999", "2D")]))
    sessions = extract_sessions(data)
    assert sessions[0]["id"] == "s-999"


def test_extract_sessions_parses_time():
    data = bms_response(venue_card(sessions=[("10:50 PM", "2", "s-1", "Dolby")]))
    sessions = extract_sessions(data)
    assert sessions[0]["time"] == "10:50 PM"


def test_extract_sessions_parses_format_from_attributes():
    data = bms_response(venue_card(sessions=[("6:00 PM", "2", "s-1", "BARCO FLAGSHIP LASER DOLBY ATMOS")]))
    sessions = extract_sessions(data)
    assert sessions[0]["format"] == "BARCO FLAGSHIP LASER DOLBY ATMOS"


def test_extract_sessions_parses_avail_status():
    data = bms_response(
        venue_card(sessions=[
            ("6:00 PM", "2", "s-avail", "2D"),
            ("9:00 PM", "1", "s-sold", "2D"),
            ("11:00 PM", "3", "s-fast", "2D"),
        ])
    )
    sessions = extract_sessions(data)
    statuses = {s["id"]: s["avail_status"] for s in sessions}
    assert statuses["s-avail"] == "2"
    assert statuses["s-sold"] == "1"
    assert statuses["s-fast"] == "3"


def test_extract_sessions_handles_multiple_venues():
    data = bms_response(
        venue_card("PVR Hyderabad", "PVR", [("6:30 PM", "2", "pvr-1", "IMAX")]),
        venue_card("INOX: GVK One", "INOX", [("7:00 PM", "3", "inox-1", "2D")]),
    )
    sessions = extract_sessions(data)
    assert len(sessions) == 2
    cinemas = {s["cinema"] for s in sessions}
    assert "PVR Hyderabad" in cinemas
    assert "INOX: GVK One" in cinemas


def test_extract_sessions_empty_when_no_widgets():
    data = {"data": {"showtimeWidgets": []}}
    sessions = extract_sessions(data)
    assert sessions == []


# ---------------------------------------------------------------------------
# Unit tests for is_session_available()
# ---------------------------------------------------------------------------

def test_is_session_available_status_2():
    assert is_session_available({"avail_status": "2"}) is True


def test_is_session_available_status_3_fast_filling():
    assert is_session_available({"avail_status": "3"}) is True


def test_is_session_available_status_4_almost_full():
    assert is_session_available({"avail_status": "4"}) is True


def test_is_session_available_status_1_sold_out():
    assert is_session_available({"avail_status": "1"}) is False


def test_is_session_available_missing_status():
    assert is_session_available({}) is False


# ---------------------------------------------------------------------------
# Integration tests for BookMyShowProvider.check()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bookmyshow_provider_available():
    client = FakeClient(
        bms_response(
            venue_card(
                "PVR Hyderabad",
                "PVR",
                [("6:30 PM", "2", "session-123", "IMAX")],
            )
        )
    )

    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is True
    assert "BookMyShow" in result["message"]
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["id"] == "session-123"
    assert result["sessions"][0]["cinema"] == "PVR Hyderabad"
    assert result["sessions"][0]["time"] == "6:30 PM"
    assert client.calls[0]["event_code"] == "ET123"
    assert client.calls[0]["date_code"] == "20260920"


@pytest.mark.asyncio
async def test_bookmyshow_provider_not_available_sold_out():
    client = FakeClient(
        bms_response(
            venue_card("PVR Hyderabad", "PVR", [("6:30 PM", "1", "s-sold", "IMAX")])
        )
    )
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is False
    assert "No matching" in result["message"]


@pytest.mark.asyncio
async def test_bookmyshow_provider_not_available_empty_widgets():
    client = FakeClient({"data": {"showtimeWidgets": []}})
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is False
    assert "No matching" in result["message"]


@pytest.mark.asyncio
async def test_bookmyshow_provider_matches_only_requested_theater():
    """Job requests PVR; provider should ignore the INOX venue."""
    client = FakeClient(
        bms_response(
            venue_card("PVR Hyderabad", "PVR", [("6:30 PM", "2", "pvr-1", "IMAX")]),
            venue_card("INOX: GVK One", "INOX", [("7:00 PM", "2", "inox-1", "2D")]),
        )
    )
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job(theater="PVR"))

    assert result["available"] is True
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["id"] == "pvr-1"


@pytest.mark.asyncio
async def test_bookmyshow_provider_handles_client_error():
    class FailingClient:
        async def fetch_showtimes(self, **kwargs):
            raise RuntimeError("BookMyShow unavailable")

    provider = BookMyShowProvider(FailingClient())
    result = await provider.check(make_job())

    assert result["available"] is False
    assert result["error"] is True
    assert result["sessions"] == []
    assert "BookMyShow unavailable" in result["message"]


@pytest.mark.asyncio
async def test_bookmyshow_empty_result_is_not_error():
    client = FakeClient({"data": {"showtimeWidgets": []}})
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is False
    assert result.get("error", False) is False


@pytest.mark.asyncio
async def test_bookmyshow_not_on_sale_is_not_error():
    client = FakeClient({"data": {"someOtherField": []}})
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is False
    assert result.get("error", False) is False
    assert "not currently on sale" in result["message"]


@pytest.mark.asyncio
async def test_bookmyshow_invalid_response_is_not_network_error():
    client = FakeClient({"unexpected": "response"})
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job())

    assert result["available"] is False
    assert result.get("error", False) is False
    assert "unexpected response" in result["message"]


# ---------------------------------------------------------------------------
# Fixture test — uses the JSON fixture file
# ---------------------------------------------------------------------------

def load_fixture():
    path = Path("tests/fixtures/bms_showtimes.json")
    return json.loads(path.read_text())


@pytest.mark.asyncio
async def test_bookmyshow_provider_fixture():
    client = FakeClient(load_fixture())
    provider = BookMyShowProvider(client)
    result = await provider.check(make_job(theater="PVR"))

    assert result["available"] is True
    # fixture has session-001 (avail=2) and session-002 (avail=1/sold)
    # only session-001 should be returned for PVR venue
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["id"] == "session-001"
    assert result["sessions"][0]["cinema"] == "PVR: Nexus Mall"
    assert result["sessions"][0]["time"] == "6:30 PM"
    assert result["sessions"][0]["format"] == "IMAX"
