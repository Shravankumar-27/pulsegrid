from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.auth import get_current_user, can_manage_job, can_view_job
from app.models.user import User
from app.database import get_db
from app.models.tracking_job import TrackingJob
from app.schemas.tracking_job import (
    TrackingJobCreate,
    TrackingJobResponse,
    TrackingJobUpdate,
)
from app.schemas.watch_job import WatchJobCreate, WatchJobResponse

from app.services.job_service import (
    InvalidJobTransition,
    change_job_status,
    create_tracking_job,
    create_watch_jobs,
)

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["jobs"],
)


@router.post("", response_model=TrackingJobResponse)
def create_job(
    job: TrackingJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_tracking_job(
        db=db,
        user=current_user,
        job_data=job,
    )


@router.post("/watch", response_model=WatchJobResponse)
def create_watch_job(
    payload: WatchJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create one or more monitoring jobs from the dashboard form."""
    try:
        return create_watch_jobs(
            db=db,
            user=current_user,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[TrackingJobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    if current_user.role == "ADMIN":
        statement = select(TrackingJob).order_by(TrackingJob.id)
    else:
        statement = ( select(TrackingJob)
                    .where(TrackingJob.user_id == current_user.id)
                    .order_by(TrackingJob.id)
        )

    jobs = db.scalars(statement).all()

    return jobs

@router.get("/{job_id}", response_model=TrackingJobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )
    
    if not can_view_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this job",
        )
    
    return job

@router.patch("/{job_id}", response_model=TrackingJobResponse)
def update_job(
    job_id: int,
    job_data: TrackingJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )
    
    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this job",
        )
    
    update_data = job_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return job

@router.post("/{job_id}/start", response_model=TrackingJobResponse)
def start_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this job",
        )

    try:
        change_job_status(db, job, "RUNNING")
    except InvalidJobTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return job


@router.post("/{job_id}/pause", response_model=TrackingJobResponse)
def pause_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this job",
        )

    try:
        change_job_status(db, job, "PAUSED")
    except InvalidJobTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return job


@router.post("/{job_id}/resume", response_model=TrackingJobResponse)
def resume_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this job",
        )

    try:
        change_job_status(db, job, "RUNNING")
    except InvalidJobTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return job


@router.post("/{job_id}/stop", response_model=TrackingJobResponse)
def stop_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this job",
        )

    try:
        change_job_status(db, job, "STOPPED")
    except InvalidJobTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return job

@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if not can_manage_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this job",
        )
    
    db.delete(job)
    db.commit()

    return {
        "message": "Job deleted successfully",
        "id": job_id,
    }


@router.get("/{job_id}/results")
def get_job_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.time import format_ist

    job = db.get(TrackingJob, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_view_job(current_user, job):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this job",
        )

    return {
        "job_id": job.id,
        "movie_name": job.movie_name or job.target_name,
        "platform": job.platform,
        "city": job.city,
        "theater": job.theater,
        "status": job.status,
        "last_checked_at": job.last_checked_at.isoformat() if job.last_checked_at else None,
        "last_checked_at_ist": format_ist(job.last_checked_at),
        "result": job.last_result_json or {
            "available": False,
            "message": "No polls completed yet.",
            "sessions": [],
            "sessions_count": 0,
        },
    }