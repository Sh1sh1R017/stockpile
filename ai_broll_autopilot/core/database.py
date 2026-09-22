"""Database module managing SQLite persistence for AI B-Roll Autopilot."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.job import Job, JobState, utc_now_iso


class Database:
    """SQLite database manager for jobs, assets, and audit logs."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT,
                transcript_text TEXT,
                transcript_segments TEXT,
                edit_plan TEXT,
                review_data TEXT,
                output_video_path TEXT,
                drive_file_url TEXT,
                retry_count INTEGER DEFAULT 0,
                repair_count INTEGER DEFAULT 0
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS broll_assets (
                asset_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                title TEXT,
                source TEXT NOT NULL,
                prompt TEXT,
                duration REAL,
                score INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """)
            conn.commit()

    def save_job(self, job: Job):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO jobs (
                job_id, source_file, source_filename, status, progress,
                created_at, updated_at, error_message, transcript_text,
                transcript_segments, edit_plan, review_data,
                output_video_path, drive_file_url, retry_count, repair_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                progress=excluded.progress,
                updated_at=excluded.updated_at,
                error_message=excluded.error_message,
                transcript_text=excluded.transcript_text,
                transcript_segments=excluded.transcript_segments,
                edit_plan=excluded.edit_plan,
                review_data=excluded.review_data,
                output_video_path=excluded.output_video_path,
                drive_file_url=excluded.drive_file_url,
                retry_count=excluded.retry_count,
                repair_count=excluded.repair_count
            """, (
                job.job_id,
                job.source_file,
                job.source_filename,
                job.status.value,
                job.progress,
                job.created_at,
                job.updated_at,
                job.error_message,
                job.transcript_text,
                json.dumps(job.transcript_segments) if job.transcript_segments else None,
                json.dumps(job.edit_plan) if job.edit_plan else None,
                json.dumps(job.review_data) if job.review_data else None,
                job.output_video_path,
                job.drive_file_url,
                job.retry_count,
                job.repair_count,
            ))
            conn.commit()

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def list_jobs(self, limit: int = 50, status: Optional[str] = None) -> List[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def has_completed_job_for_file(self, filename: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM jobs WHERE source_filename = ? AND UPPER(status) = 'COMPLETED' LIMIT 1",
                (filename,)
            )
            return cursor.fetchone() is not None

    def delete_job(self, job_id: str):
        """Delete a job and its associated transition and feedback records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM job_transitions WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM job_broll_feedback WHERE job_id = ?", (job_id,))
            conn.commit()

    def clear_all_jobs(self):
        """Clear all jobs and transitions from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs")
            cursor.execute("DELETE FROM job_transitions")
            cursor.execute("DELETE FROM job_broll_feedback")
            conn.commit()

    def record_transition(self, job_id: str, from_state: str, to_state: str, message: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO job_transitions (job_id, from_state, to_state, timestamp, message)
            VALUES (?, ?, ?, ?, ?)
            """, (job_id, from_state, to_state, utc_now_iso(), message))
            conn.commit()

    def save_broll_asset(self, asset_id: str, file_path: str, title: str, source: str, prompt: str, duration: float, score: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO broll_assets (asset_id, file_path, title, source, prompt, duration, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                score=excluded.score,
                file_path=excluded.file_path
            """, (asset_id, file_path, title, source, prompt, duration, score, utc_now_iso()))
            conn.commit()

    def find_cached_asset(self, prompt: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM broll_assets WHERE prompt = ? AND score >= 7 ORDER BY score DESC LIMIT 1",
                (prompt,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"],
            source_file=row["source_file"],
            source_filename=row["source_filename"],
            status=JobState(row["status"]),
            progress=row["progress"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            error_message=row["error_message"],
            transcript_text=row["transcript_text"],
            transcript_segments=json.loads(row["transcript_segments"]) if row["transcript_segments"] else None,
            edit_plan=json.loads(row["edit_plan"]) if row["edit_plan"] else None,
            review_data=json.loads(row["review_data"]) if row["review_data"] else None,
            output_video_path=row["output_video_path"],
            drive_file_url=row["drive_file_url"],
            retry_count=row["retry_count"],
            repair_count=row["repair_count"],
        )
