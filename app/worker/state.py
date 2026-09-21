from collections import defaultdict
import json
from pathlib import Path

from app.models.availability_state import AvailabilityState


class WorkerState:
    """
    In-memory per-job availability state with optional JSON persistence.

    Persistence prevents re-notifying the same BMS sessions after a
    worker restart.
    """

    def __init__(self, persist_path: Path | str | None = None):
        self.persist_path = Path(persist_path) if persist_path else None
        self.job_states: dict[int, AvailabilityState] = defaultdict(
            lambda: AvailabilityState(seen_session_ids=set())
        )
        if self.persist_path:
            self.load()

    def get_job_state(self, job_id) -> AvailabilityState:
        return self.job_states[job_id]

    def clear_job(self, job_id) -> None:
        self.job_states.pop(job_id, None)

    def load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return

        raw = json.loads(self.persist_path.read_text(encoding="utf-8"))
        jobs = raw.get("jobs", raw) if isinstance(raw, dict) else {}
        for job_id, payload in jobs.items():
            ids = payload.get("seen_session_ids", []) if isinstance(payload, dict) else payload
            self.job_states[int(job_id)] = AvailabilityState(
                seen_session_ids=set(str(x) for x in ids)
            )

    def save(self) -> None:
        if not self.persist_path:
            return

        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "jobs": {
                str(job_id): {
                    "seen_session_ids": sorted(state.seen_session_ids),
                }
                for job_id, state in self.job_states.items()
            }
        }
        self.persist_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
