import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BookMyShowConfig:
    region_code: str
    region_slug: str
    latitude: str
    longitude: str


CITY_CONFIG = {
    "hyderabad": BookMyShowConfig(
        region_code=os.getenv("BMS_HYDERABAD_REGION_CODE", "HYD"),
        region_slug=os.getenv(
            "BMS_HYDERABAD_REGION_SLUG",
            "hyderabad",
        ),
        latitude=os.getenv(
            "BMS_HYDERABAD_LATITUDE",
            "17.3850",
        ),
        longitude=os.getenv(
            "BMS_HYDERABAD_LONGITUDE",
            "78.4867",
        ),
    ),
}


def get_city_config(city: str) -> BookMyShowConfig:
    key = city.strip().lower()

    try:
        return CITY_CONFIG[key]
    except KeyError:
        raise ValueError(
            f"Unsupported BookMyShow city: {city}"
        )