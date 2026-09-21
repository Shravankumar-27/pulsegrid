"""
District response parsing.

District SSR embeds showtimes in ``__NEXT_DATA__``:

    props.pageProps.data.serverState.movieSessions[*].arrangedSessions[]
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def classify_response(page_props: dict) -> str:
    if not isinstance(page_props, dict):
        return "invalid"

    sessions_root = (
        ((page_props.get("data") or {}).get("serverState") or {}).get("movieSessions")
    )
    if not isinstance(sessions_root, dict) or not sessions_root:
        return "not_on_sale"

    return "showtimes"


def _display_time(show_time: str) -> str:
    """Convert District UTC-naive ``showTime`` → IST clock string."""
    if not show_time:
        return ""
    try:
        dt = datetime.fromisoformat(show_time)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return show_time


def _avail_status(session: dict) -> str:
    """
    Map District seat status into BMS-compatible avail codes for the worker.

    District uses seatStatus / statusColor:
      Available / G → bookable
      Fast Filling / O → bookable
      Sold Out / R → not bookable
    """
    status = str(session.get("seatStatus") or "").strip().lower()
    color = str(session.get("statusColor") or "").strip().upper()

    if status in {"sold out", "unavailable"} or color == "R":
        return "1"
    if status in {"fast filling", "almost full"} or color == "O":
        return "3"
    if status in {"available", ""} or color in {"G", ""}:
        # Prefer numeric avail when present
        avail = session.get("avail")
        total = session.get("total")
        try:
            if avail is not None and total:
                ratio = float(avail) / float(total)
                if ratio <= 0:
                    return "1"
                if ratio < 0.15:
                    return "4"
                if ratio < 0.4:
                    return "3"
        except (TypeError, ValueError):
            pass
        return "2"
    return "0"


def extract_sessions(page_props: dict) -> list[dict]:
    """
    Extract worker-shaped session dicts from District pageProps.
    """
    sessions_root = (
        ((page_props.get("data") or {}).get("serverState") or {}).get("movieSessions")
        or {}
    )
    if not isinstance(sessions_root, dict):
        return []

    out: list[dict] = []

    for block in sessions_root.values():
        if not isinstance(block, dict):
            continue
        arranged = block.get("arrangedSessions") or []
        if not isinstance(arranged, list):
            continue

        for cinema in arranged:
            if not isinstance(cinema, dict):
                continue

            add = cinema.get("data") or {}
            venue_name = (
                cinema.get("entityName")
                or add.get("name")
                or add.get("label")
                or "Unknown Theater"
            )
            venue_code = str(
                cinema.get("entityCode")
                or add.get("id")
                or ""
            )

            for show in cinema.get("sessions") or []:
                if not isinstance(show, dict):
                    continue

                show_id = (
                    show.get("encSessionId")
                    or show.get("sid")
                    or show.get("mid")
                )
                if not show_id:
                    continue

                fmt = (
                    show.get("premiumLabel")
                    or show.get("scrnFmt")
                    or show.get("audi")
                    or ""
                )

                out.append(
                    {
                        "id": str(show_id),
                        "cinema": venue_name,
                        "venue_code": venue_code,
                        "time": _display_time(str(show.get("showTime") or "")),
                        "show_dt": str(show.get("showTime") or ""),
                        "format": str(fmt),
                        "avail_status": _avail_status(show),
                    }
                )

    return out
