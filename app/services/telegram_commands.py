from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tracking_job import TrackingJob
from app.models.user import User
from app.services.telegram import send_message
from app.services.job_service import (
    InvalidJobTransition,
    change_job_status,
)

async def handle_start(chat_id: int):
    await send_message(
        chat_id,
        "Welcome to PulseGrid!\n\n"
        "Your Telegram account is authorized.\n\n"
        "Use /help to see available commands.",
    )


async def handle_help(chat_id: int):
    await send_message(
        chat_id,
        "PulseGrid Commands\n\n"
        "/start - Start using PulseGrid\n"
        "/help - Show available commands\n"
        "/jobs - View your tracking jobs\n"
        "/job <id> - View job details\n"
        "/stop <id> - Stop a job\n"
        "/pause <id> - Pause a job\n"
        "/resume <id> - Resume a job",
    )


async def handle_jobs(
    chat_id: int,
    db: Session,
    user: User,
):
    if user.role == "ADMIN":
        statement = select(TrackingJob).order_by(TrackingJob.id)
    else:
        statement = (
            select(TrackingJob)
            .where(TrackingJob.user_id == user.id)
            .order_by(TrackingJob.id)
        )

    jobs = db.scalars(statement).all()

    if not jobs:
        await send_message(
            chat_id,
            "You don't have any tracking jobs yet.",
        )
        return

    lines = ["Your PulseGrid Jobs:\n"]

    for job in jobs:
        lines.append(
            f"#{job.id} | {job.target_name}\n"
            f"Platform: {job.platform}\n"
            f"Location: {job.city} / {job.theater}\n"
            f"Date: {job.target_date}\n"
            f"Status: {job.status}\n"
        )

    await send_message(
        chat_id,
        "\n".join(lines),
    )


async def handle_job(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    try:
        job_id = int(argument)
    except ValueError:
        await send_message(
            chat_id,
            "Usage: /job <job_id>\nExample: /job 1",
        )
        return

    job = db.get(TrackingJob, job_id)

    if job is None:
        await send_message(
            chat_id,
            f"Job #{job_id} was not found.",
        )
        return

    if user.role != "ADMIN" and job.user_id != user.id:
        await send_message(
            chat_id,
            "You do not have access to this job.",
        )
        return

    await send_message(
        chat_id,
        f"Job #{job.id}\n\n"
        f"Target: {job.target_name}\n"
        f"Platform: {job.platform}\n"
        f"City: {job.city}\n"
        f"Theater: {job.theater}\n"
        f"Date: {job.target_date}\n"
        f"Start: {job.start_at}\n"
        f"End: {job.end_at}\n"
        f"Poll interval: {job.poll_interval_seconds} seconds\n"
        f"Status: {job.status}",
    )


async def handle_stop(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    try:
        job_id = int(argument)
    except ValueError:
        await send_message(
            chat_id,
            "Usage: /stop <job_id>\nExample: /stop 1",
        )
        return

    job = db.get(TrackingJob, job_id)

    if job is None:
        await send_message(
            chat_id,
            f"Job #{job_id} was not found.",
        )
        return

    if user.role != "ADMIN" and job.user_id != user.id:
        await send_message(
            chat_id,
            "You do not have access to this job.",
        )
        return

    if job.status in {"STOPPED", "COMPLETED"}:
        await send_message(
            chat_id,
            f"Job #{job.id} is already {job.status.lower()}.",
        )
        return

    try:
        change_job_status(db, job, "STOPPED")
    except InvalidJobTransition:
        await send_message(
            chat_id,
            f"Job #{job.id} cannot be stopped because it is "
            f"{job.status.lower()}.",
        )
        return

    await send_message(
        chat_id,
        f"Job #{job.id} has been stopped.",
    )


async def handle_pause(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    try:
        job_id = int(argument)
    except ValueError:
        await send_message(
            chat_id,
            "Usage: /pause <job_id>\nExample: /pause 1",
        )
        return

    job = db.get(TrackingJob, job_id)

    if job is None:
        await send_message(
            chat_id,
            f"Job #{job_id} was not found.",
        )
        return

    if user.role != "ADMIN" and job.user_id != user.id:
        await send_message(
            chat_id,
            "You do not have access to this job.",
        )
        return

    if job.status == "PAUSED":
        await send_message(
            chat_id,
            f"Job #{job.id} is already paused.",
        )
        return

    if job.status in {"STOPPED", "COMPLETED"}:
        await send_message(
            chat_id,
            f"Job #{job.id} cannot be paused because it is "
            f"{job.status.lower()}.",
        )
        return

    try:
        change_job_status(db, job, "PAUSED")
    except InvalidJobTransition:
        await send_message(
            chat_id,
            f"Job #{job.id} cannot be paused because it is "
            f"{job.status.lower()}.",
        )
        return

    await send_message(
        chat_id,
        f"Job #{job.id} has been paused.",
    )


async def handle_resume(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    try:
        job_id = int(argument)
    except ValueError:
        await send_message(
            chat_id,
            "Usage: /resume <job_id>\nExample: /resume 1",
        )
        return

    job = db.get(TrackingJob, job_id)

    if job is None:
        await send_message(
            chat_id,
            f"Job #{job_id} was not found.",
        )
        return

    if user.role != "ADMIN" and job.user_id != user.id:
        await send_message(
            chat_id,
            "You do not have access to this job.",
        )
        return

    if job.status == "RUNNING":
        await send_message(
            chat_id,
            f"Job #{job.id} is already running.",
        )
        return

    if job.status in {"STOPPED", "COMPLETED"}:
        await send_message(
            chat_id,
            f"Job #{job.id} cannot be resumed because it is "
            f"{job.status.lower()}.",
        )
        return

    try:
        change_job_status(db, job, "RUNNING")
    except InvalidJobTransition:
        await send_message(
            chat_id,
            f"Job #{job.id} cannot be resumed because it is "
            f"{job.status.lower()}.",
        )
        return

    await send_message(
        chat_id,
        f"Job #{job.id} has been resumed.",
    )