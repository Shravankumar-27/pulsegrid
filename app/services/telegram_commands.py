from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date, datetime, time, timezone

from app.models.tracking_job import TrackingJob
from app.models.user import User
from app.services.telegram import send_message
from app.services.job_service import (
    InvalidJobTransition,
    change_job_status,
    create_tracking_job,
    delete_tracking_job,
    get_job_for_user,
)
from pydantic import ValidationError

from app.schemas.tracking_job import TrackingJobCreate

def parse_track_command(argument: str) -> TrackingJobCreate:
    fields = [
        field.strip()
        for field in argument.splitlines()
        if field.strip()
    ]

    if len(fields) != 8:
        raise ValueError(
            "Usage:\n"
            "/track\n"
            "<target>\n"
            "<platform>\n"
            "<city>\n"
            "<theater>\n"
            "<date>\n"
            "<start time>\n"
            "<end time>\n"
            "<poll interval>\n\n"
            "Platforms: bookmyshow | district\n"
            "BookMyShow target: ET code (ET00514261)\n"
            "District target: MV code (MV181196) or movie URL\n"
            "Theater: Any for all venues"
        )

    (
        target_name,
        platform,
        city,
        theater,
        target_date,
        start_time,
        end_time,
        poll_interval,
    ) = fields

    try:
        parsed_date = date.fromisoformat(target_date)

        parsed_start = datetime.combine(
            parsed_date,
            time.fromisoformat(start_time),
            tzinfo=timezone.utc,
        )

        parsed_end = datetime.combine(
            parsed_date,
            time.fromisoformat(end_time),
            tzinfo=timezone.utc,
        )

        parsed_poll_interval = int(poll_interval)

    except ValueError as exc:
        raise ValueError(
            "Invalid date, time, or poll interval.\n"
            "Use:\n"
            "Date: YYYY-MM-DD\n"
            "Time: HH:MM\n"
            "Poll interval: seconds"
        ) from exc

    return TrackingJobCreate(
        target_name=target_name,
        platform=platform,
        city=city,
        theater=theater,
        target_date=parsed_date,
        start_at=parsed_start,
        end_at=parsed_end,
        poll_interval_seconds=parsed_poll_interval,
    )

