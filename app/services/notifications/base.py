from abc import ABC, abstractmethod


class NotificationService(ABC):
    """Interface for sending notifications."""

    @abstractmethod
    async def send(self, recipient: str, message: str) -> None:
        """Send a notification to a recipient."""
        raise NotImplementedError