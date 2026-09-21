from types import SimpleNamespace

from app.services.providers.matcher import matches_job, matching_sessions


def make_job(theater):
    return SimpleNamespace(theater=theater)


def test_matches_theater():
    job = make_job("PVR")

    session = {
        "cinema": "PVR: Nexus Mall",
    }

    assert matches_job(job, session) is True


def test_rejects_different_theater():
    job = make_job("PVR")

    session = {
        "cinema": "INOX: GVK One",
    }

    assert matches_job(job, session) is False


def test_matching_sessions():
    job = make_job("PVR")

    sessions = [
        {"cinema": "PVR: Nexus Mall", "id": "1"},
        {"cinema": "INOX: GVK One", "id": "2"},
    ]

    result = matching_sessions(job, sessions)

    assert len(result) == 1
    assert result[0]["id"] == "1"