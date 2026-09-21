from dataclasses import dataclass


@dataclass
class AvailabilityResult:
    available: bool
    message: str
    sessions: list[dict]

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "message": self.message,
            "sessions": self.sessions,
        }