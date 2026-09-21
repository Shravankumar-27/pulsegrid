from abc import ABC, abstractmethod


class HttpTransport(ABC):

    @abstractmethod
    async def get(self, url: str, *, params=None, headers=None):
        pass