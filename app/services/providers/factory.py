from app.services.providers.base import BaseProvider
from app.services.providers.bookmyshow import BookMyShowProvider
from app.services.providers.mock import MockProvider


def get_provider(platform: str) -> BaseProvider:
    platform = platform.strip().lower()

    if platform == "mock":
        return MockProvider()

    if platform == "bookmyshow":
        return BookMyShowProvider()

    raise ValueError(f"Unsupported provider: {platform}")