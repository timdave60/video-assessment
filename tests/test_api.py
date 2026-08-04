from fastapi.testclient import TestClient

from app.main import app
from app.models import AssessmentRecord
from app.routes import matcher
from app.storage import store


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
    assert "Find Matches" in response.text


def test_match_returns_cross_bucket_matches_for_same_content_family() -> None:
    store.clear()
    matcher.remove_video("reference")
    matcher.remove_video("candidate")
    matcher._fingerprints.clear()

    matcher._fingerprints["reference"] = {
        "video_id": "reference",
        "video_path": "dummy-reference.mp4",
        "fingerprint": "0" * 64,
        "ratio_bucket": "9:16",
        "content_family": "shared creative",
        "filename": "shared_creative_AS_9-16.mp4",
    }
    matcher._fingerprints["candidate"] = {
        "video_id": "candidate",
        "video_path": "dummy-candidate.mp4",
        "fingerprint": "0" * 64,
        "ratio_bucket": "4:5",
        "content_family": "shared creative",
        "filename": "shared_creative_AS_4-5.mp4",
    }

    store.add(
        AssessmentRecord(
            id="reference",
            video_id="reference",
            filename="shared_creative_AS_9-16.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
        )
    )
    store.add(
        AssessmentRecord(
            id="candidate",
            video_id="candidate",
            filename="shared_creative_AS_4-5.mp4",
            width=1080,
            height=1350,
            aspect_ratio="4:5",
            ratio_bucket="4:5",
        )
    )

    response = client.get("/match?video_id=reference")
    assert response.status_code == 200
    assert response.json()[0]["video_id"] == "candidate"
    assert response.json()[0]["confidence"] >= 0.9
