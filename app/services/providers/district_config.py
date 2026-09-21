"""District (district.in) city configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DistrictConfig:
    city_slug: str
    city_label: str


CITY_CONFIG = {
    "hyderabad": DistrictConfig("hyderabad", "Hyderabad"),
    "mumbai": DistrictConfig("mumbai", "Mumbai"),
    "bengaluru": DistrictConfig("bengaluru", "Bengaluru"),
    "bangalore": DistrictConfig("bengaluru", "Bengaluru"),
    "chennai": DistrictConfig("chennai", "Chennai"),
    "delhi": DistrictConfig("delhi-ncr", "Delhi NCR"),
    "ncr": DistrictConfig("delhi-ncr", "Delhi NCR"),
    "gurgaon": DistrictConfig("gurgaon", "Gurgaon"),
    "gurugram": DistrictConfig("gurgaon", "Gurgaon"),
}


def get_city_config(city: str) -> DistrictConfig:
    key = city.strip().lower()
    try:
        return CITY_CONFIG[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported District city: {city}") from exc


def movies_base_url() -> str:
    return os.getenv("DISTRICT_BASE_URL", "https://www.district.in").rstrip("/")
