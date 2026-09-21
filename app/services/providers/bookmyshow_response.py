def classify_response(data: dict) -> str:
    """
    Classify a BookMyShow response.

    Returns:
        "showtimes"       -> showtime data is present
        "not_on_sale"     -> valid response but showtimes are absent
        "invalid"         -> unexpected response shape
    """

    if not isinstance(data, dict):
        return "invalid"

    payload = data.get("data")

    if not isinstance(payload, dict):
        return "invalid"

    if "showtimeWidgets" in payload:
        return "showtimes"

    return "not_on_sale"