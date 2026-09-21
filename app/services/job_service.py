from sqlalchemy.orm import Session

from app.models.tracking_job import TrackingJob
from app.models.user import User
from app.schemas.tracking_job import TrackingJobCreate
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

def create_tracking_job(
    db: Session,
    user: User,
    job_data: TrackingJobCreate,
) -> TrackingJob:
    new_job = TrackingJob(
        user_id=user.id,
        target_name=job_data.target_name,
        platform=job_data.platform,
        city=job_data.city,
        theater=job_data.theater,
        movie_name=job_data.movie_name,
        theater_id=job_data.theater_id,
        target_date=job_data.target_date,
        start_at=job_data.start_at,
        end_at=job_data.end_at,
        poll_interval_seconds=job_data.poll_interval_seconds,
        status="PENDING",
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


def create_watch_jobs(
    db: Session,
    user: User,
    payload,
):
    """Create one job per selected platform; optionally start them."""
    from app.schemas.tracking_job import TrackingJobCreate
    from app.schemas.watch_job import WatchJobResponse
    from app.services.theater_service import (
        get_theater_for_user,
        upsert_theater_by_name,
    )

    theater = None
    theater_name = "Any"

    if payload.theater_id is not None:
        theater = get_theater_for_user(db, payload.theater_id, user)
        theater_name = theater.name
        if bookmyshow_venue := payload.bookmyshow_venue_id:
            theater.bookmyshow_venue_id = bookmyshow_venue
        if district_venue := payload.district_venue_id:
            theater.district_venue_id = district_venue
        db.commit()
        db.refresh(theater)
    elif payload.theater_name and payload.theater_name.lower() != "any":
        theater = upsert_theater_by_name(
            db,
            user,
            name=payload.theater_name,
            city=payload.city,
            bookmyshow_venue_id=payload.bookmyshow_venue_id,
            district_venue_id=payload.district_venue_id,
        )
        theater_name = theater.name
    else:
        theater_name = "Any"

    target_by_platform = {
        "bookmyshow": payload.bookmyshow_target,
        "district": payload.district_target,
    }

    jobs = []
    for platform in payload.platforms:
        job = create_tracking_job(
            db=db,
            user=user,
            job_data=TrackingJobCreate(
                target_name=target_by_platform[platform],
                platform=platform,
                city=payload.city,
                theater=theater_name,
                movie_name=payload.movie_name,
                theater_id=theater.id if theater else None,
                target_date=payload.start_at.date(),
                start_at=payload.start_at,
                end_at=payload.end_at,
                poll_interval_seconds=payload.poll_interval_seconds,
            ),
        )
        if payload.start_immediately:
            try:
                job = change_job_status(db, job, "RUNNING")
            except InvalidJobTransition:
                pass
        jobs.append(job)

    return WatchJobResponse(jobs=jobs, theater=theater)

def delete_tracking_job(
    db: Session,
    job_id: int,
    user: User,
) -> None:
    job = get_job_for_user(
        db=db,
        job_id=job_id,
        user=user,
    )

    db.delete(job)
    db.commit()