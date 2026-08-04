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


def test_root_path_returns_welcome_payload() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_page_renders_browser_form() -> None:
    response = client.get("/upload-page")
    assert response.status_code == 200
    assert "multipart/form-data" in response.text
    assert "/upload" in response.text
