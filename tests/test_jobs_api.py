from datetime import datetime, timezone

from app.models.tracking_job import TrackingJob
from app.models.user import User


def create_user(
    db_session,
    user_id: int,
    role: str = "USER",
    status: str = "ACTIVE",
):
    user = User(
        id=user_id,
        telegram_user_id=1000000000 + user_id,
        name=f"Test User {user_id}",
        role=role,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(user)
    db_session.commit()

    return user


def create_job(
    db_session,
    user_id: int,
    target_name: str,
):
    job = TrackingJob(
        user_id=user_id,
        target_name=target_name,
        platform="platform_a",
        city="Hyderabad",
        theater="Test Theater",
        target_date=datetime(2026, 9, 16).date(),
        start_at=datetime(
            2026, 9, 16, 17, 0, tzinfo=timezone.utc
        ),
        end_at=datetime(
            2026, 9, 16, 19, 0, tzinfo=timezone.utc
        ),
        poll_interval_seconds=60,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return job


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------

def test_create_job_belongs_to_current_user(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    response = client.post(
        "/api/v1/jobs",
        headers=auth_headers(2),
        json={
            "target_name": "Test Target",
            "platform": "platform_a",
            "city": "Hyderabad",
            "theater": "Test Theater",
            "target_date": "2026-09-16",
            "start_at": "2026-09-16T17:00:00Z",
            "end_at": "2026-09-16T19:00:00Z",
            "poll_interval_seconds": 60,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["user_id"] == 2
    assert data["target_name"] == "Test Target"
    assert data["status"] == "PENDING"


def test_create_job_requires_authentication(client):
    response = client.post(
        "/api/v1/jobs",
        json={
            "target_name": "Test Target",
            "platform": "platform_a",
            "city": "Hyderabad",
            "theater": "Test Theater",
            "target_date": "2026-09-16",
            "start_at": "2026-09-16T17:00:00Z",
            "end_at": "2026-09-16T19:00:00Z",
            "poll_interval_seconds": 60,
        },
    )

    assert response.status_code == 401


def test_create_job_rejects_invalid_time(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    response = client.post(
        "/api/v1/jobs",
        headers=auth_headers(2),
        json={
            "target_name": "Invalid Job",
            "platform": "platform_a",
            "city": "Hyderabad",
            "theater": "Test Theater",
            "target_date": "2026-09-16",
            "start_at": "2026-09-16T19:00:00Z",
            "end_at": "2026-09-16T17:00:00Z",
            "poll_interval_seconds": 60,
        },
    )

    assert response.status_code == 422


def test_create_job_rejects_poll_interval_below_minimum(
    client,
    db_session,
    auth_headers
):
    create_user(db_session, user_id=2)

    response = client.post(
        "/api/v1/jobs",
        headers=auth_headers(2),
        json={
            "target_name": "Invalid Poll Job",
            "platform": "platform_a",
            "city": "Hyderabad",
            "theater": "Test Theater",
            "target_date": "2026-09-16",
            "start_at": "2026-09-16T17:00:00Z",
            "end_at": "2026-09-16T19:00:00Z",
            "poll_interval_seconds": 5,
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# GET LIST
# ---------------------------------------------------------

def test_user_sees_only_own_jobs(client, db_session, auth_headers):
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    user_two_job = create_job(
        db_session,
        user_id=2,
        target_name="User 2 Job",
    )

    create_job(
        db_session,
        user_id=3,
        target_name="User 3 Job",
    )

    response = client.get(
        "/api/v1/jobs",
        headers=auth_headers(2),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == user_two_job.id
    assert data[0]["user_id"] == 2


def test_admin_sees_all_jobs(client, db_session, auth_headers):
    create_user(db_session, user_id=1, role="ADMIN")
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    create_job(db_session, user_id=2, target_name="User 2 Job")
    create_job(db_session, user_id=3, target_name="User 3 Job")

    response = client.get(
        "/api/v1/jobs",
        headers=auth_headers(1),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert len(data) == 2
    assert {job["user_id"] for job in data} == {2, 3}


def test_get_jobs_requires_authentication(client):
    response = client.get("/api/v1/jobs")

    assert response.status_code == 401


# ---------------------------------------------------------
# GET SINGLE JOB
# ---------------------------------------------------------

def test_user_can_view_own_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="My Job",
    )

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job.id
    assert data["user_id"] == 2


def test_user_cannot_view_another_users_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    job = create_job(
        db_session,
        user_id=3,
        target_name="User 3 Job",
    )

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
    )

    assert response.status_code == 403


def test_admin_can_view_another_users_job(client, db_session, auth_headers):
    create_user(db_session, user_id=1, role="ADMIN")
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="User 2 Job",
    )

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(1),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job.id
    assert data["user_id"] == 2


def test_get_nonexistent_job_returns_404(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    response = client.get(
        "/api/v1/jobs/99999",
        headers=auth_headers(2),
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------

def test_user_can_update_own_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Original Name",
    )

    response = client.patch(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
        json={
            "target_name": "Updated Name",
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["target_name"] == "Updated Name"
    assert data["user_id"] == 2


def test_user_cannot_update_another_users_job(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    job = create_job(
        db_session,
        user_id=3,
        target_name="User 3 Job",
    )

    response = client.patch(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
        json={
            "target_name": "Hacked Name",
        },
    )

    assert response.status_code == 403


def test_admin_can_update_another_users_job(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=1, role="ADMIN")
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Original Name",
    )

    response = client.patch(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(1),
        json={
            "target_name": "Admin Updated Name",
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["target_name"] == "Admin Updated Name"
    assert data["user_id"] == 2


def test_update_nonexistent_job_returns_404(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=2)

    response = client.patch(
        "/api/v1/jobs/99999",
        headers=auth_headers(2),
        json={
            "target_name": "Updated",
        },
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# DELETE
# ---------------------------------------------------------

def test_user_can_delete_own_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Delete Me",
    )

    response = client.delete(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job.id


def test_user_cannot_delete_another_users_job(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    job = create_job(
        db_session,
        user_id=3,
        target_name="User 3 Job",
    )

    response = client.delete(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(2),
    )

    assert response.status_code == 403


def test_admin_can_delete_another_users_job(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=1, role="ADMIN")
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Delete Me",
    )

    response = client.delete(
        f"/api/v1/jobs/{job.id}",
        headers=auth_headers(1),
    )

    assert response.status_code == 200


def test_delete_nonexistent_job_returns_404(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=2)

    response = client.delete(
        "/api/v1/jobs/99999",
        headers=auth_headers(2),
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# USER STATUS
# ---------------------------------------------------------

def test_inactive_user_cannot_access_jobs(
    client,
    db_session,
    auth_headers,
):
    create_user(
        db_session,
        user_id=2,
        status="INACTIVE",
    )

    response = client.get(
        "/api/v1/jobs",
        headers=auth_headers(2),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": "User is not active"
    }

# ---------------------------------------------------------
# LIFECYCLE
# ---------------------------------------------------------


def test_start_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Start Me",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/start",
        headers=auth_headers(2),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RUNNING"


def test_pause_running_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Pause Me",
    )

    client.post(
        f"/api/v1/jobs/{job.id}/start",
        headers=auth_headers(2),
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/pause",
        headers=auth_headers(2),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PAUSED"


def test_resume_paused_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Resume Me",
    )

    client.post(
        f"/api/v1/jobs/{job.id}/start",
        headers=auth_headers(2),
    )

    client.post(
        f"/api/v1/jobs/{job.id}/pause",
        headers=auth_headers(2),
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/resume",
        headers=auth_headers(2),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RUNNING"


def test_stop_running_job(client, db_session, auth_headers):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Stop Me",
    )

    client.post(
        f"/api/v1/jobs/{job.id}/start",
        headers=auth_headers(2),
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/stop",
        headers=auth_headers(2),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "STOPPED"

def test_user_cannot_start_another_users_job(
    client,
    db_session,
    auth_headers,
):
    create_user(db_session, user_id=2)
    create_user(db_session, user_id=3)

    job = create_job(
        db_session,
        user_id=3,
        target_name="User 3 Job",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/start",
        headers=auth_headers(2),
    )

    assert response.status_code == 403

def test_start_job_requires_authentication(client, db_session):
    create_user(db_session, user_id=2)

    job = create_job(
        db_session,
        user_id=2,
        target_name="Auth Test",
    )

    response = client.post(
        f"/api/v1/jobs/{job.id}/start",
    )

    assert response.status_code == 401