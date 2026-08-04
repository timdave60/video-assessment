import math
from pathlib import Path
from typing import Optional

import cv2

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}


class VideoProcessingError(Exception):
    """Raised when video processing fails."""


SUPPORTED_RATIO_BUCKETS = {
    "9:16": 9 / 16,
    "1:1": 1.0,
    "4:5": 4 / 5,
    "16:9": 16 / 9,
}


def ensure_upload_dir(upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_video_metadata(video_path: Path) -> Optional[dict]:
    """Read basic video metadata using OpenCV when available."""
    if not video_path.exists() or not video_path.is_file():
        raise VideoProcessingError(f"Video file does not exist: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        raise VideoProcessingError(f"Unable to open video file: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if frame_count <= 0 or width <= 0 or height <= 0:
        raise VideoProcessingError(f"Video contains no readable frames: {video_path}")

    return {
        "frame_count": frame_count,
        "fps": fps,
        "width": width,
        "height": height,
    }


def validate_video_filename(filename: str) -> None:
    if not filename or not filename.strip():
        raise ValueError("Filename is required")

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported video format: {suffix or 'unknown'}")


def validate_upload_size(size_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValueError("Uploaded file is empty")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("Uploaded file exceeds the maximum supported size")


def get_reduced_aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive integers.")

    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def get_ratio_bucket(width: int, height: int, tolerance_percent: float = 1.0) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive integers.")

    ratio = width / height
    tolerance = tolerance_percent / 100.0

    for bucket, expected_ratio in SUPPORTED_RATIO_BUCKETS.items():
        if abs(ratio - expected_ratio) <= tolerance * expected_ratio:
            return bucket

    return "Other"
