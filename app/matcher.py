from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

import cv2
import imagehash
import numpy as np
from PIL import Image


class VideoMatcher:
    """Create visual fingerprints for videos and compare them robustly."""

    def __init__(self, upload_dir: Optional[str | Path] = None) -> None:
        base_dir = Path(upload_dir) if upload_dir is not None else Path(__file__).resolve().parent.parent / "uploads"
        self._upload_dir = base_dir.resolve()
        self._fingerprints: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    async def compare(self, reference_video_id: str, candidate_video_id: str) -> Dict[str, Any]:
        reference = self._get_or_build_fingerprint(reference_video_id)
        candidate = self._get_or_build_fingerprint(candidate_video_id)

        if reference is None or candidate is None:
            return {
                "matched": False,
                "confidence": 0.0,
                "reference_video_id": reference_video_id,
                "candidate_video_id": candidate_video_id,
            }

        if reference["ratio_bucket"] == "Other" or candidate["ratio_bucket"] == "Other":
            return {
                "matched": False,
                "confidence": 0.0,
                "reference_video_id": reference_video_id,
                "candidate_video_id": candidate_video_id,
            }

        if reference["ratio_bucket"] == candidate["ratio_bucket"]:
            return {
                "matched": False,
                "confidence": 0.0,
                "reference_video_id": reference_video_id,
                "candidate_video_id": candidate_video_id,
            }

        confidence = self._normalized_hamming_similarity(reference["fingerprint"], candidate["fingerprint"])
        matched = confidence >= 0.75

        return {
            "matched": matched,
            "confidence": round(float(confidence), 6),
            "reference_video_id": reference_video_id,
            "candidate_video_id": candidate_video_id,
        }

    def register_video(self, video_id: str, video_path: str | Path) -> Dict[str, Any]:
        fingerprint = self._build_fingerprint(video_path)
        record = {
            "video_id": video_id,
            "video_path": str(video_path),
            **fingerprint,
        }
        with self._lock:
            self._fingerprints[video_id] = record
        return record

    def remove_video(self, video_id: str) -> None:
        with self._lock:
            self._fingerprints.pop(video_id, None)

    def get_fingerprint(self, video_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._fingerprints.get(video_id)

    def compare_fingerprints(self, left: str, right: str) -> float:
        return self._normalized_hamming_similarity(left, right)

    def _get_or_build_fingerprint(self, video_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if video_id in self._fingerprints:
                return self._fingerprints[video_id]

        video_path = self._resolve_video_path(video_id)
        if video_path is None:
            return None

        return self.register_video(video_id, video_path)

    def _resolve_video_path(self, video_id: str) -> Optional[Path]:
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        matches = sorted(self._upload_dir.glob(f"{video_id}_*"))
        if matches:
            return matches[0]
        return None

    def _build_fingerprint(self, video_path: str | Path) -> Dict[str, Any]:
        video_path = Path(video_path)
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError(f"Unable to open video: {video_path}")

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ratio_bucket = self._get_ratio_bucket(width, height)

        sample_count = 12
        hashes: list[str] = []

        if frame_count <= 0:
            capture.release()
            return {"fingerprint": "0" * 64, "ratio_bucket": ratio_bucket}

        for index in range(sample_count):
            frame_index = self._sample_frame_index(frame_count, sample_count, index)
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = capture.read()
            if not success or frame is None:
                continue

            hash_bits = self._frame_to_hash(frame)
            hashes.append(hash_bits)

        capture.release()

        if not hashes:
            return {"fingerprint": "0" * 64, "ratio_bucket": ratio_bucket}

        aggregated_bits = self._aggregate_hashes(hashes)
        return {"fingerprint": aggregated_bits, "ratio_bucket": ratio_bucket}

    def _sample_frame_index(self, frame_count: int, sample_count: int, sample_index: int) -> int:
        if frame_count <= 1:
            return 0
        if sample_count <= 1:
            return 0
        return min(frame_count - 1, max(0, int(round(sample_index * (frame_count - 1) / (sample_count - 1)))))

    def _frame_to_hash(self, frame: np.ndarray) -> str:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cropped = self._crop_black_borders(gray)
        resized = cv2.resize(cropped, (32, 32), interpolation=cv2.INTER_AREA)
        image = Image.fromarray(resized)
        perceptual_hash = imagehash.phash(image, hash_size=8)
        bits = perceptual_hash.hash.flatten().astype(int).tolist()
        return "".join(str(int(bit)) for bit in bits)

    def _crop_black_borders(self, gray_frame: np.ndarray) -> np.ndarray:
        _, mask = cv2.threshold(gray_frame, 20, 255, cv2.THRESH_BINARY)
        points = cv2.findNonZero(mask)
        if points is None:
            return gray_frame

        x, y, width, height = cv2.boundingRect(points)
        if width <= 0 or height <= 0:
            return gray_frame

        return gray_frame[y : y + height, x : x + width]

    def _aggregate_hashes(self, hashes: list[str]) -> str:
        if not hashes:
            return "0" * 64

        bit_count = len(hashes[0])
        aggregate = []
        for bit_index in range(bit_count):
            ones = sum(int(frame_hash[bit_index]) for frame_hash in hashes)
            aggregate.append("1" if ones > len(hashes) / 2 else "0")
        return "".join(aggregate)

    def _normalized_hamming_similarity(self, left: str, right: str) -> float:
        if len(left) != len(right):
            return 0.0
        if not left:
            return 0.0

        distance = sum(1 for a, b in zip(left, right) if a != b)
        return max(0.0, 1.0 - (distance / len(left)))

    def _get_ratio_bucket(self, width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            return "Other"

        ratio = width / height
        tolerance = 0.01
        supported = {
            "9:16": 9 / 16,
            "1:1": 1.0,
            "4:5": 4 / 5,
            "16:9": 16 / 9,
        }

        for bucket, expected_ratio in supported.items():
            if abs(ratio - expected_ratio) <= tolerance * expected_ratio:
                return bucket

        return "Other"
