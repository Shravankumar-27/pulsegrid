from collections import defaultdict

from app.models.availability_state import AvailabilityState


class WorkerState:
    def __init__(self):
        self.job_states = defaultdict(
            lambda: AvailabilityState(
                seen_session_ids=set()
            )
        )

    def get_job_state(self, job_id):
        return self.job_states[job_id]

    def clear_job(self, job_id):
        self.job_states.pop(job_id, None)