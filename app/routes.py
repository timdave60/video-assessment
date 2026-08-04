import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import settings
from app.matcher import VideoMatcher
from app.models import AssessmentRecord, DeleteResponse, MatchCandidate, UploadMetadata, UploadedVideoResult
from app.storage import store
from app.video_utils import (
    SUPPORTED_RATIO_BUCKETS,
    VideoProcessingError,
    ensure_upload_dir,
    get_ratio_bucket,
    get_reduced_aspect_ratio,
    get_video_metadata,
    validate_upload_size,
    validate_video_filename,
)

router = APIRouter(tags=["assessment"])
matcher = VideoMatcher(upload_dir=settings.upload_dir)


@router.get("/")
async def root() -> dict:
    return {"status": "ok"}


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@router.post("/upload", response_model=List[UploadedVideoResult])
async def upload_videos(files: List[UploadFile] = File(...)) -> List[UploadedVideoResult]:
    """Upload MP4 files, analyze their dimensions, and store metadata in memory."""
    upload_dir = ensure_upload_dir(Path(settings.upload_dir))
    results: List[UploadedVideoResult] = []

    for upload_file in files:
        if upload_file.filename is None:
            continue

        try:
            validate_video_filename(upload_file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        video_id = str(uuid.uuid4())
        target_path = upload_dir / f"{video_id}_{Path(upload_file.filename).name}"

        try:
            contents = await upload_file.read()
            validate_upload_size(len(contents))
            target_path.write_bytes(contents)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {exc}") from exc

        try:
            metadata = get_video_metadata(target_path)
        except (VideoProcessingError, ValueError) as exc:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            width = int(metadata["width"])
            height = int(metadata["height"])
            aspect_ratio = get_reduced_aspect_ratio(width, height)
            ratio_bucket = get_ratio_bucket(width, height)
        except (KeyError, TypeError, ValueError) as exc:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Unable to determine video dimensions") from exc

        try:
            fingerprint_path = upload_dir / f"{video_id}.fingerprint"
            fingerprint_path.write_text(f"{video_id}\n{upload_file.filename}\n", encoding="utf-8")
        except OSError as exc:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Failed to write fingerprint metadata: {exc}") from exc

        try:
            record = AssessmentRecord(
                id=video_id,
                video_id=video_id,
                filename=upload_file.filename,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                ratio_bucket=ratio_bucket,
                metadata=UploadMetadata(
                    filename=upload_file.filename,
                    content_type=upload_file.content_type,
                    size_bytes=len(contents),
                ),
            )
            store.add(record)
            matcher.register_video(video_id, target_path)
        except (ValueError, OSError) as exc:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            if (upload_dir / f"{video_id}.fingerprint").exists():
                (upload_dir / f"{video_id}.fingerprint").unlink(missing_ok=True)
            store.delete(video_id)
            raise HTTPException(status_code=500, detail=f"Failed to persist video metadata: {exc}") from exc

        results.append(
            UploadedVideoResult(
                video_id=video_id,
                filename=upload_file.filename,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                ratio_bucket=ratio_bucket,
            )
        )

    return results


@router.get("/videos", response_model=List[UploadedVideoResult])
async def list_videos(ratio: Optional[str] = Query(default=None)) -> List[UploadedVideoResult]:
    """Return all uploaded videos, optionally filtered by a canonical ratio bucket."""
    if ratio is not None and ratio not in SUPPORTED_RATIO_BUCKETS:
        raise HTTPException(status_code=400, detail="Invalid ratio filter")

    records = store.list()
    videos = []
    for record in records:
        if ratio is not None and record.ratio_bucket != ratio:
            continue

        videos.append(
            UploadedVideoResult(
                video_id=record.video_id or record.id,
                filename=record.filename or "",
                width=record.width or 0,
                height=record.height or 0,
                aspect_ratio=record.aspect_ratio or "",
                ratio_bucket=record.ratio_bucket or "",
            )
        )

    return videos


@router.delete("/videos/{video_id}", response_model=DeleteResponse)
async def delete_video(video_id: str) -> DeleteResponse:
    """Delete a stored video, its saved file, and its fingerprint artifact."""
    upload_dir = ensure_upload_dir(Path(settings.upload_dir))
    deleted_record = store.delete(video_id, upload_dir=upload_dir)
    if deleted_record is None:
        raise HTTPException(status_code=404, detail="Video not found")

    matcher.remove_video(video_id)
    return DeleteResponse(deleted=video_id)


@router.get("/match", response_model=List[MatchCandidate])
async def match_video(video_id: str) -> List[MatchCandidate]:
    """Return ranked visual matches for a stored video."""
    if store.get(video_id) is None:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        reference = matcher._get_or_build_fingerprint(video_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build video fingerprint: {exc}") from exc

    if reference is None:
        return []

    matches: List[MatchCandidate] = []
    for record in store.list():
        candidate_id = record.video_id or record.id
        if candidate_id == video_id:
            continue
        if record.ratio_bucket in {None, "Other"}:
            continue
        if record.ratio_bucket == reference["ratio_bucket"]:
            continue

        try:
            candidate = matcher._get_or_build_fingerprint(candidate_id)
        except (ValueError, OSError) as exc:
            continue
        if candidate is None:
            continue

        confidence = matcher.compare_fingerprints(reference["fingerprint"], candidate["fingerprint"])
        if confidence <= 0:
            continue

        matches.append(
            MatchCandidate(
                video_id=candidate_id,
                filename=record.filename or "",
                confidence=round(float(confidence), 6),
            )
        )

    matches.sort(key=lambda item: item.confidence, reverse=True)
    return matches
