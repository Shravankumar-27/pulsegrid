from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta, timezone

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

IST = timezone(timedelta(hours=5, minutes=30))

TRACK_USAGE = (
    "Create a tracking job:\n\n"
    "Easy (recommended):\n"
    "/track ET00514261 bookmyshow Hyderabad\n"
    "/track MV181196 district Hyderabad\n\n"
    "Optional extras:\n"
    "/track <target> <platform> <city> [theater] [YYYY-MM-DD]\n\n"
    "Defaults if omitted:\n"
    "• Theater = Any\n"
    "• Date = today (IST)\n"
    "• Window = 00:00–23:59\n"
    "• Poll = 60 seconds\n\n"
    "Full form (8 lines) still works for custom windows."
)


def _today_ist() -> date:
    return datetime.now(IST).date()


def _split_track_fields(argument: str) -> list[str]:
    raw = argument.strip()
    if "\n" in raw:
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return raw.split()


def parse_track_command(argument: str) -> TrackingJobCreate:
    fields = _split_track_fields(argument)

    if len(fields) not in {3, 4, 5, 8}:
        raise ValueError(TRACK_USAGE)

    target_name = fields[0]
    platform = fields[1]
    city = fields[2]

    theater = "Any"
    target_date = _today_ist()
    start_clock = time(0, 0)
    end_clock = time(23, 59)
    poll_interval = 60

    if len(fields) == 4:
        theater = fields[3]
    elif len(fields) == 5:
        theater = fields[3]
        try:
            target_date = date.fromisoformat(fields[4])
        except ValueError as exc:
            raise ValueError(
                "Invalid date. Use YYYY-MM-DD (e.g. 2026-09-21)."
            ) from exc
    elif len(fields) == 8:
        theater = fields[3]
        try:
            target_date = date.fromisoformat(fields[4])
            start_clock = time.fromisoformat(fields[5])
            end_clock = time.fromisoformat(fields[6])
            poll_interval = int(fields[7])
        except ValueError as exc:
            raise ValueError(
                "Invalid date, time, or poll interval.\n"
                "Use:\n"
                "Date: YYYY-MM-DD\n"
                "Time: HH:MM\n"
                "Poll interval: seconds"
            ) from exc

    parsed_start = datetime.combine(target_date, start_clock, tzinfo=timezone.utc)
    parsed_end = datetime.combine(target_date, end_clock, tzinfo=timezone.utc)

    return TrackingJobCreate(
        target_name=target_name,
        platform=platform,
        city=city,
        theater=theater,
        target_date=target_date,
        start_at=parsed_start,
        end_at=parsed_end,
        poll_interval_seconds=poll_interval,
    )


async def handle_track(
    chat_id: int,
    db: Session,
    user: User,
    argument: str,
):
    if not argument.strip():
        await send_message(chat_id, TRACK_USAGE)
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
            f"✅ Job #{job.id} created (PENDING).\n"
            f"Start it with /resume {job.id}",
        )
        return
    except Exception:
        await send_message(
            chat_id,
            "❌ Couldn't create that job. Check the target/platform and try again.",
        )
        return

    await send_message(
        chat_id,
        f"✅ Watching #{job.id}\n\n"
        f"Target: {job.target_name}\n"
        f"Platform: {job.platform}\n"
        f"City: {job.city}\n"
        f"Theater: {job.theater}\n"
        f"Date: {job.target_date}\n"
        f"Window: {job.start_at.strftime('%H:%M')}–"
        f"{job.end_at.strftime('%H:%M')}\n"
        f"Poll: every {job.poll_interval_seconds}s\n"
        f"Status: {job.status}\n\n"
        f"Manage: /pause {job.id} · /jobs · /stop {job.id}",
    )


async def handle_start(chat_id: int):
    await send_message(
        chat_id,
        "Welcome to PulseGrid 👋\n\n"
        "I watch BookMyShow & District showtimes and ping you "
        "when matching shows appear.\n\n"
        "Quick start:\n"
        "/track ET00514261 bookmyshow Hyderabad\n"
        "/track MV181196 district Hyderabad\n\n"
        "See all commands: /help",
    )


async def handle_help(chat_id: int):
    await send_message(
        chat_id,
        "PulseGrid help\n\n"
        "Create\n"
        "/track <target> <platform> <city>\n"
        "  e.g. /track ET00514261 bookmyshow Hyderabad\n"
        "  e.g. /track MV181196 district Hyderabad\n\n"
        "Browse\n"
        "/jobs — list your jobs\n"
        "/job <id> — job details\n"
        "/status — counts by status\n\n"
        "Control\n"
        "/pause <id>  /resume <id>\n"
        "/stop <id>   /delete <id>\n\n"
        "Platforms: bookmyshow · district\n"
        "Theater tip: use Any for all venues\n"
        "Optional: add theater and date after city",
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
            "No jobs yet.\n\n"
            "Create one:\n"
            "/track ET00514261 bookmyshow Hyderabad",
        )
        return

    lines = ["Your jobs\n"]

    for job in jobs:
        lines.append(
            f"#{job.id} · {job.status}\n"
            f"{job.target_name} · {job.platform}\n"
            f"{job.city} / {job.theater} · {job.target_date}\n"
            f"/job {job.id} · /pause {job.id} · /stop {job.id}\n"
        )

    await send_message(
        chat_id,
        "\n".join(lines).strip(),
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
        f"Status: {job.status}\n\n"
        f"/pause {job.id}  /resume {job.id}\n"
        f"/stop {job.id}   /delete {job.id}",
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
            "Try /help or:\n"
            "/track ET00514261 bookmyshow Hyderabad",
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

    # Telegram may send /start@BotName
    command = parts[0].lower().split("@", 1)[0]
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
        "PulseGrid status\n\n"
        f"Total: {len(jobs)}\n"
        f"Pending: {counts['PENDING']}\n"
        f"Running: {counts['RUNNING']}\n"
        f"Paused: {counts['PAUSED']}\n"
        f"Completed: {counts['COMPLETED']}\n"
        f"Stopped: {counts['STOPPED']}",
    )
