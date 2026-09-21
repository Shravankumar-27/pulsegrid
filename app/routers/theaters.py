from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.theater import TheaterCreate, TheaterResponse, TheaterUpdate
from app.services import theater_service

router = APIRouter(
    prefix="/api/v1/theaters",
    tags=["theaters"],
)


@router.get("", response_model=list[TheaterResponse])
def list_theaters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return theater_service.list_theaters_for_user(db, current_user)


@router.post("", response_model=TheaterResponse)
def create_theater(
    data: TheaterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return theater_service.create_theater(db, current_user, data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{theater_id}", response_model=TheaterResponse)
def update_theater(
    theater_id: int,
    data: TheaterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        theater = theater_service.get_theater_for_user(
            db, theater_id, current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return theater_service.update_theater(db, theater, data)


@router.delete("/{theater_id}")
def delete_theater(
    theater_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        theater = theater_service.get_theater_for_user(
            db, theater_id, current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    theater_service.delete_theater(db, theater)
    return {"message": "Theater deleted", "id": theater_id}
