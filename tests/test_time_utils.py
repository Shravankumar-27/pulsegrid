from datetime import datetime, timezone, timedelta
from app.utils.time import to_ist, format_ist, to_ist_iso, IST_OFFSET, IST_TZ


def test_to_ist_conversion():
    utc_dt = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    ist_dt = to_ist(utc_dt)
    
    assert ist_dt is not None
    assert ist_dt.hour == 16
    assert ist_dt.minute == 0
    assert ist_dt.tzinfo == IST_TZ


def test_format_ist():
    utc_dt = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    formatted = format_ist(utc_dt)
    
    assert formatted is not None
    assert "21 Sep 2026" in formatted
    assert "04:00 PM IST" in formatted


def test_none_handling():
    assert to_ist(None) is None
    assert format_ist(None) is None
    assert to_ist_iso(None) is None
