from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.tracking_job import TrackingJob
from app.services.providers.factory import get_provider
from app.services.availability_tracker import get_new_sessions

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
    message = (
        f"🎟️ PulseGrid Alert\n\n"
        f"Target: {job.target_name}\n"
        f"Platform: {job.platform}\n"
        f"City: {job.city}\n"
        f"Theater: {job.theater}\n\n"
    )

    sessions = result.get("sessions", [])

    if sessions:
        message += "🎬 New showtime available!\n\n"

        for session in sessions:
            message += (
                f"🕐 {session.get('time', 'Unknown time')}\n"
                f"🎞️ {session.get('format', 'Unknown format')}\n"
                f"🏢 {session.get('cinema', 'Unknown theater')}\n"
                f"🆔 {session.get('id', 'Unknown')}\n\n"
            )
    else:
        message += result.get(
            "message",
            "Availability detected.",
        )

    return message.strip()

async def process_job(
        job,
        provider,
        notification_service,
        worker_state=None,
    ):
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

    if result.get("available") is True and worker_state is not None:
        state = worker_state.get_job_state(job.id)

        new_sessions = get_new_sessions(
            result.get("sessions", []),
            state,
        )

        result["sessions"] = new_sessions
        result["available"] = bool(new_sessions)

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
    provider=None,
    notification_service=None,
    worker_state=None,
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

            if worker_state is not None:
                worker_state.clear_job(job.id)

            result["completed"] += 1
            continue

        if not should_poll(job):
            result["skipped"] += 1
            continue

        job_provider = provider or get_provider(job.platform)


        provider_result = await job_provider.check(job)

        if (
        provider_result.get("available") is True
        and worker_state is not None):

            state = worker_state.get_job_state(job.id)

            new_sessions = get_new_sessions(
                provider_result.get("sessions", []),
                state,
            )

            provider_result["sessions"] = new_sessions
            provider_result["available"] = bool(new_sessions)

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

async def process_running_job(
    job,
    notification_service,
    worker_state=None,
):
    provider = get_provider(job.platform)

    if worker_state is None:
        result = await process_job(
            job,
            provider,
            notification_service,
        )
    else:
        result = await process_job(
            job,
            provider,
            notification_service,
            worker_state=worker_state,
        )

    return result