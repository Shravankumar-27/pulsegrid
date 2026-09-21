from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.models.theater import Theater
from app.models.tracking_job import TrackingJob


def _seed_user(db_session):
    user = User(
        telegram_user_id=777799369,
        name="Tester",
        role="USER",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_theater(client, db_session, auth_headers):
    user = _seed_user(db_session)

    response = client.post(
        "/api/v1/theaters",
        headers=auth_headers(user.id),
        json={
            "name": "AMB Cinemas",
            "city": "Hyderabad",
            "bookmyshow_venue_id": "BV123",
            "district_venue_id": "DV456",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "AMB Cinemas"
    assert body["bookmyshow_venue_id"] == "BV123"

    listed = client.get("/api/v1/theaters", headers=auth_headers(user.id))
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_watch_creates_both_platforms_and_saves_theater(
    client, db_session, auth_headers
):
    user = _seed_user(db_session)
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)

    response = client.post(
        "/api/v1/jobs/watch",
        headers=auth_headers(user.id),
        json={
            "movie_name": "Coolie",
            "city": "Hyderabad",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "platforms": ["bookmyshow", "district"],
            "bookmyshow_target": "ET00514261",
            "district_target": "MV181196",
            "theater_name": "AMB Cinemas",
            "bookmyshow_venue_id": "BV123",
            "district_venue_id": "DV456",
            "poll_interval_seconds": 60,
            "start_immediately": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["jobs"]) == 2
    assert body["theater"]["name"] == "AMB Cinemas"
    assert {job["platform"] for job in body["jobs"]} == {
        "bookmyshow",
        "district",
    }
    assert all(job["status"] == "RUNNING" for job in body["jobs"])
    assert all(job["movie_name"] == "Coolie" for job in body["jobs"])

    theaters = db_session.query(Theater).all()
    assert len(theaters) == 1
    assert theaters[0].bookmyshow_venue_id == "BV123"

    # Reuse by name next time — still one theater row
    response2 = client.post(
        "/api/v1/jobs/watch",
        headers=auth_headers(user.id),
        json={
            "movie_name": "Coolie",
            "city": "Hyderabad",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "platforms": ["bookmyshow"],
            "bookmyshow_target": "ET00514261",
            "theater_name": "AMB Cinemas",
            "start_immediately": True,
        },
    )
    assert response2.status_code == 200
    assert db_session.query(Theater).count() == 1
    assert db_session.query(TrackingJob).count() == 3


def test_watch_requires_platform_target(client, db_session, auth_headers):
    user = _seed_user(db_session)
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=6)

    response = client.post(
        "/api/v1/jobs/watch",
        headers=auth_headers(user.id),
        json={
            "movie_name": "Coolie",
            "city": "Hyderabad",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "platforms": ["bookmyshow"],
            "start_immediately": True,
        },
    )

    assert response.status_code == 422
