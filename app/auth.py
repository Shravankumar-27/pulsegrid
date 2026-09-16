import jwt

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.database import get_db 
from app.models.tracking_job import TrackingJob
from app.models.user import User
from app.security import decode_access_token


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="User is not active",
        )

    return user

def can_manage_job(user: User, job: TrackingJob) -> bool:
    return user.role == "ADMIN" or user.id == job.user_id

def can_view_job(user: User, job: TrackingJob) -> bool:
    return user.role == "ADMIN" or user.id == job.user_id