async def handle_track(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    if not argument.strip():
        await send_message(
            chat_id,
            "Usage:\n\n"
            "/track\n"
            "Target\n"
            "Platform (bookmyshow | district)\n"
            "City\n"
            "Theater (or Any)\n"
            "YYYY-MM-DD\n"
            "HH:MM\n"
            "HH:MM\n"
            "Poll interval in seconds\n\n"
            "BookMyShow target: ET00514261\n"
            "District target: MV181196",
        )
        return

    try:
        job_data = parse_track_command(argument)
    except (ValueError, ValidationError) as exc:
        message = str(exc)
        if isinstance(exc, ValidationError):
            message = "; ".join(
                err.get("msg", str(err)) for err in exc.errors()
            )
        await send_message(
            chat_id,
            f"❌ {message}",
        )
        return

    try:
        job = create_tracking_job(
            db=db,
            user=user,
            job_data=job_data,
        )
        # Start monitoring immediately so /track is enough for MVP use.
        job = change_job_status(db, job, "RUNNING")
    except InvalidJobTransition:
        await send_message(
            chat_id,
            f"✅ Tracking job #{job.id} created (PENDING).\n"
            f"Use /resume {job.id} to start monitoring.",
        )
        return
    except Exception:
        await send_message(
            chat_id,
            "❌ Failed to create tracking job.",
        )
        return

    await send_message(
        chat_id,
        f"✅ Tracking job #{job.id} created and running!\n\n"
        f"🎬 Target: {job.target_name}\n"
        f"📺 Platform: {job.platform}\n"
        f"📍 City: {job.city}\n"
        f"🏢 Theater: {job.theater}\n"
        f"📅 Date: {job.target_date}\n"
        f"⏰ {job.start_at.strftime('%H:%M')} - "
        f"{job.end_at.strftime('%H:%M')}\n"
        f"🔄 Poll interval: {job.poll_interval_seconds}s\n"
        f"📌 Status: {job.status}\n\n"
        f"Tips:\n"
        f"• bookmyshow → Target = ET code (ET00514261)\n"
        f"• district → Target = MV code (MV181196) or movie URL\n"
        f"• Theater Any = all venues",
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
        "/track - Create and start a tracking job\n"
        "/jobs - View your tracking jobs\n"
        "/job <id> - View job details\n"
        "/status - Show tracking summary\n"
        "/pause <id> - Pause a job\n"
        "/resume <id> - Resume / start a pending job\n"
        "/stop <id> - Stop a job\n"
        "/delete <id> - Delete a tracking job\n\n"
        "Platforms: bookmyshow | district\n"
        "BookMyShow target: ET code (e.g. ET00514261)\n"
        "District target: MV code (e.g. MV181196) or movie URL\n"
        "Theater can be Any for all venues.",
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

async def route_command(
    command: str,
    argument: str,
    chat_id: int,
    db: Session,
    user: User,
):
    if command == "/start":
        await handle_start(chat_id)

    elif command == "/help":
        await handle_help(chat_id)

    elif command == "/jobs":
        await handle_jobs(
            chat_id,
            db,
            user,
        )

    elif command == "/job":
        await handle_job(
            chat_id,
            db,
            user,
            argument,
        )

    elif command == "/stop":
        await handle_stop(
            chat_id,
            db,
            user,
            argument,
        )

    elif command == "/pause":
        await handle_pause(
            chat_id,
            db,
            user,
            argument,
        )

    elif command == "/resume":
        await handle_resume(
            chat_id,
            db,
            user,
            argument,
        )
    elif command == "/track":
        await handle_track(
            chat_id,
            db,
            user,
            argument,
        )
    elif command == "/delete":
        await handle_delete(
            chat_id,
            db,
            user,
            argument,
        )
    elif command == "/status":
        await handle_status(
            chat_id,
            db,
            user,
        )
    else:
        await send_message(
            chat_id,
            "I don't understand that command.\n"
            "Use /help to see available commands.",
        )

async def handle_delete(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    parts = argument.strip().split()

    if not parts:
        await send_message(
            chat_id,
            "Usage:\n"
            "/delete <job_id>\n\n"
            "Example:\n"
            "/delete 12",
        )
        return

    try:
        job_id = int(parts[0])
    except ValueError:
        await send_message(
            chat_id,
            "❌ Job ID must be a number.",
        )
        return

    try:
        job = get_job_for_user(
            db=db,
            job_id=job_id,
            user=user,
        )
    except ValueError:
        await send_message(
            chat_id,
            "❌ Job not found.",
        )
        return
    except PermissionError:
        await send_message(
            chat_id,
            "❌ You do not have access to this job.",
        )
        return

    if len(parts) < 2 or parts[1].lower() != "confirm":
        await send_message(
            chat_id,
            f"⚠️ Delete tracking job #{job.id}?\n\n"
            f"Target: {job.target_name}\n"
            f"Theater: {job.theater}\n\n"
            f"To confirm, send:\n"
            f"/delete {job.id} confirm",
        )
        return

    target_name = job.target_name

    delete_tracking_job(
        db=db,
        job_id=job.id,
        user=user,
    )

    await send_message(
        chat_id,
        f"🗑️ Tracking job #{job.id} deleted.\n"
        f"Target: {target_name}",
    )

def parse_command(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)

    if not parts:
        return "", ""

    command = parts[0].lower()
    argument = parts[1] if len(parts) > 1 else ""

    return command, argument

async def handle_status(
    chat_id: int,
    db: Session,
    user: User,
):
    query = select(TrackingJob)

    if user.role != "ADMIN":
        query = query.where(
            TrackingJob.user_id == user.id
        )

    jobs = db.execute(query).scalars().all()

    counts = {
        "PENDING": 0,
        "RUNNING": 0,
        "PAUSED": 0,
        "COMPLETED": 0,
        "STOPPED": 0,
    }

    for job in jobs:
        if job.status in counts:
            counts[job.status] += 1

    await send_message(
        chat_id,
        "📊 PulseGrid Status\n\n"
        f"Total jobs: {len(jobs)}\n"
        f"🟡 Pending: {counts['PENDING']}\n"
        f"🟢 Running: {counts['RUNNING']}\n"
        f"⏸️ Paused: {counts['PAUSED']}\n"
        f"✅ Completed: {counts['COMPLETED']}\n"
        f"🛑 Stopped: {counts['STOPPED']}",
    )