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
        region_slug=os.getenv("BMS_HYDERABAD_REGION_SLUG", "hyderabad"),
        latitude=os.getenv("BMS_HYDERABAD_LATITUDE", "17.385044"),
        longitude=os.getenv("BMS_HYDERABAD_LONGITUDE", "78.486671"),
    ),
    "mumbai": BookMyShowConfig(
        region_code=os.getenv("BMS_MUMBAI_REGION_CODE", "MUMBAI"),
        region_slug=os.getenv("BMS_MUMBAI_REGION_SLUG", "mumbai"),
        latitude=os.getenv("BMS_MUMBAI_LATITUDE", "19.0760"),
        longitude=os.getenv("BMS_MUMBAI_LONGITUDE", "72.8777"),
    ),
    "bengaluru": BookMyShowConfig(
        region_code=os.getenv("BMS_BENGALURU_REGION_CODE", "BANG"),
        region_slug=os.getenv("BMS_BENGALURU_REGION_SLUG", "bengaluru"),
        latitude=os.getenv("BMS_BENGALURU_LATITUDE", "12.9716"),
        longitude=os.getenv("BMS_BENGALURU_LONGITUDE", "77.5946"),
    ),
    "bangalore": BookMyShowConfig(
        region_code=os.getenv("BMS_BENGALURU_REGION_CODE", "BANG"),
        region_slug=os.getenv("BMS_BENGALURU_REGION_SLUG", "bengaluru"),
        latitude=os.getenv("BMS_BENGALURU_LATITUDE", "12.9716"),
        longitude=os.getenv("BMS_BENGALURU_LONGITUDE", "77.5946"),
    ),
    "chennai": BookMyShowConfig(
        region_code=os.getenv("BMS_CHENNAI_REGION_CODE", "CHEN"),
        region_slug=os.getenv("BMS_CHENNAI_REGION_SLUG", "chennai"),
        latitude=os.getenv("BMS_CHENNAI_LATITUDE", "13.0827"),
        longitude=os.getenv("BMS_CHENNAI_LONGITUDE", "80.2707"),
    ),
    "delhi": BookMyShowConfig(
        region_code=os.getenv("BMS_DELHI_REGION_CODE", "NCR"),
        region_slug=os.getenv("BMS_DELHI_REGION_SLUG", "national-capital-region-ncr"),
        latitude=os.getenv("BMS_DELHI_LATITUDE", "28.6139"),
        longitude=os.getenv("BMS_DELHI_LONGITUDE", "77.2090"),
    ),
    "ncr": BookMyShowConfig(
        region_code=os.getenv("BMS_DELHI_REGION_CODE", "NCR"),
        region_slug=os.getenv("BMS_DELHI_REGION_SLUG", "national-capital-region-ncr"),
        latitude=os.getenv("BMS_DELHI_LATITUDE", "28.6139"),
        longitude=os.getenv("BMS_DELHI_LONGITUDE", "77.2090"),
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