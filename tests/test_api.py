from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_requires_files() -> None:
    response = client.post("/upload")
    assert response.status_code == 422


def test_list_videos_empty_initially() -> None:
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_ratio_filter_returns_400() -> None:
    response = client.get("/videos?ratio=invalid")
    assert response.status_code == 400
