from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional

from app.models import AssessmentRecord


class InMemoryStore:
    """Simple in-memory persistence layer for the assessment workflow."""

    def __init__(self) -> None:
        self._records: Dict[str, AssessmentRecord] = OrderedDict()
        self._lock = RLock()

    def add(self, record: AssessmentRecord) -> AssessmentRecord:
        with self._lock:
            self._records[record.id] = record
            return record

    def get(self, record_id: str) -> Optional[AssessmentRecord]:
        with self._lock:
            return self._records.get(record_id)

    def list(self) -> List[AssessmentRecord]:
        with self._lock:
            return list(self._records.values())

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def delete(self, record_id: str, upload_dir: Optional[Path] = None) -> Optional[AssessmentRecord]:
        with self._lock:
            record = self._records.pop(record_id, None)
            if record is None:
                return None

            if upload_dir is not None:
                uploaded_file = upload_dir / f"{record.id}_{Path(record.filename).name}" if record.filename else None
                if uploaded_file and uploaded_file.exists():
                    uploaded_file.unlink()

                fingerprint_file = upload_dir / f"{record.id}.fingerprint"
                if fingerprint_file.exists():
                    fingerprint_file.unlink()

            return record


store = InMemoryStore()
