import pytest

from app.services.providers.bookmyshow_config import (
    get_city_config,
)


def test_hyderabad_config():
    config = get_city_config("Hyderabad")

    assert config.region_code == "HYD"
    assert config.region_slug == "hyderabad"


def test_city_is_case_insensitive():
    config = get_city_config("HYDERABAD")

    assert config.region_code == "HYD"


def test_unknown_city_rejected():
    with pytest.raises(ValueError, match="Unsupported BookMyShow city"):
        get_city_config("Mumbai")

def test_hyderabad_config_has_location():
    config = get_city_config("Hyderabad")

    assert config.latitude == "17.3850"
    assert config.longitude == "78.4867"