from app.database import SessionLocal
from app.models.tracking_job import TrackingJob
from datetime import datetime, timezone


def get_running_jobs():
    db = SessionLocal()

    try:
        return (
            db.query(TrackingJob)
            .filter(TrackingJob.status == "RUNNING")
            .all()
        )
    finally:
        db.close()

def is_job_expired(job):
    end_at = job.end_at

    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) >= end_at

def complete_expired_jobs():
    db = SessionLocal()

    try:
        jobs = (
            db.query(TrackingJob)
            .filter(TrackingJob.status == "RUNNING")
            .all()
        )

        completed_count = 0

        for job in jobs:
            if is_job_expired(job):
                job.status = "COMPLETED"
                completed_count += 1

        db.commit()

        return completed_count

    finally:
        db.close()

def run_worker_cycle():
    completed_count = complete_expired_jobs()

    return {
        "completed": completed_count,
    }