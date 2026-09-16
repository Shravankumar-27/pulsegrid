from types import SimpleNamespace

from app.auth import can_manage_job, can_view_job


def test_admin_can_view_any_job():
    admin = SimpleNamespace(
        id=1,
        role="ADMIN",
    )

    job = SimpleNamespace(
        user_id=2,
    )

    assert can_view_job(admin, job) is True


def test_user_can_view_own_job():
    user = SimpleNamespace(
        id=2,
        role="USER",
    )

    job = SimpleNamespace(
        user_id=2,
    )

    assert can_view_job(user, job) is True


def test_user_cannot_view_other_users_job():
    user = SimpleNamespace(
        id=2,
        role="USER",
    )

    job = SimpleNamespace(
        user_id=3,
    )

    assert can_view_job(user, job) is False


def test_admin_can_manage_any_job():
    admin = SimpleNamespace(
        id=1,
        role="ADMIN",
    )

    job = SimpleNamespace(
        user_id=2,
    )

    assert can_manage_job(admin, job) is True


def test_user_can_manage_own_job():
    user = SimpleNamespace(
        id=2,
        role="USER",
    )

    job = SimpleNamespace(
        user_id=2,
    )

    assert can_manage_job(user, job) is True


def test_user_cannot_manage_other_users_job():
    user = SimpleNamespace(
        id=2,
        role="USER",
    )

    job = SimpleNamespace(
        user_id=3,
    )

    assert can_manage_job(user, job) is False