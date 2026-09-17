from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.tracking_job import TrackingJob


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


def should_poll(job):
    now = datetime.now(timezone.utc)

    if job.last_checked_at is None:
        return True

    last_checked_at = job.last_checked_at

    if last_checked_at.tzinfo is None:
        last_checked_at = last_checked_at.replace(tzinfo=timezone.utc)

    elapsed_seconds = (now - last_checked_at).total_seconds()

    return elapsed_seconds >= job.poll_interval_seconds


def build_notification_message(job, result):
    return (
        f"🎟️ PulseGrid Alert\n\n"
        f"Target: {job.target_name}\n"
        f"Platform: {job.platform}\n"
        f"City: {job.city}\n"
        f"Theater: {job.theater}\n\n"
        f"{result.get('message', 'Availability detected.')}"
    )


async def process_job(job, provider, notification_service):
    """
    Process one tracking job.

    Returns:
        "completed" -> job expired
        "skipped"   -> polling is not due
        provider result -> provider was checked
    """

    if is_job_expired(job):
        job.status = "COMPLETED"
        return "completed"

    if not should_poll(job):
        return "skipped"

    result = await provider.check(job)

    job.last_checked_at = datetime.now(timezone.utc)

    if result.get("available") is True:
        recipient = str(job.user.telegram_user_id)

        message = build_notification_message(
            job,
            result,
        )

        await notification_service.send(
            recipient=recipient,
            message=message,
        )

    return result


async def run_worker_cycle(
    db,
    provider,
    notification_service,
):
    """
    Run one complete worker cycle.

    The worker:
    1. Finds RUNNING jobs.
    2. Completes expired jobs.
    3. Checks jobs that are due for polling.
    4. Calls the provider.
    5. Sends notifications when availability is detected.
    6. Commits database changes.
    """

    jobs = (
        db.query(TrackingJob)
        .filter(TrackingJob.status == "RUNNING")
        .all()
    )

    result = {
        "completed": 0,
        "checked": 0,
        "skipped": 0,
        "notified": 0,
    }

    for job in jobs:
        if is_job_expired(job):
            job.status = "COMPLETED"
            result["completed"] += 1
            continue

        if not should_poll(job):
            result["skipped"] += 1
            continue

        provider_result = await provider.check(job)

        job.last_checked_at = datetime.now(timezone.utc)

        result["checked"] += 1

        if provider_result.get("available") is True:
            recipient = str(job.user.telegram_user_id)

            message = build_notification_message(
                job,
                provider_result,
            )

            await notification_service.send(
                recipient=recipient,
                message=message,
            )

            result["notified"] += 1

    db.commit()

    return result