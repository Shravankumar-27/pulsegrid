import pytest

from app.services.providers.bookmyshow_config import get_city_config


def test_hyderabad_config():
    config = get_city_config("Hyderabad")

    assert config.region_code == "HYD"
    assert config.region_slug == "hyderabad"


def test_city_is_case_insensitive():
    config = get_city_config("HYDERABAD")

    assert config.region_code == "HYD"


def test_mumbai_config():
    config = get_city_config("Mumbai")
    assert config.region_code == "MUMBAI"
    assert config.region_slug == "mumbai"


def test_unknown_city_rejected():
    with pytest.raises(ValueError, match="Unsupported BookMyShow city"):
        get_city_config("Atlantis")


def test_hyderabad_config_has_location():
    config = get_city_config("Hyderabad")

    assert config.latitude.startswith("17.385")
    assert config.longitude.startswith("78.486")
