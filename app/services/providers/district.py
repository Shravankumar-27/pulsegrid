"""District provider placeholder.

District retrieval is the next provider research milestone. The factory
and BaseProvider contract are ready; implement client/transport here when
District endpoints are mapped the same way BMS was.
"""

from app.models.tracking_job import TrackingJob
from app.services.providers.base import BaseProvider
from app.services.providers.result import AvailabilityResult


class DistrictProvider(BaseProvider):
    async def check(self, job: TrackingJob) -> dict:
        return AvailabilityResult(
            available=False,
            message=(
                "District provider is not implemented yet. "
                "Track BookMyShow jobs for now."
            ),
            sessions=[],
        ).to_dict()
