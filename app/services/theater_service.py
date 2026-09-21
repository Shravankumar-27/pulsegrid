from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.theater import Theater
from app.models.user import User
from app.schemas.theater import TheaterCreate, TheaterUpdate


def list_theaters_for_user(db: Session, user: User) -> list[Theater]:
    statement = select(Theater).order_by(Theater.name, Theater.city)
    if user.role != "ADMIN":
        statement = statement.where(Theater.user_id == user.id)
    return list(db.scalars(statement).all())


def get_theater_for_user(db: Session, theater_id: int, user: User) -> Theater:
    theater = db.get(Theater, theater_id)
    if theater is None:
        raise ValueError("Theater not found")
    if user.role != "ADMIN" and theater.user_id != user.id:
        raise PermissionError("You do not have access to this theater")
    return theater


def create_theater(
    db: Session,
    user: User,
    data: TheaterCreate,
) -> Theater:
    theater = Theater(
        user_id=user.id,
        name=data.name,
        city=data.city,
        bookmyshow_venue_id=data.bookmyshow_venue_id,
        district_venue_id=data.district_venue_id,
    )
    db.add(theater)
    db.commit()
    db.refresh(theater)
    return theater


def update_theater(
    db: Session,
    theater: Theater,
    data: TheaterUpdate,
) -> Theater:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(theater, field, value)
    db.commit()
    db.refresh(theater)
    return theater


def delete_theater(db: Session, theater: Theater) -> None:
    db.delete(theater)
    db.commit()


def upsert_theater_by_name(
    db: Session,
    user: User,
    *,
    name: str,
    city: str,
    bookmyshow_venue_id: str | None = None,
    district_venue_id: str | None = None,
) -> Theater:
    """Find theater by name+city for this user, or create it.

    Existing venue ids are filled in when new values are provided.
    """
    statement = (
        select(Theater)
        .where(Theater.user_id == user.id)
        .where(Theater.name == name)
        .where(Theater.city == city)
    )
    theater = db.scalars(statement).first()

    if theater is None:
        theater = Theater(
            user_id=user.id,
            name=name,
            city=city,
            bookmyshow_venue_id=bookmyshow_venue_id,
            district_venue_id=district_venue_id,
        )
        db.add(theater)
        db.commit()
        db.refresh(theater)
        return theater

    changed = False
    if bookmyshow_venue_id and not theater.bookmyshow_venue_id:
        theater.bookmyshow_venue_id = bookmyshow_venue_id
        changed = True
    if district_venue_id and not theater.district_venue_id:
        theater.district_venue_id = district_venue_id
        changed = True
    if bookmyshow_venue_id and theater.bookmyshow_venue_id != bookmyshow_venue_id:
        theater.bookmyshow_venue_id = bookmyshow_venue_id
        changed = True
    if district_venue_id and theater.district_venue_id != district_venue_id:
        theater.district_venue_id = district_venue_id
        changed = True

    if changed:
        db.commit()
        db.refresh(theater)

    return theater
