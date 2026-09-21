import pytest

from app.services.providers.factory import get_provider
from app.services.providers.mock import MockProvider
from app.services.providers.bookmyshow import BookMyShowProvider
from app.services.providers.district import DistrictProvider


def test_get_mock_provider():
    provider = get_provider("mock")

    assert isinstance(provider, MockProvider)


def test_get_mock_provider_case_insensitive():
    provider = get_provider("MoCk")

    assert isinstance(provider, MockProvider)


def test_get_provider_rejects_unknown_platform():
    with pytest.raises(ValueError, match="Unsupported provider"):
        get_provider("unknown")

def test_get_bookmyshow_provider():
    provider = get_provider("bookmyshow")

    assert isinstance(provider, BookMyShowProvider)


def test_get_bookmyshow_provider_case_insensitive():
    provider = get_provider("BOOKMYSHOW")

    assert isinstance(provider, BookMyShowProvider)

def test_get_district_provider():
    provider = get_provider("district")

    assert isinstance(provider, DistrictProvider)

