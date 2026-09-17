from abc import ABC, abstractmethod

from app.models.tracking_job import TrackingJob


class BaseProvider(ABC):

    @abstractmethod
    async def check(self, job: TrackingJob) -> dict:
        pass