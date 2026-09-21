"""
Timezone and date formatting utilities for PulseGrid.

Defaults to Indian Standard Time (IST / UTC+05:30) as primary timezone.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)
IST_TZ = timezone(IST_OFFSET, name="IST")


def to_ist(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST_TZ)


def format_ist(dt: datetime | None, format_str: str = "%d %b %Y, %I:%M %p IST") -> str | None:
    ist_dt = to_ist(dt)
    if ist_dt is None:
        return None
    return ist_dt.strftime(format_str)


def to_ist_iso(dt: datetime | None) -> str | None:
    ist_dt = to_ist(dt)
    if ist_dt is None:
        return None
    return ist_dt.isoformat()
