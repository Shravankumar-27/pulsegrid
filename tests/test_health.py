from pathlib import Path

from fastapi.testclient import TestClient

from app.main import FRONTEND_DIST, app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    if FRONTEND_DIST.is_dir():
        assert "text/html" in response.headers["content-type"]
        assert "PulseGrid" in response.text
    else:
        assert response.json()["message"] == "PulseGrid API"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }
