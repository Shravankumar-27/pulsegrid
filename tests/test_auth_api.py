from datetime import datetime, timezone

from app.models.user import User


def create_user(
    db_session,
    user_id: int,
    telegram_user_id: int,
    status: str = "ACTIVE",
):
    user = User(
        id=user_id,
        telegram_user_id=telegram_user_id,
        name=f"Test User {user_id}",
        role="USER",
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_login_returns_access_token(client, db_session):
    create_user(
        db_session,
        user_id=2,
        telegram_user_id=123456789,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "telegram_user_id": 123456789,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_rejects_unknown_user(client, db_session):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "telegram_user_id": 999999999,
        },
    )

    assert response.status_code == 401


def test_login_rejects_inactive_user(client, db_session):
    create_user(
        db_session,
        user_id=2,
        telegram_user_id=123456789,
        status="INACTIVE",
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "telegram_user_id": 123456789,
        },
    )

    assert response.status_code == 403


def test_login_rejects_missing_telegram_user_id(client):
    response = client.post(
        "/api/v1/auth/login",
        json={},
    )

    assert response.status_code == 422