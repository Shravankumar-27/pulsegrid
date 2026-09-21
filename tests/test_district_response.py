"""Unit tests for District response parsing (fixture only — no network)."""

from pathlib import Path
import json

from app.services.providers.district_client import ensure_city_in_url
from app.services.providers.district_response import (
    classify_response,
    extract_sessions,
)


FIXTURE = Path("tests/fixtures/district_next_data.json")


def _page_props() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_classify_showtimes():
    assert classify_response(_page_props()) == "showtimes"


def test_classify_empty():
    assert classify_response({"data": {"serverState": {}}}) == "not_on_sale"


def test_extract_sessions_from_fixture():
    sessions = extract_sessions(_page_props())
    assert len(sessions) > 0
    sample = sessions[0]
    assert sample["id"]
    assert sample["cinema"]
    assert sample["time"]
    assert sample["avail_status"] in {"1", "2", "3", "4", "0"}


def test_ensure_city_in_url():
    url = "https://www.district.in/movies/mirzapur-the-movie-movie-tickets-MV181196"
    out = ensure_city_in_url(url, "hyderabad")
    assert "-in-hyderabad-MV181196" in out
    assert ensure_city_in_url(out, "hyderabad") == out
