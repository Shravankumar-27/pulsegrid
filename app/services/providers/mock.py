from app.models.tracking_job import TrackingJob

from app.services.providers.base import BaseProvider


class MockProvider(BaseProvider):

    async def check(self, job: TrackingJob) -> dict:
        return {
            "available": True,
            "message": "Mock provider check successful",
        }