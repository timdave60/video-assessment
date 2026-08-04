from typing import Optional

from pydantic import BaseModel, Field


class UploadMetadata(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class UploadedVideoResult(BaseModel):
    video_id: str
    filename: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str


class MatchRequest(BaseModel):
    reference_video_id: str = Field(..., min_length=1)
    candidate_video_id: str = Field(..., min_length=1)


class MatchResponse(BaseModel):
    message: str = "Matching logic will be implemented here."
    matched: bool = False
    score: Optional[float] = None


class DeleteResponse(BaseModel):
    deleted: str


class MatchCandidate(BaseModel):
    video_id: str
    filename: str
    confidence: float


class AssessmentRecord(BaseModel):
    id: str
    video_id: Optional[str] = None
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[str] = None
    ratio_bucket: Optional[str] = None
    reference_video_id: Optional[str] = None
    candidate_video_id: Optional[str] = None
    metadata: Optional[UploadMetadata] = None
    status: str = "queued"
