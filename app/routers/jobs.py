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
    new_job = TrackingJob(
        user_id=current_user.id,
        target_name=job.target_name,
        platform=job.platform,
        city=job.city,
        theater=job.theater,
        target_date=job.target_date,
        start_at=job.start_at,
        end_at=job.end_at,
        poll_interval_seconds=job.poll_interval_seconds,
        status="PENDING",
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job

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