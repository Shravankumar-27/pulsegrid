from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.user import User
from app.models.tracking_job import TrackingJob


TELEGRAM_USER_ID = 777799369
NAME = "starkkyyy"


db = SessionLocal()

try:
    existing_user = (
        db.query(User)
        .filter(User.telegram_user_id == TELEGRAM_USER_ID)
        .first()
    )

    if existing_user:
        print("User already exists:", existing_user.id)
    else:
        user = User(
            telegram_user_id=TELEGRAM_USER_ID,
            name=NAME,
            role="ADMIN",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print("Admin created:", user.id)

finally:
    db.close()