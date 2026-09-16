from sqlalchemy.orm import Session

from app.models.tracking_job import TrackingJob
from app.models.user import User

class InvalidJobTransition(Exception):
    pass


ALLOWED_TRANSITIONS = {
    "PENDING": {"RUNNING", "STOPPED"},
    "RUNNING": {"PAUSED", "STOPPED", "COMPLETED"},
    "PAUSED": {"RUNNING", "STOPPED"},
    "STOPPED": set(),
    "COMPLETED": set(),
}


def change_job_status(
    db: Session,
    job: TrackingJob,
    new_status: str,
) -> TrackingJob:
    current_status = job.status

    allowed_statuses = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_statuses:
        raise InvalidJobTransition(
            f"Cannot change job from {current_status} to {new_status}"
        )

    job.status = new_status

    db.commit()
    db.refresh(job)

    return job

def get_job_for_user(
    db: Session,
    job_id: int,
    user: User,
) -> TrackingJob:
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise ValueError("Job not found")

    if user.role != "ADMIN" and job.user_id != user.id:
        raise PermissionError("You do not have access to this job")

    return job