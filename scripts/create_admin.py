"""
Create / ensure an admin user.

    TELEGRAM_ADMIN_USER_ID=123456789 TELEGRAM_ADMIN_NAME=you \\
      .\\.venv\\Scripts\\python.exe scripts/create_admin.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.user import User


def main() -> int:
    telegram_user_id = os.getenv("TELEGRAM_ADMIN_USER_ID", "").strip()
    name = os.getenv("TELEGRAM_ADMIN_NAME", "admin").strip() or "admin"

    if not telegram_user_id.isdigit():
        print("Set TELEGRAM_ADMIN_USER_ID to your numeric Telegram user id.")
        return 1

    telegram_user_id_int = int(telegram_user_id)
    db = SessionLocal()

    try:
        existing = (
            db.query(User)
            .filter(User.telegram_user_id == telegram_user_id_int)
            .first()
        )
        if existing:
            print(f"User already exists: id={existing.id} role={existing.role}")
            return 0

        user = User(
            telegram_user_id=telegram_user_id_int,
            name=name,
            role="ADMIN",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Admin created: id={user.id} telegram={telegram_user_id_int}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
