import asyncio
from datetime import datetime, timezone
import logging

from app.database import SessionLocal
from app.models.tracking_job import TrackingJob
from app.services.providers.factory import get_provider
from app.services.availability_tracker import get_new_sessions
from app.utils.time import format_ist

logger = logging.getLogger("pulsegrid.worker")

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
    title = getattr(job, "movie_name", None) or job.target_name
    checked_time_ist = format_ist(getattr(job, "last_checked_at", None) or datetime.now(timezone.utc))
    message = (
        f"🎟️ PulseGrid Alert\n\n"
        f"Movie: {title}\n"
        f"Target: {job.target_name}\n"
        f"Platform: {job.platform}\n"
        f"City: {job.city}\n"
        f"Theater: {job.theater}\n"
        f"Time (IST): {checked_time_ist}\n\n"
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
    raw_sessions = result.get("sessions", [])
    job.last_result_json = {
        "available": result.get("available", False),
        "message": result.get("message", ""),
        "sessions": raw_sessions,
        "sessions_count": len(raw_sessions),
        "last_checked_at": job.last_checked_at.isoformat(),
        "last_checked_at_ist": format_ist(job.last_checked_at),
    }

    if result.get("available") is True and notification_service is not None:
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
        raw_sessions = provider_result.get("sessions", [])
        job.last_result_json = {
            "available": bool(raw_sessions),
            "message": provider_result.get("message", ""),
            "sessions": raw_sessions,
            "sessions_count": len(raw_sessions),
            "last_checked_at": job.last_checked_at.isoformat(),
            "last_checked_at_ist": format_ist(job.last_checked_at),
        }

        result["checked"] += 1

        if (
            provider_result.get("available") is True
            and notification_service is not None
        ):
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


async def run_embedded_worker(
    poll_interval: float = 15.0,
    notification_service=None,
    worker_state=None,
):
    """
    Background asyncio task for FastAPI lifespan.
    Runs worker cycles periodically inside the web server process.
    """
    from app.services.notifications.telegram import TelegramNotification
    from app.config import settings
    from app.worker.state import WorkerState

    if notification_service is None and settings.telegram_bot_token:
        notification_service = TelegramNotification(settings.telegram_bot_token)
    if worker_state is None:
        worker_state = WorkerState(persist_path="data/worker_state.json")

    logger.info("Embedded PulseGrid worker task started.")
    while True:
        db = SessionLocal()
        try:
            result = await run_worker_cycle(
                db=db,
                notification_service=notification_service,
                worker_state=worker_state,
            )
            worker_state.save()
            if result["checked"] > 0 or result["completed"] > 0:
                logger.info(
                    f"Embedded worker cycle: checked={result['checked']} "
                    f"notified={result['notified']} skipped={result['skipped']} "
                    f"completed={result['completed']}"
                )
        except asyncio.CancelledError:
            logger.info("Embedded worker task cancelled.")
            break
        except Exception as exc:
            logger.error(f"Embedded worker cycle error: {exc}")
        finally:
            db.close()

        await asyncio.sleep(poll_interval)