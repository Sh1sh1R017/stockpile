"""Google Drive Cloud Synchronization Service.

Handles two-way synchronization between Google Drive and AI B-Roll Autopilot:
1. Inbound Sync: Polls/downloads new raw video clips from Google Drive input folder into local/cloud `input/`.
2. Outbound Sync: Uploads finished rendered MP4s, subtitles (.srt), and audit metadata to Google Drive output folder.
"""

import io
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


class DriveSyncService:
    """Manages cloud synchronization with Google Drive."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.input_folder_id = Config.GOOGLE_DRIVE_INPUT_FOLDER_ID or os.getenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "")
        self.output_folder_id = Config.GOOGLE_DRIVE_OUTPUT_FOLDER_ID or os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
        self.client_id = Config.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = Config.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")
        self._drive_service = None
        self._init_service()

    def _init_service(self):
        """Initialize Google Drive API client if credentials exist."""
        if not self.client_id or not self.client_secret:
            logger.info("Google Drive credentials not set in environment. Running in local/standby mode.")
            return

        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow

            scopes = ["https://www.googleapis.com/auth/drive"]
            creds = None
            token_path = Path("token.json")

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), scopes)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # In headless cloud environments, service account or stored refresh token is used
                    refresh_token = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN")
                    if refresh_token:
                        creds = Credentials(
                            None,
                            refresh_token=refresh_token,
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            scopes=scopes,
                        )
                        creds.refresh(Request())

            if creds and creds.valid:
                self._drive_service = build("drive", "v3", credentials=creds)
                logger.info("Google Drive API client initialized successfully.")
        except Exception as e:
            logger.warning(f"Google Drive initialization skipped or failed: {e}")
            self._drive_service = None

    def get_status(self) -> Dict[str, Any]:
        """Return Drive connection and configuration status."""
        is_connected = self._drive_service is not None
        return {
            "connected": is_connected,
            "has_credentials": bool(self.client_id and self.client_secret),
            "input_folder_id": self.input_folder_id or None,
            "output_folder_id": self.output_folder_id or None,
            "mode": "live_drive" if is_connected else "local_standby",
        }

    async def pull_new_inputs(self, dest_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Scan Google Drive input folder and download new videos to input/."""
        dest = dest_dir or Config.INPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        downloaded = []

        if not self._drive_service or not self.input_folder_id:
            logger.info("Google Drive not connected or input folder ID missing. Skipping pull.")
            return []

        try:
            from googleapiclient.http import MediaIoBaseDownload

            # Query video files in input folder
            query = f"'{self.input_folder_id}' in parents and trashed = false"
            results = self._drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)",
                pageSize=50
            ).execute()

            files = results.get("files", [])
            for f in files:
                name = f.get("name", "")
                file_id = f.get("id")
                ext = Path(name).suffix.lower()

                if ext in SUPPORTED_VIDEO_EXTS:
                    target_path = dest / name
                    # Skip if already exists or completed in DB
                    if target_path.exists() or self.db.has_completed_job_for_file(name):
                        continue

                    logger.info(f"Downloading new video from Google Drive: {name} ({file_id})")
                    request = self._drive_service.files().get_media(fileId=file_id)
                    with open(target_path, "wb") as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            _, done = downloader.next_chunk()

                    downloaded.append({
                        "file_id": file_id,
                        "name": name,
                        "local_path": str(target_path),
                        "size": f.get("size")
                    })
                    logger.info(f"Finished downloading: {name} -> {target_path}")

        except Exception as e:
            logger.error(f"Error pulling files from Google Drive: {e}", exc_info=True)

        return downloaded

    async def push_deliverables(self, job_dir: Path, slug: str) -> Optional[str]:
        """Upload completed deliverables to Google Drive output folder."""
        if not self._drive_service or not self.output_folder_id:
            logger.info("Google Drive not connected or output folder ID missing. Deliverables saved locally.")
            return None

        try:
            from googleapiclient.http import MediaFileUpload

            date_str = datetime.now().strftime("%Y-%m-%d")
            # Create date folder
            date_folder_meta = {
                "name": f"AI_BROLL_{date_str}",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.output_folder_id]
            }
            # Search or create date folder
            q = f"'{self.output_folder_id}' in parents and name = 'AI_BROLL_{date_str}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res = self._drive_service.files().list(q=q, fields="files(id)").execute()
            items = res.get("files", [])
            if items:
                parent_id = items[0]["id"]
            else:
                created = self._drive_service.files().create(body=date_folder_meta, fields="id").execute()
                parent_id = created.get("id")

            # Create project subfolder
            proj_meta = {
                "name": slug,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id]
            }
            created_proj = self._drive_service.files().create(body=proj_meta, fields="id").execute()
            proj_folder_id = created_proj.get("id")

            # Upload all files in job_dir
            main_video_url = None
            for fpath in job_dir.iterdir():
                if fpath.is_file():
                    media = MediaFileUpload(str(fpath), resumable=True)
                    f_meta = {"name": fpath.name, "parents": [proj_folder_id]}
                    uploaded = self._drive_service.files().create(body=f_meta, media_body=media, fields="id, webViewLink").execute()
                    if fpath.suffix == ".mp4" and "final" in fpath.name:
                        main_video_url = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{uploaded.get('id')}/view"

            logger.info(f"Successfully uploaded deliverables for {slug} to Google Drive: {main_video_url}")
            return main_video_url

        except Exception as e:
            logger.error(f"Failed to upload deliverables to Google Drive: {e}", exc_info=True)
            return None


drive_sync_service = DriveSyncService()
