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
                repair_count INTEGER DEFAULT 0,
                campaign_id TEXT DEFAULT 'default'
            )
            """)

            # Graceful migration for existing database instances
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN campaign_id TEXT DEFAULT 'default'")
            except Exception:
                pass

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
                created_at TEXT NOT NULL,
                niche_id TEXT DEFAULT 'generic',
                tags TEXT DEFAULT '[]',
                width INTEGER,
                height INTEGER,
                fps REAL,
                description TEXT
            )
            """)

            # Graceful migrations for broll_assets
            for col, col_type in [
                ("niche_id", "TEXT DEFAULT 'generic'"),
                ("tags", "TEXT DEFAULT '[]'"),
                ("width", "INTEGER"),
                ("height", "INTEGER"),
                ("fps", "REAL"),
                ("description", "TEXT"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE broll_assets ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

            conn.commit()

    def save_job(self, job: Job):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO jobs (
                job_id, source_file, source_filename, status, progress,
                created_at, updated_at, error_message, transcript_text,
                transcript_segments, edit_plan, review_data,
                output_video_path, drive_file_url, retry_count, repair_count, campaign_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                repair_count=excluded.repair_count,
                campaign_id=excluded.campaign_id
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
                job.campaign_id,
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

    def save_broll_asset(
        self,
        asset_id: str,
        file_path: str,
        title: str,
        source: str,
        prompt: str,
        duration: float,
        score: int = 5,
        niche_id: str = "generic",
        tags: Optional[List[str]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        description: Optional[str] = None,
    ):
        tags_json = json.dumps(tags or [])
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO broll_assets (
                asset_id, file_path, title, source, prompt, duration, score, created_at,
                niche_id, tags, width, height, fps, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                score=excluded.score,
                file_path=excluded.file_path,
                niche_id=excluded.niche_id,
                tags=excluded.tags,
                width=excluded.width,
                height=excluded.height,
                fps=excluded.fps,
                description=excluded.description
            """, (
                asset_id, file_path, title, source, prompt, duration, score,
                utc_now_iso(), niche_id, tags_json, width, height, fps, description
            ))
            conn.commit()

    def search_broll_assets(
        self,
        niche_id: Optional[str] = None,
        query: Optional[str] = None,
        min_score: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search indexed local B-roll assets matching niche and query terms."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM broll_assets WHERE score >= ?"
            params: List[Any] = [min_score]

            if niche_id and niche_id != "generic":
                sql += " AND (niche_id = ? OR niche_id = 'generic')"
                params.append(niche_id)

            if query:
                terms = query.lower().split()
                for term in terms:
                    sql += " AND (LOWER(title) LIKE ? OR LOWER(prompt) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(description) LIKE ?)"
                    pattern = f"%{term}%"
                    params.extend([pattern, pattern, pattern, pattern])

            sql += " ORDER BY score DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, tuple(params))
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("tags"):
                    try:
                        d["tags"] = json.loads(d["tags"])
                    except Exception:
                        d["tags"] = []
                results.append(d)
            return results

    def list_broll_assets(self, niche_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List assets optionally filtered by niche."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if niche_id:
                cursor.execute(
                    "SELECT * FROM broll_assets WHERE niche_id = ? ORDER BY created_at DESC LIMIT ?",
                    (niche_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM broll_assets ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("tags"):
                    try:
                        d["tags"] = json.loads(d["tags"])
                    except Exception:
                        d["tags"] = []
                results.append(d)
            return results

    def get_broll_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM broll_assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if d.get("tags"):
                try:
                    d["tags"] = json.loads(d["tags"])
                except Exception:
                    d["tags"] = []
            return d

    def find_cached_asset(self, prompt: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM broll_assets WHERE prompt = ? AND score >= 7 ORDER BY score DESC LIMIT 1",
                (prompt,)
            )
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("tags"):
                    try:
                        d["tags"] = json.loads(d["tags"])
                    except Exception:
                        d["tags"] = []
                return d
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
            campaign_id=row["campaign_id"] if "campaign_id" in row.keys() and row["campaign_id"] else "default",
        )
