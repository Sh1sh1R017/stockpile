"""Delivery service organizing local project folders and Google Drive uploads."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.job import Job

logger = logging.getLogger(__name__)


class DeliveryService:
    """Handles structured packaging and cloud upload for completed video jobs."""

    def __init__(self):
        self.output_base = Config.OUTPUT_DIR
        self._drive_service = None
        self._init_drive()

    def _init_drive(self):
        if Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET and Config.GOOGLE_DRIVE_FOLDER_ID:
            try:
                import sys
                sys.path.insert(0, str(Config.STOCKPILE_DIR))
                from services.drive_service import DriveService
                self._drive_service = DriveService(
                    Config.GOOGLE_CLIENT_ID,
                    Config.GOOGLE_CLIENT_SECRET,
                    Config.GOOGLE_DRIVE_FOLDER_ID
                )
                logger.info("Google Drive delivery service initialized")
            except Exception as e:
                logger.warning(f"Google Drive initialization failed: {e}")
                self._drive_service = None

    async def deliver(self, job: Job, rendered_video_path: str, srt_content: Optional[str]) -> Dict[str, str]:
        """Package final video deliverables locally and to Google Drive."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = Path(job.source_filename).stem
        job_dir = self.output_base / f"{job.job_id}_{slug}"
        job_dir.mkdir(parents=True, exist_ok=True)

        final_video_dest = job_dir / f"final_{slug}.mp4"
        shutil.copy2(rendered_video_path, final_video_dest)

        # Write SRT
        if srt_content:
            (job_dir / f"{slug}.srt").write_text(srt_content, encoding="utf-8")

        # Write Edit Plan JSON
        if job.edit_plan:
            (job_dir / "edit_plan.json").write_text(
                json.dumps(job.edit_plan, indent=2), encoding="utf-8"
            )

        # Write Review Report
        if job.review_data:
            (job_dir / "review_report.json").write_text(
                json.dumps(job.review_data, indent=2), encoding="utf-8"
            )

        delivery_info = {
            "local_dir": str(job_dir),
            "final_video": str(final_video_dest),
            "drive_url": None,
        }

        # Google Drive Upload
        if self._drive_service:
            try:
                logger.info(f"Uploading {final_video_dest.name} to Google Drive...")
                import asyncio
                loop = asyncio.get_event_loop()
                folder_id = await loop.run_in_executor(
                    None,
                    self._drive_service.create_project_structure,
                    f"AI BROLL OUTPUT/{date_str}/{slug}"
                )
                file_id = await loop.run_in_executor(
                    None,
                    self._drive_service.upload_file,
                    str(final_video_dest),
                    folder_id
                )
                drive_url = f"https://drive.google.com/file/d/{file_id}/view"
                delivery_info["drive_url"] = drive_url
                logger.info(f"Successfully uploaded to Google Drive: {drive_url}")
            except Exception as e:
                logger.error(f"Google Drive upload failed: {e}", exc_info=True)

        return delivery_info
