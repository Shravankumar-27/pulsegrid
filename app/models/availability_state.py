from dataclasses import dataclass


@dataclass
class AvailabilityState:
    seen_session_ids: set[str]

    def is_new(self, session_id: str) -> bool:
        return session_id not in self.seen_session_ids

    def mark_seen(self, session_id: str) -> None:
        self.seen_session_ids.add(session_id)