"""Job models and state definitions for AI B-Roll Autopilot."""

import enum
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


class JobState(str, enum.Enum):
    QUEUED = "QUEUED"
    INGESTING = "INGESTING"
    TRANSCRIBING = "TRANSCRIBING"
    DIRECTING = "DIRECTING"
    MATCHING = "MATCHING"
    PLANNING = "PLANNING"
    RENDERING = "RENDERING"
    REVIEWING = "REVIEWING"
    REPAIRING = "REPAIRING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Valid state transitions
VALID_TRANSITIONS = {
    JobState.QUEUED: [JobState.INGESTING, JobState.CANCELLED, JobState.FAILED],
    JobState.INGESTING: [JobState.TRANSCRIBING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.TRANSCRIBING: [JobState.DIRECTING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.DIRECTING: [JobState.MATCHING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.MATCHING: [JobState.PLANNING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.PLANNING: [JobState.RENDERING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.RENDERING: [JobState.REVIEWING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.REVIEWING: [JobState.UPLOADING, JobState.REPAIRING, JobState.COMPLETED, JobState.FAILED, JobState.INGESTING],
    JobState.REPAIRING: [JobState.RENDERING, JobState.FAILED, JobState.CANCELLED, JobState.INGESTING],
    JobState.UPLOADING: [JobState.COMPLETED, JobState.FAILED, JobState.INGESTING],
    JobState.COMPLETED: [JobState.QUEUED, JobState.INGESTING, JobState.DIRECTING, JobState.MATCHING, JobState.RENDERING],
    JobState.FAILED: [JobState.QUEUED, JobState.INGESTING, JobState.DIRECTING, JobState.MATCHING, JobState.RENDERING],  # Can retry
    JobState.CANCELLED: [JobState.QUEUED, JobState.INGESTING],  # Can retry
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_job_id(prefix: str = "job") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


@dataclass
class Job:
    """Core job entity representing a video editing workflow execution."""

    job_id: str
    source_file: str
    source_filename: str
    status: JobState = JobState.QUEUED
    progress: float = 0.0
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    error_message: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_segments: Optional[List[Dict[str, Any]]] = None
    edit_plan: Optional[Dict[str, Any]] = None
    review_data: Optional[Dict[str, Any]] = None
    output_video_path: Optional[str] = None
    drive_file_url: Optional[str] = None
    retry_count: int = 0
    repair_count: int = 0
    campaign_id: str = "default"

    @classmethod
    def create(cls, source_file_path: str, campaign_id: str = "default") -> "Job":
        path = Path(source_file_path)
        job_id = generate_job_id(prefix=path.stem[:12])

        return cls(
            job_id=job_id,
            source_file=str(path.resolve()),
            source_filename=path.name,
            status=JobState.QUEUED,
            progress=0.0,
            campaign_id=campaign_id or "default",
        )

    def can_transition_to(self, target_state: JobState) -> bool:
        return target_state in VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, target_state: JobState, error: Optional[str] = None, progress: Optional[float] = None):
        if not self.can_transition_to(target_state):
            # Allow force error
            if target_state not in (JobState.FAILED, JobState.CANCELLED):
                raise ValueError(f"Invalid state transition: {self.status.value} -> {target_state.value}")

        self.status = target_state
        self.updated_at = utc_now_iso()
        if error is not None:
            self.error_message = error
        elif target_state in (JobState.COMPLETED, JobState.INGESTING, JobState.QUEUED):
            self.error_message = None
        if progress is not None:
            self.progress = progress

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_file": self.source_file,
            "source_filename": self.source_filename,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "output_video_path": self.output_video_path,
            "drive_file_url": self.drive_file_url,
            "retry_count": self.retry_count,
            "repair_count": self.repair_count,
        }
