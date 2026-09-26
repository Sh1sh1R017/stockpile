"""FastAPI REST API server for AI B-Roll Autopilot.

Exposes REST endpoints for the Next.js Web Dashboard, real-time job monitoring,
video uploads, video streaming, emotional feedback submission, and Google Drive cloud sync.
"""

import asyncio
import json
import logging
import os
import shutil
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.core.job import Job, JobState
from ai_broll_autopilot.orchestrator import Orchestrator
from ai_broll_autopilot.services.learning import FeedbackLearningEngine
from ai_broll_autopilot.services.drive_sync import drive_sync_service
from ai_broll_autopilot.services.pexels import pexels_service
from ai_broll_autopilot.services.nle_exporter import NLEExporter
from ai_broll_autopilot.niches import niche_registry
from ai_broll_autopilot.styles import style_registry
from ai_broll_autopilot.services.niche_detector import niche_detector, content_analyzer
from ai_broll_autopilot.services.clip_detector import clip_detector
from ai_broll_autopilot.services.edit_director import edit_director, EditPlan
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter
from ai_broll_autopilot.services.broll_library import broll_library, extract_media_metadata
from ai_broll_autopilot.services.transcriber import Transcriber
from ai_broll_autopilot.services.qc_service import edit_quality_service

logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="AI B-Roll Autopilot API",
    version="1.0.0",
    description="Backend API for AI B-Roll Autopilot Studio",
)

# Enable CORS for Next.js web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development and flexible Azure deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
db = Database()
learning_engine = FeedbackLearningEngine()
orchestrator = Orchestrator()
hdr_tasks: Dict[str, Dict[str, Any]] = {}


# Request Models
class FeedbackRequest(BaseModel):
    job_id: str
    rating: int = Field(..., ge=1, le=10, description="Rating from 1 to 10")
    feedback: str = Field(..., description="User feedback or direction")
    shot_id: Optional[str] = None
    preferred_metaphor: Optional[str] = None
    avoided_metaphor: Optional[str] = None
    thematic_category: Optional[str] = "General"


class DriveConfigUpdate(BaseModel):
    input_folder_id: Optional[str] = None
    output_folder_id: Optional[str] = None


class YouTubeJobRequest(BaseModel):
    url: str = Field(..., description="YouTube video or Shorts URL to download and process")
    campaign_id: Optional[str] = Field("default", description="Target campaign preset ID (e.g. 'default')")


class MemeGenerateRequest(BaseModel):
    template_key: str = Field(..., description="Meme template archetype or key")
    captions: Dict[str, str] = Field(default_factory=dict, description="Custom meme captions")
    sfx_file: Optional[str] = Field(None, description="Punchline SFX filename from catalog")
    duration: float = Field(2.8, description="Target duration in seconds")


class ShotMemeRequest(BaseModel):
    template_key: str = Field(..., description="Meme template archetype or key")
    captions: Dict[str, str] = Field(default_factory=dict, description="Custom meme captions")
    sfx_file: Optional[str] = Field(None, description="Punchline SFX filename from catalog")
    duration: Optional[float] = Field(None, description="Target duration in seconds")


class ShotTrimRequest(BaseModel):
    start_time: float = Field(..., description="New shot start timestamp in seconds")
    end_time: float = Field(..., description="New shot end timestamp in seconds")
    duration: Optional[float] = Field(None, description="Optional explicit duration")


class ShotInsertRequest(BaseModel):
    start_time: float = Field(..., description="Timestamp to insert cutaway at")
    duration: float = Field(2.5, description="Duration of cutaway in seconds")
    style: str = Field("stockpile", description="Cutaway style: stockpile or meme")
    dialogue_quote: Optional[str] = Field("", description="Spoken dialogue context")
    search_prompt: Optional[str] = Field("focused business professional", description="Stock search query")
    meme_template: Optional[str] = Field("stepped_in_shit", description="Meme template if style is meme")


class StockSwapRequest(BaseModel):
    download_url: Optional[str] = Field(None, description="Pexels candidate MP4 download URL")
    prompt: Optional[str] = Field(None, description="Updated search prompt description")


class JobSettingsRequest(BaseModel):
    subtitles_enabled: Optional[bool] = Field(None, description="Toggle kinetic subtitles on/off")
    subtitle_style: Optional[str] = Field(None, description="Subtitle style: hormozi, beast, clean")
    subtitle_position: Optional[str] = Field(None, description="Subtitle position: bottom, center, top")
    bgm_track_id: Optional[str] = Field(None, description="BGM track ID or None to mute")
    bgm_volume: Optional[float] = Field(None, description="BGM volume 0.0 to 1.0")
    bgm_ducking: Optional[bool] = Field(None, description="Toggle voice auto-ducking")
    hdr_upscale_enabled: Optional[bool] = Field(None, description="Toggle SDR2HDR upscale & HDR10 output")
    hdr_output_scale: Optional[float] = Field(None, description="HDR output scale: 1.0 (native), 1.5 (QHD), 2.0 (4K UHD)")
    hdr_tone: Optional[str] = Field(None, description="HDR tone: vivid or reference")


class HdrUpscaleRequest(BaseModel):
    output_scale: Optional[float] = Field(1.0, description="Scale factor: 1.0 (native), 1.5 (QHD), 2.0 (4K UHD)")
    tone: Optional[str] = Field("vivid", description="Tone mapping: vivid (viral pop) or reference (BT.2408)")
    hdr_style: Optional[str] = Field("natural", description="Style: natural, cinematic, or night")
    fast_mode: Optional[bool] = Field(True, description="Fast mode for rapid generation")


@app.on_event("startup")
async def startup_event():
    """Start background queue processor on API server boot."""
    Config.ensure_directories()
    # Start the worker queue asynchronously
    asyncio.create_task(orchestrator.queue.start(orchestrator.process_job))
    logger.info("FastAPI Server & Autopilot Queue initialized.")


# API Endpoints
@app.get("/api/health")
async def get_health():
    """System health check and diagnostic information."""
    jobs = db.list_jobs(limit=100)
    completed_jobs = [j for j in jobs if j.status == JobState.COMPLETED]

    return {
        "status": "online",
        "version": "1.0.0",
        "whisper_model": Config.WHISPER_MODEL,
        "gemini_model": Config.GEMINI_MODEL,
        "total_jobs": len(jobs),
        "completed_jobs": len(completed_jobs),
        "input_dir": str(Config.INPUT_DIR),
        "output_dir": str(Config.OUTPUT_DIR),
        "drive_status": drive_sync_service.get_status(),
        "pexels_available": pexels_service.is_available(),
        "youtube_available": True,
    }


@app.get("/api/stats")
async def get_stats():
    """High-level metrics for dashboard cards."""
    jobs = db.list_jobs(limit=100)
    completed = [j for j in jobs if j.status == JobState.COMPLETED]
    queued = [j for j in jobs if j.status in (JobState.QUEUED, JobState.INGESTING, JobState.TRANSCRIBING, JobState.DIRECTING, JobState.MATCHING, JobState.RENDERING, JobState.REVIEWING)]

    # Compute average emotional score from completed edit plans
    scores = []
    for j in completed:
        if j.edit_plan and isinstance(j.edit_plan, dict):
            for s in j.edit_plan.get("shots", []):
                if "emotional_score" in s:
                    scores.append(s["emotional_score"])

    avg_score = round(sum(scores) / len(scores), 1) if scores else 9.0
    rules = learning_engine.get_active_rules()

    return {
        "total_jobs": len(jobs),
        "completed_count": len(completed),
        "in_progress_count": len(queued),
        "average_emotional_score": avg_score,
        "active_learning_rules": len(rules),
    }


@app.get("/api/jobs")
async def list_jobs(limit: int = 50):
    """List all jobs with metadata and status."""
    jobs = db.list_jobs(limit=limit)
    res = []
    for j in jobs:
        # Check if output file exists
        has_video = bool(j.output_video_path and Path(j.output_video_path).exists())

        # Extract emotional summary if available
        emotional_summary = None
        if j.edit_plan and isinstance(j.edit_plan, dict):
            emotional_summary = j.edit_plan.get("summary")

        res.append({
            "job_id": j.job_id,
            "filename": j.source_filename,
            "status": j.status.value,
            "progress": j.progress,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
            "error_message": j.error_message,
            "has_video": has_video,
            "emotional_summary": emotional_summary,
            "drive_file_url": j.drive_file_url,
            "review_data": j.review_data,
            "campaign_id": getattr(j, "campaign_id", "default"),
        })
    return res


@app.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: str):
    """Retrieve full details, transcript, and edit plan for a specific job."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    has_video = bool(job.output_video_path and Path(job.output_video_path).exists())

    # Check for survey file
    survey_data = None
    if job.output_video_path:
        survey_path = Path(job.output_video_path).parent / "feedback_survey.json"
        if survey_path.exists():
            try:
                survey_data = json.loads(survey_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    # Enhance edit_plan shots with direct B-roll video preview URLs
    enhanced_edit_plan = None
    if job.edit_plan and isinstance(job.edit_plan, dict):
        enhanced_edit_plan = dict(job.edit_plan)
        enhanced_shots = []
        for s in job.edit_plan.get("shots", []):
            sc = dict(s)
            sid = s.get("shot_id")
            # Verify if asset exists
            has_asset = bool(s.get("asset_path") and Path(s["asset_path"]).exists())
            if not has_asset:
                wk_broll = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
                if wk_broll.exists():
                    for cand in wk_broll.iterdir():
                        if cand.is_file() and cand.suffix == ".mp4" and cand.name.startswith(sid):
                            sc["asset_path"] = str(cand)
                            has_asset = True
                            break
            if has_asset:
                sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{sid}"
                sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{sid}/thumb"

            # Attach audio URLs for web preview
            if sc.get("contextual_sfx") and "file" in sc["contextual_sfx"]:
                sc["contextual_sfx"]["audio_url"] = f"/api/sfx/{sc['contextual_sfx']['file']}"
            if sc.get("transition", {}).get("stinger_sfx") and "file" in sc["transition"]["stinger_sfx"]:
                sc["transition"]["stinger_sfx"]["audio_url"] = f"/api/sfx/{sc['transition']['stinger_sfx']['file']}"

            enhanced_shots.append(sc)
        enhanced_edit_plan["shots"] = enhanced_shots

    return {
        "job_id": job.job_id,
        "filename": job.source_filename,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "error_message": job.error_message,
        "transcript_text": job.transcript_text,
        "transcript_segments": job.transcript_segments,
        "edit_plan": enhanced_edit_plan,
        "review_data": job.review_data,
        "output_video_path": job.output_video_path,
        "has_video": has_video,
        "drive_file_url": job.drive_file_url,
        "survey_data": survey_data,
        "campaign_id": getattr(job, "campaign_id", "default"),
    }


@app.get("/api/jobs/{job_id}/video")
async def get_job_video(job_id: str):
    """Stream the final rendered MP4 video file with HTTP Range support."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    vpath = None
    if job.output_video_path and Path(job.output_video_path).exists():
        vpath = Path(job.output_video_path)
    else:
        # Check workspace rendered video
        wk_v = Config.OUTPUT_DIR / "workspace" / job.job_id / f"rendered_{job.source_filename}"
        if wk_v.exists():
            vpath = wk_v
        else:
            # Check for any .mp4 starting with final in output folder
            slug = Path(job.source_filename).stem
            cand = Config.OUTPUT_DIR / f"{job.job_id}_{slug}" / f"final_{slug}.mp4"
            if cand.exists():
                vpath = cand

    if not vpath or not vpath.exists():
        raise HTTPException(status_code=404, detail="Video file missing on disk")

    return FileResponse(
        path=str(vpath),
        media_type="video/mp4",
        filename=vpath.name,
        content_disposition_type="inline",
    )


@app.get("/api/jobs/{job_id}/broll/{shot_id}")
async def get_job_broll_asset(job_id: str, shot_id: str):
    """Stream an individual B-roll cutaway video clip for standalone preview."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    target_path = None
    if job.edit_plan and isinstance(job.edit_plan, dict):
        for s in job.edit_plan.get("shots", []):
            if s.get("shot_id") == shot_id and s.get("asset_path"):
                p = Path(s["asset_path"])
                if p.exists():
                    target_path = p
                    break

    if not target_path:
        # Search workspace broll directory
        wk_broll = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
        if wk_broll.exists():
            for f in wk_broll.iterdir():
                if f.is_file() and f.suffix == ".mp4" and f.name.startswith(shot_id):
                    target_path = f
                    break

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail=f"B-roll clip '{shot_id}' not found")

    return FileResponse(
        path=str(target_path),
        media_type="video/mp4",
        filename=target_path.name,
        content_disposition_type="inline",
    )


@app.get("/api/jobs/{job_id}/broll/{shot_id}/thumb")
async def get_job_broll_thumb(job_id: str, shot_id: str):
    """Serve a JPEG frame thumbnail for a specific B-roll cutaway."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    target_path = None
    if job.edit_plan and isinstance(job.edit_plan, dict):
        for s in job.edit_plan.get("shots", []):
            if s.get("shot_id") == shot_id and s.get("asset_path"):
                p = Path(s["asset_path"])
                if p.exists():
                    target_path = p
                    break

    if not target_path:
        wk_broll = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
        if wk_broll.exists():
            for f in wk_broll.iterdir():
                if f.is_file() and f.suffix == ".mp4" and f.name.startswith(shot_id):
                    target_path = f
                    break

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail=f"B-roll clip '{shot_id}' not found")

    thumb_path = target_path.parent / f"{shot_id}_thumb.jpg"
    if not thumb_path.exists():
        cmd = [
            "ffmpeg", "-y",
            "-ss", "0.5",
            "-i", str(target_path),
            "-frames:v", "1",
            "-update", "1",
            "-q:v", "2",
            str(thumb_path)
        ]
        try:
            import subprocess
            await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)
        except Exception as e:
            logger.error(f"Failed to generate thumb for {shot_id}: {e}")

    if not thumb_path.exists():
        raise HTTPException(status_code=500, detail="Could not extract thumbnail")

    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        filename=thumb_path.name,
        content_disposition_type="inline",
    )


@app.get("/api/sfx/{filename}")
async def get_sfx_audio(filename: str):
    """Serve individual SFX from the 189 unified sound effect library."""
    import urllib.parse
    clean_fn = urllib.parse.unquote(filename).strip()

    # 1. Check local split_sfx
    sfx_path = Config.OUTPUT_DIR / "split_sfx" / clean_fn
    if sfx_path.exists() and sfx_path.is_file():
        media_type = "audio/wav" if clean_fn.lower().endswith(".wav") else "audio/mpeg"
        return FileResponse(path=str(sfx_path), media_type=media_type, filename=clean_fn)

    # 2. Check catalog for exact or case-insensitive filename or path
    catalog_path = Config.OUTPUT_DIR / "split_sfx" / "sfx_catalog.json"
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
                for item in catalog:
                    item_file = item.get("file", "")
                    item_name = Path(item.get("path", "")).name
                    if clean_fn.lower() in (item_file.lower(), item_name.lower()):
                        item_p = Path(item["path"])
                        if item_p.exists():
                            media_type = "audio/wav" if item_p.suffix.lower() == ".wav" else "audio/mpeg"
                            return FileResponse(path=str(item_p), media_type=media_type, filename=item_p.name)
        except Exception as e:
            logger.warning(f"Error checking catalog for {filename}: {e}")

    raise HTTPException(status_code=404, detail=f"SFX file '{filename}' not found")


@app.get("/api/jobs/{job_id}/export/xml")
async def export_job_xml(job_id: str):
    """Export standard Final Cut Pro 7 XML timeline compatible with Adobe Premiere Pro and DaVinci Resolve."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    shots = job.edit_plan.get("shots", []) if (job.edit_plan and isinstance(job.edit_plan, dict)) else []
    total_dur = job.edit_plan.get("total_duration", 12.0) if job.edit_plan else 12.0

    xml_text = NLEExporter.generate_fcp_xml(
        project_name=job.source_filename,
        base_video_path=job.source_file,
        total_duration=total_dur,
        shots=shots,
        fps=Config.TARGET_FPS,
        width=Config.TARGET_WIDTH,
        height=Config.TARGET_HEIGHT
    )

    clean_name = Path(job.source_filename).stem
    return Response(
        content=xml_text,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="timeline_{clean_name}.xml"'}
    )


@app.get("/api/jobs/{job_id}/export/zip")
async def export_job_zip(job_id: str):
    """Download 1-Click production ZIP archive containing master video, XML timeline, SRT, and cutaways."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clean_name = Path(job.source_filename).stem
    zip_path = Config.OUTPUT_DIR / "workspace" / job.job_id / f"package_{clean_name}.zip"
    NLEExporter.create_zip_package(job, zip_path)

    if not zip_path.exists():
        raise HTTPException(status_code=500, detail="Failed to build ZIP archive")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"package_{clean_name}.zip"
    )


@app.get("/api/jobs/{job_id}/openreel-project")
async def get_job_openreel_project(job_id: str):
    """Retrieve native OpenReel Schema 1.2.0 project JSON for this job.

    If the job has been rendered, the OpenReel project is built around the
    final 9:16 render (with face tracking, B-roll, captions all baked in),
    so the user sees exactly what the AI produced and can fine-tune on top.
    If not yet rendered, falls back to the raw source + edit plan approach.
    """
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    base_asset_url = f"http://127.0.0.1:8000/api/jobs/{urllib.parse.quote(job.job_id)}/assets"
    oreel_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "openreel"

    # ----------------------------------------------------------------
    # 1. Find the final rendered video (9:16 AI-edited output)
    # ----------------------------------------------------------------
    final_video_path: Path | None = None
    for candidate_dir in Config.OUTPUT_DIR.iterdir():
        if candidate_dir.is_dir() and job.job_id in candidate_dir.name:
            finals = sorted(candidate_dir.glob("final_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if finals:
                final_video_path = finals[0]
                break

    if final_video_path and final_video_path.exists():
        # ----------------------------------------------------------------
        # 2a. RENDERED MODE — final 9:16 render on track 1 + B-roll on track 2
        # ----------------------------------------------------------------
        import subprocess, time as _time

        final_name = final_video_path.name
        final_url = f"{base_asset_url}/final"
        final_thumb_url = f"{base_asset_url}/final/thumb"

        # Get actual duration via ffprobe
        final_dur = float(job.edit_plan.get("total_duration", 30.0)) if job.edit_plan else 30.0
        try:
            probe = await asyncio.to_thread(
                subprocess.run,
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(final_video_path)],
                capture_output=True, text=True
            )
            probe_data = json.loads(probe.stdout or "{}")
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    dur_str = stream.get("duration") or probe_data.get("format", {}).get("duration", "")
                    if dur_str:
                        final_dur = float(dur_str)
                    break
        except Exception:
            pass

        now_ms = int(_time.time() * 1000)
        proj_id = f"proj_{job.job_id[:12]}"
        title = f"AI Edit: {Path(job.source_filename).stem}"

        # ---- Collect B-roll files from workspace ----
        broll_workspace = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
        broll_files: list[Path] = sorted(broll_workspace.glob("*.mp4")) if broll_workspace.exists() else []

        # Build shot → broll file mapping from edit_plan
        plan_shots = job.edit_plan.get("shots", []) if job.edit_plan else []
        # Match shots that have asset_path set, else try to match by index with broll files
        shot_broll_pairs = []
        for i, shot in enumerate(plan_shots):
            asset_path = shot.get("asset_path")
            if asset_path and Path(asset_path).exists():
                bfile = Path(asset_path)
            elif i < len(broll_files):
                bfile = broll_files[i]
            else:
                bfile = None
            shot_broll_pairs.append((shot, bfile))

        # Also include any broll files not matched to a shot
        matched_files = {p for _, p in shot_broll_pairs if p}
        unmatched_broll = [f for f in broll_files if f not in matched_files]

        # ---- Build media library items ----
        media_items = [
            {
                "id": "media_final_render",
                "name": final_name,
                "type": "video",
                "metadata": {
                    "duration": final_dur,
                    "width": 1080,
                    "height": 1920,
                    "frameRate": 30,
                    "codec": "h264",
                    "sampleRate": 48000,
                    "channels": 2,
                    "fileSize": final_video_path.stat().st_size,
                    "hasVideo": True,
                    "hasAudio": True,
                },
                "fileHandle": None,
                "blob": None,
                "thumbnailUrl": final_thumb_url,
                "waveformData": None,
                "isPlaceholder": False,
                "originalUrl": final_url,
                "url": final_url,
                "sourceFile": {
                    "name": final_name,
                    "size": final_video_path.stat().st_size,
                    "lastModified": now_ms,
                },
            }
        ]

        broll_track_clips = []
        broll_markers = []

        def _broll_media_item(bfile: Path, media_id: str, shot_dur: float) -> dict:
            bname = bfile.name
            burl = f"{base_asset_url}/{urllib.parse.quote(bname)}"
            bthumb = f"{base_asset_url}/{urllib.parse.quote(bname)}/thumb"
            return {
                "id": media_id,
                "name": bname,
                "type": "video",
                "metadata": {
                    "duration": shot_dur,
                    "width": 1920,
                    "height": 1080,
                    "frameRate": 30,
                    "codec": "h264",
                    "sampleRate": 48000,
                    "channels": 2,
                    "fileSize": bfile.stat().st_size,
                    "hasVideo": True,
                    "hasAudio": False,
                },
                "fileHandle": None,
                "blob": None,
                "thumbnailUrl": bthumb,
                "waveformData": None,
                "isPlaceholder": False,
                "originalUrl": burl,
                "url": burl,
                "sourceFile": {
                    "name": bname,
                    "size": bfile.stat().st_size,
                    "lastModified": now_ms,
                },
            }

        for i, (shot, bfile) in enumerate(shot_broll_pairs):
            if not bfile:
                continue
            shot_id = shot.get("shot_id", f"broll_{i+1}")
            media_id = f"media_broll_{i+1}"
            st = float(shot.get("start_time", 0.0))
            dur = float(shot.get("duration", 2.0))

            media_items.append(_broll_media_item(bfile, media_id, dur))

            broll_track_clips.append({
                "id": f"clip_{shot_id}",
                "mediaId": media_id,
                "trackId": "track_video_broll",
                "startTime": st,
                "duration": dur,
                "inPoint": 0.0,
                "outPoint": dur,
                "effects": [],
                "audioEffects": [],
                "transform": {
                    "position": {"x": 0.5, "y": 0.5},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                    "fitMode": "cover",
                },
                "volume": 0.0,
                "keyframes": [],
                "metadata": {
                    "searchQuery": shot.get("search_prompt", ""),
                    "rationale": shot.get("narrative_reason", ""),
                    "dialogueQuote": shot.get("dialogue_quote", ""),
                },
            })

            broll_markers.append({
                "id": f"marker_broll_{i+1}",
                "time": st,
                "label": f"B-Roll {i+1}: {shot.get('search_prompt', shot_id)}",
                "color": "#F59E0B",
            })

        # Add any unmatched broll files to media library only (no timeline clip)
        for j, bfile in enumerate(unmatched_broll):
            media_id = f"media_broll_extra_{j+1}"
            media_items.append(_broll_media_item(bfile, media_id, 3.0))

        # ---- Build tracks ----
        tracks = [
            {
                "id": "track_video_main",
                "name": "🎬 AI Edit (9:16) — Face Tracked",
                "type": "video",
                "role": "dialogue",
                "mode": "standard",
                "hidden": False,
                "muted": False,
                "locked": True,   # Lock the main render so user doesn't accidentally move it
                "solo": False,
                "transitions": [],
                "clips": [
                    {
                        "id": "clip_final_render",
                        "mediaId": "media_final_render",
                        "trackId": "track_video_main",
                        "startTime": 0.0,
                        "duration": final_dur,
                        "inPoint": 0.0,
                        "outPoint": final_dur,
                        "effects": [],
                        "audioEffects": [],
                        "transform": {
                            "position": {"x": 0.5, "y": 0.5},
                            "scale": {"x": 1.0, "y": 1.0},
                            "rotation": 0,
                            "anchor": {"x": 0.5, "y": 0.5},
                            "opacity": 1.0,
                            "fitMode": "contain",
                        },
                        "volume": 1.0,
                        "keyframes": [],
                    }
                ],
            }
        ]

        if broll_track_clips:
            tracks.append({
                "id": "track_video_broll",
                "name": "✂️ B-Roll Cuts (Swap / Reposition)",
                "type": "video",
                "role": "general",
                "mode": "standard",
                "hidden": False,
                "muted": True,
                "locked": False,
                "solo": False,
                "transitions": [],
                "clips": broll_track_clips,
            })

        project = {
            "id": proj_id,
            "name": title,
            "createdAt": now_ms,
            "modifiedAt": now_ms,
            "settings": {
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "frameRate": 30,
                "sampleRate": 48000,
                "channels": 2,
            },
            "timeline": {
                "duration": final_dur,
                "tracks": tracks,
                "subtitles": [],
                "markers": broll_markers,
            },
            "mediaLibrary": {"items": media_items},
            "textClips": [],
            "shapeClips": [],
            "svgClips": [],
            "stickerClips": [],
            "capabilities": ["tracks-universal", "behind-subject"],
        }

        return {"version": "1.2.0", "project": project}

    # ----------------------------------------------------------------
    # 2b. DRAFT MODE — job not rendered yet, use raw source + edit plan
    # ----------------------------------------------------------------
    # Check for a cached project
    project_oreel = oreel_dir / f"{job.job_id}.oreel"
    if project_oreel.exists():
        try:
            with open(project_oreel, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("project", {}).get("mediaLibrary", {}).get("items", [])
                has_file_urls = any((item.get("url") or "").startswith("file:///") for item in items)
                has_space_urls = any(" " in (item.get("url") or "") for item in items)
                if not has_file_urls and not has_space_urls and items:
                    return data
        except Exception:
            pass

    if not job.edit_plan:
        raise HTTPException(status_code=400, detail="Job has no edit plan and no rendered output yet")

    plan_dict = job.edit_plan
    total_dur = plan_dict.get("total_duration") or plan_dict.get("target_duration") or 30.0

    plan_obj = EditPlan(
        plan_id=f"plan_{job.job_id}",
        title=f"Draft: {Path(job.source_filename).stem}",
        target_duration=float(total_dur),
        source_media={"path": job.source_file, "duration": float(total_dur), "title": job.source_filename},
        clip_interval={"in_point": 0.0, "out_point": float(total_dur)},
        niche=plan_dict.get("niche", {"name": "Podcast", "id": "generic"}),
        style=plan_dict.get("style", {"name": "Clean Podcast", "id": "clean_podcast"}),
        shots=plan_dict.get("shots", []),
        text_overlays=plan_dict.get("text_overlays", []),
        subtitles=plan_dict.get("subtitles", []),
        zooms=plan_dict.get("zooms", []),
        audio_cues=plan_dict.get("audio_cues", {}),
    )

    oreel_dir.mkdir(parents=True, exist_ok=True)
    openreel_adapter.export_project_files(
        edit_plan=plan_obj,
        output_dir=oreel_dir,
        project_filename=f"{job.job_id}.oreel",
        base_asset_url=base_asset_url,
    )
    return openreel_adapter.create_openreel_project(plan_obj, base_asset_url=base_asset_url)


@app.api_route("/api/jobs/{job_id}/openreel-project", methods=["POST", "PUT"])
async def save_job_openreel_project(job_id: str, payload: Dict[str, Any]):
    """Save user modifications from OpenReel Editor back into Stockpile.

    Persists updated .oreel and project.json files, synchronizes shot timings,
    subtitles, and text overlays in SQLite database, enabling re-rendering.
    """
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    oreel_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "openreel"
    oreel_dir.mkdir(parents=True, exist_ok=True)
    project_oreel = oreel_dir / f"{job.job_id}.oreel"
    project_json = oreel_dir / "project.json"

    # 1. Format payload conforming to Schema 1.2.0
    project_obj = payload.get("project", payload)
    save_data = {
        "version": "1.2.0",
        "project": project_obj,
    }

    # 2. Write to disk
    with open(project_oreel, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    with open(project_json, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)

    # 3. Synchronize edit_plan in SQLite if job has one
    if job.edit_plan and isinstance(job.edit_plan, dict):
        plan_dict = job.edit_plan
        plan_obj = EditPlan(
            plan_id=f"plan_{job.job_id}",
            title=plan_dict.get("title", f"Edit: {Path(job.source_filename).stem}"),
            target_duration=float(plan_dict.get("total_duration") or plan_dict.get("target_duration") or 30.0),
            source_media={"path": job.source_file, "duration": float(plan_dict.get("total_duration") or 30.0), "title": job.source_filename},
            clip_interval=plan_dict.get("clip_interval", {"in_point": 0.0, "out_point": 30.0}),
            niche=plan_dict.get("niche", {"name": "Podcast", "id": "generic"}),
            style=plan_dict.get("style", {"name": "Clean Podcast", "id": "clean_podcast"}),
            shots=plan_dict.get("shots", []),
            text_overlays=plan_dict.get("text_overlays", []),
            subtitles=plan_dict.get("subtitles", []),
            zooms=plan_dict.get("zooms", []),
            audio_cues=plan_dict.get("audio_cues", {}),
        )

        updated_plan = openreel_adapter.update_edit_plan_from_openreel(plan_obj, save_data)
        updated_dict = updated_plan.to_dict()
        # Mark with OpenReel edit tag
        updated_dict["openreel_custom_edited"] = True
        updated_dict["last_openreel_sync"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        job.edit_plan = updated_dict
        job.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        db.save_job(job)

        return {
            "status": "SAVED",
            "job_id": job.job_id,
            "shots_count": len(updated_plan.shots),
            "target_duration": updated_plan.target_duration,
            "subtitles_count": len(updated_plan.subtitles),
            "text_overlays_count": len(updated_plan.text_overlays),
            "message": "OpenReel edits saved and synchronized with Stockpile SQLite database.",
        }

    return {
        "status": "SAVED",
        "job_id": job.job_id,
        "message": "OpenReel project file saved to disk.",
    }


@app.api_route("/api/jobs/{job_id}/assets/{asset_name:path}", methods=["GET", "HEAD"])
async def get_job_asset(job_id: str, asset_name: str):
    """Serve media assets (source video, B-roll clips, audio, graphics, thumbnails) to OpenReel Editor."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    def _infer_mime(filename: str) -> str:
        s = Path(filename).suffix.lower()
        if s in (".jpg", ".jpeg"):
            return "image/jpeg"
        if s == ".png":
            return "image/png"
        if s == ".webp":
            return "image/webp"
        if s in (".mp3", ".mpeg"):
            return "audio/mpeg"
        if s == ".wav":
            return "audio/wav"
        return "video/mp4"

    raw_asset = urllib.parse.unquote(asset_name).strip()
    is_thumb = raw_asset.endswith("/thumb") or raw_asset.endswith(".thumb.jpg")
    clean_asset = raw_asset[:-6] if raw_asset.endswith("/thumb") else (raw_asset[:-10] if raw_asset.endswith(".thumb.jpg") else raw_asset)
    clean_name = Path(clean_asset).name

    # Handle Thumbnail requests
    if is_thumb:
        # 1. A-Roll source thumb
        if clean_name in ("source", "main", Path(job.source_filename).name):
            source_thumb = Config.OUTPUT_DIR / "workspace" / job.job_id / "source_thumb.jpg"
            if not source_thumb.exists() and job.source_file and Path(job.source_file).exists():
                source_thumb.parent.mkdir(parents=True, exist_ok=True)
                cmd = ["ffmpeg", "-y", "-ss", "1.0", "-i", str(job.source_file), "-frames:v", "1", "-update", "1", "-q:v", "2", str(source_thumb)]
                try:
                    import subprocess
                    await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)
                except Exception as e:
                    logger.error(f"Failed to generate source thumb: {e}")
            if source_thumb.exists():
                return FileResponse(path=str(source_thumb), media_type="image/jpeg", filename="source_thumb.jpg", content_disposition_type="inline")

        # 2. B-Roll thumb in workspace
        broll_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
        if broll_dir.exists():
            stem = Path(clean_name).stem
            for cand_name in (f"{stem}_thumb.jpg", f"{clean_name}_thumb.jpg", f"{clean_name}.jpg"):
                cand = broll_dir / cand_name
                if cand.exists():
                    return FileResponse(path=str(cand), media_type="image/jpeg", filename=cand.name, content_disposition_type="inline")
            # Generate if video exists
            vid_cand = broll_dir / clean_name
            if not vid_cand.exists() and not clean_name.endswith(".mp4"):
                vid_cand = broll_dir / f"{clean_name}.mp4"
            if vid_cand.exists():
                thumb_target = broll_dir / f"{stem}_thumb.jpg"
                cmd = ["ffmpeg", "-y", "-ss", "0.5", "-i", str(vid_cand), "-frames:v", "1", "-update", "1", "-q:v", "2", str(thumb_target)]
                try:
                    import subprocess
                    await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)
                    if thumb_target.exists():
                        return FileResponse(path=str(thumb_target), media_type="image/jpeg", filename=thumb_target.name, content_disposition_type="inline")
                except Exception as e:
                    logger.error(f"Failed to generate broll thumb: {e}")

        raise HTTPException(status_code=404, detail=f"Thumbnail for asset '{asset_name}' not found")

    # Regular Asset requests
    # 0. Rendered final output video — what the AI editor produced (9:16 with face tracking, B-roll, captions baked in)
    if clean_name in ("final", "final_render", "output"):
        # Find the rendered final file for this job
        job_out_dir = Config.OUTPUT_DIR / job.job_id if (Config.OUTPUT_DIR / job.job_id).exists() else None
        # Also scan output root for dirs that start with job_id prefix
        if not job_out_dir:
            for d in Config.OUTPUT_DIR.iterdir():
                if d.is_dir() and job.job_id in d.name:
                    job_out_dir = d
                    break
        if job_out_dir:
            final_candidates = sorted(job_out_dir.glob("final_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if final_candidates:
                final_path = final_candidates[0]
                if is_thumb:
                    thumb_path = final_path.parent / f"{final_path.stem}_thumb.jpg"
                    if not thumb_path.exists():
                        cmd = ["ffmpeg", "-y", "-ss", "1.0", "-i", str(final_path), "-frames:v", "1", "-update", "1", "-q:v", "2", str(thumb_path)]
                        try:
                            await asyncio.to_thread(subprocess.run, cmd, capture_output=True)
                        except Exception:
                            pass
                    if thumb_path.exists():
                        return FileResponse(path=str(thumb_path), media_type="image/jpeg", filename=thumb_path.name, content_disposition_type="inline")
                else:
                    return FileResponse(path=str(final_path), media_type="video/mp4", filename=final_path.name, content_disposition_type="inline")

    # 1. Main A-Roll source video
    if clean_name in ("source", "main", Path(job.source_filename).name):
        if job.source_file and Path(job.source_file).exists():
            return FileResponse(path=str(job.source_file), media_type="video/mp4", filename=clean_name, content_disposition_type="inline")

    # 2. B-roll workspace directory
    broll_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    if broll_dir.exists():
        target = broll_dir / clean_name
        if target.exists():
            return FileResponse(path=str(target), media_type=_infer_mime(clean_name), filename=clean_name, content_disposition_type="inline")
        for f in broll_dir.iterdir():
            if f.is_file() and f.name.startswith(clean_name):
                return FileResponse(path=str(f), media_type=_infer_mime(f.name), filename=f.name, content_disposition_type="inline")

    # 3. SFX or audio in workspace
    sfx_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "sfx"
    if sfx_dir.exists():
        target = sfx_dir / clean_name
        if target.exists():
            return FileResponse(path=str(target), media_type=_infer_mime(clean_name), filename=clean_name, content_disposition_type="inline")

    # 4. Global static SFX
    static_sfx = Path("ai_broll_autopilot/assets/sfx") / clean_name
    if static_sfx.exists():
        return FileResponse(path=str(static_sfx), media_type=_infer_mime(clean_name), filename=clean_name, content_disposition_type="inline")

    # 5. Direct workspace asset
    target = Config.OUTPUT_DIR / "workspace" / job.job_id / clean_name
    if target.exists():
        return FileResponse(path=str(target), media_type=_infer_mime(clean_name), filename=clean_name, content_disposition_type="inline")

    raise HTTPException(status_code=404, detail=f"Asset '{asset_name}' not found for job {job_id}")


@app.get("/api/jobs/{job_id}/export/openreel")
async def export_job_openreel_file(job_id: str):
    """Download OpenReel project bundle (.oreel) for direct opening in OpenReel."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    oreel_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "openreel"
    project_oreel = oreel_dir / f"{job.job_id}.oreel"

    if not project_oreel.exists():
        await get_job_openreel_project(job_id)

    if not project_oreel.exists():
        raise HTTPException(status_code=500, detail="Could not generate OpenReel project file")

    clean_name = Path(job.source_filename).stem
    return FileResponse(
        path=str(project_oreel),
        media_type="application/json",
        filename=f"{clean_name}.oreel",
    )


@app.get("/api/jobs/{job_id}/openreel-manifest")
async def get_job_openreel_manifest(job_id: str):
    """Get project manifest detailing tracks, assets, and OpenReel import instructions."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    manifest_path = Config.OUTPUT_DIR / "workspace" / job.job_id / "openreel" / "project_manifest.json"
    if not manifest_path.exists():
        await get_job_openreel_project(job_id)

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise HTTPException(status_code=404, detail="Manifest not found for job")


@app.get("/api/jobs/{job_id}/qc-report")
async def get_job_qc_report(job_id: str):
    """Audit edit plan and return 5-point Quality Control report (pacing, safe zones, readability, audio)."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    plan_dict = job.edit_plan or {}
    total_dur = plan_dict.get("total_duration") or plan_dict.get("target_duration") or 30.0

    plan_obj = EditPlan(
        plan_id=f"plan_{job.job_id}",
        title=f"Edit: {Path(job.source_filename).stem}",
        target_duration=float(total_dur),
        source_media={"path": job.source_file, "duration": float(total_dur)},
        clip_interval={"in_point": 0.0, "out_point": float(total_dur)},
        niche=plan_dict.get("niche", {}),
        style=plan_dict.get("style", {}),
        shots=plan_dict.get("shots", []),
        text_overlays=plan_dict.get("text_overlays", []),
        subtitles=plan_dict.get("subtitles", []),
        zooms=plan_dict.get("zooms", []),
        audio_cues=plan_dict.get("audio_cues", {}),
    )

    report = edit_quality_service.evaluate_edit_plan(plan_obj)
    return report.to_dict()



@app.delete("/api/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Delete a job and remove its temporary workspace files."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete_job(job_id)
    wk = Config.OUTPUT_DIR / "workspace" / job_id
    if wk.exists():
        try:
            shutil.rmtree(wk)
        except Exception as e:
            logger.warning(f"Could not delete workspace for {job_id}: {e}")

    return {"status": "deleted", "job_id": job_id}


@app.post("/api/jobs/clear")
async def clear_all_jobs_endpoint():
    """Clear all jobs from database and remove workspace temp files."""
    db.clear_all_jobs()
    wk_root = Config.OUTPUT_DIR / "workspace"
    if wk_root.exists():
        for item in wk_root.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                except Exception:
                    pass
    return {"status": "cleared", "message": "All projects cleared successfully"}


@app.post("/api/jobs/upload")
async def upload_video(
    file: UploadFile = File(...),
    campaign_id: Optional[str] = Form("default"),
):
    """Upload a raw video file, save to input/, and enqueue for autopilot processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}:
        raise HTTPException(status_code=400, detail=f"Unsupported video format: {ext}")

    target_file = Config.INPUT_DIR / file.filename
    # Avoid overwriting directly with duplicate name
    if target_file.exists():
        stem = Path(file.filename).stem
        target_file = Config.INPUT_DIR / f"{stem}_{int(asyncio.get_event_loop().time())}{ext}"

    # Write file chunk by chunk
    with open(target_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"Uploaded file saved to: {target_file} (Campaign: {campaign_id})")

    # Enqueue job
    job_id = await orchestrator.enqueue_file(str(target_file), campaign_id=campaign_id or "default")

    return {
        "status": "queued",
        "job_id": job_id,
        "filename": target_file.name,
        "campaign_id": campaign_id or "default",
        "message": f"Successfully uploaded and enqueued {target_file.name}",
    }


@app.post("/api/jobs/youtube")
async def import_youtube_video(req: YouTubeJobRequest):
    """Import a video from YouTube URL, download with yt-dlp, and enqueue for autopilot processing."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    target_campaign = req.campaign_id or "default"
    logger.info(f"Importing YouTube video from URL: {url} (Campaign: {target_campaign})")
    loop = asyncio.get_event_loop()

    def _download_yt():
        import yt_dlp
        import time
        ts = int(time.time())
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(Config.INPUT_DIR / f'%(title).40s_{ts}.%(ext)s'),
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            p = Path(filename)
            if not p.exists() and p.with_suffix('.mp4').exists():
                return p.with_suffix('.mp4')
            return p

    try:
        downloaded_file = await loop.run_in_executor(None, _download_yt)
        if not downloaded_file.exists():
            raise HTTPException(status_code=500, detail="Failed to download YouTube video")

        logger.info(f"YouTube video downloaded to: {downloaded_file}")
        job_id = await orchestrator.enqueue_file(str(downloaded_file), campaign_id=target_campaign)

        return {
            "status": "queued",
            "job_id": job_id,
            "filename": downloaded_file.name,
            "campaign_id": target_campaign,
            "message": f"Successfully imported and enqueued {downloaded_file.name}",
        }
    except Exception as e:
        logger.error(f"Error importing YouTube video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import YouTube video: {str(e)}")


@app.get("/api/campaigns")
async def list_campaigns():
    """List all available clipping campaigns with configuration metadata."""
    from ai_broll_autopilot.campaigns import campaign_registry
    campaigns = campaign_registry.list_campaigns()
    return [c.to_dict() for c in campaigns]


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign_detail(campaign_id: str):
    """Retrieve full details, rules checklist, and curated moments for a specific campaign."""
    from ai_broll_autopilot.campaigns import campaign_registry
    c = campaign_registry.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c.to_dict()


@app.get("/api/campaigns/{campaign_id}/moments")
async def get_campaign_moments(campaign_id: str):
    """Retrieve pre-curated timestamped moments for a campaign."""
    from ai_broll_autopilot.campaigns import campaign_registry
    c = campaign_registry.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return [
        {
            "moment_id": m.moment_id,
            "timestamp_range": m.timestamp_range,
            "start_time_sec": m.start_time_sec,
            "end_time_sec": m.end_time_sec,
            "screen_hook": m.screen_hook,
            "post_caption": m.post_caption,
            "broll_theme": m.broll_theme,
            "broll_sources": m.broll_sources,
            "angle": m.angle,
        }
        for m in c.curated_moments
    ]


@app.post("/api/feedback")
async def submit_feedback(fb: FeedbackRequest):
    """Submit user emotional rating & feedback to the persistent Learning Engine."""
    # Find clip title from job if available
    job = db.get_job(fb.job_id)
    title = job.source_filename if job else "Unknown Video"

    learning_engine.record_job_feedback(
        job_id=fb.job_id,
        user_rating=fb.rating,
        feedback_text=fb.feedback,
        shot_id=fb.shot_id,
        clip_title=title,
        emotional_score=fb.rating,
        thematic_category=fb.thematic_category or "General",
        preferred_metaphor=fb.preferred_metaphor,
        avoided_metaphor=fb.avoided_metaphor,
    )

    return {
        "status": "success",
        "message": "Feedback recorded. Future B-roll selections will learn from this rating.",
    }


@app.get("/api/learning")
async def get_learning_rules():
    """Retrieve all active learned rules and preferences."""
    rules = learning_engine.get_active_rules()
    return rules


@app.get("/api/drive/status")
async def get_drive_status():
    """Get Google Drive connection status and configuration."""
    return drive_sync_service.get_status()


@app.post("/api/drive/sync")
async def sync_google_drive(background_tasks: BackgroundTasks):
    """Trigger inbound sync to download any newly dropped clips from Google Drive."""
    status = drive_sync_service.get_status()
    if not status["has_credentials"]:
        return {
            "status": "simulated",
            "message": "Google Drive credentials not configured. Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable live cloud sync.",
            "downloaded": []
        }

    downloaded = await drive_sync_service.pull_new_inputs()
    # Enqueue any downloaded files
    enqueued_jobs = []
    for item in downloaded:
        jid = await orchestrator.enqueue_file(item["local_path"])
        enqueued_jobs.append(jid)

    return {
        "status": "success",
        "downloaded_count": len(downloaded),
        "enqueued_jobs": enqueued_jobs,
    }


@app.get("/api/memes/templates")
async def list_meme_templates(q: Optional[str] = None, limit: int = 80):
    """List or search HD meme templates from the 1,000+ template library with archetype ranking."""
    import urllib.parse
    from ai_broll_autopilot.services.meme_engine import MemeEngine
    engine = MemeEngine()

    featured_archetypes = [
        {
            "key": "ishowspeed_shock",
            "name": "⚡ IShowSpeed (Screaming Shock & Hype)",
            "category": "Viral Streamers & Creators",
            "description": "Darren Watkins Jr barking & wide-eyed screaming - captures #1 viewer retention",
            "fields": [
                {"name": "caption", "label": "Speed Reaction Caption (Optional)", "placeholder": "WHEN BRO ACTUALLY DID IT..."}
            ]
        },
        {
            "key": "caseoh_rage",
            "name": "🎙️ CaseOh (Headset Mic Rage)",
            "category": "Viral Streamers & Creators",
            "description": "Furious mic-blast scream & chat spam - unhinged reaction for bad takes or roasting",
            "fields": [
                {"name": "caption", "label": "CaseOh Rage Caption (Optional)", "placeholder": "MODS, BAN THIS GUY IMMEDIATELY"}
            ]
        },
        {
            "key": "jynxzi_freakout",
            "name": "🎮 Jynxzi (Controller Slam & Disbelief)",
            "category": "Viral Streamers & Creators",
            "description": "Glasses, headset, controller disbelief scream - viral reaction for shock and absurdity",
            "fields": [
                {"name": "caption", "label": "Jynxzi Reaction Caption (Optional)", "placeholder": "BRO JUST WITNESSED A MIRACLE"}
            ]
        },
        {
            "key": "moms_kinda_homeless",
            "name": "🥺 My Mom's Kinda Homeless (Speed Fortnite)",
            "category": "Viral Streamers & Creators",
            "description": "Desperate Fortnite kid pleading 'My mom is kinda homeless' while streamer struggles not to laugh",
            "fields": [
                {"name": "caption", "label": "Desperate Plea Caption (Optional)", "placeholder": "BRO PLEASE I NEED THIS..."}
            ]
        },
        {
            "key": "not_your_personal_pornstar",
            "name": "🤬 Not Your Personal Pornstar! (Public Meltdown)",
            "category": "Viral Streamers & Creators",
            "description": "Unhinged street screaming after chat asked 'did you shave?' - guaranteed comment section meltdown bait",
            "fields": [
                {"name": "caption", "label": "Rage Caption (Optional)", "placeholder": "SHUT THE F*** UP!"}
            ]
        },
        {
            "key": "the_trusted_doctor",
            "name": "The Trusted Specialist (IYKYK)",
            "category": "IYKYK Pop-Culture Troll",
            "description": "The world's most qualified doctor & specialist - guaranteed comment section bait",
            "fields": [
                {"name": "caption", "label": "Caption / Meme Subtext", "placeholder": "The specialist she told you not to worry about..."}
            ]
        },
        {
            "key": "gigachad",
            "name": "Gigachad (Absolute Legend)",
            "category": "IYKYK Pop-Culture Troll",
            "description": "Ultra-masculine jawline Chad - peak masculine discipline & winner mindset",
            "fields": [
                {"name": "caption", "label": "Chad Statement", "placeholder": "Average consistency enjoyer"}
            ]
        },
        {
            "key": "hide_the_pain_harold",
            "name": "Hide The Pain Harold",
            "category": "IYKYK Pop-Culture Troll",
            "description": "Strained coffee smile - smiling through the inner panic",
            "fields": [
                {"name": "caption", "label": "Harold Reaction", "placeholder": "When they ask how the project is going"}
            ]
        },
        {
            "key": "stepped_in_shit",
            "name": "Ew, I Stepped In Shit",
            "category": "Bad Opinions & Terrible Takes",
            "description": "Text rendered dynamically on shoe sole angled at 38°",
            "fields": [
                {"name": "shoe_text", "label": "Shoe Sole Text (Bad Opinion / Distraction)", "placeholder": "Distractions, bad advice, terrible take..."}
            ]
        },
        {
            "key": "drake",
            "name": "Drake Hotline Bling",
            "category": "Rejection vs Acceptance",
            "description": "Top panel rejected, bottom panel accepted",
            "fields": [
                {"name": "top_text", "label": "Top (Rejected / Bad Habit)", "placeholder": "Doomscrolling, giving up, excuses..."},
                {"name": "bottom_text", "label": "Bottom (Accepted / Winner Habit)", "placeholder": "Staying focused, hard work..."}
            ]
        },
        {
            "key": "clown",
            "name": "Clown Makeup",
            "category": "Progressive Bad Logic",
            "description": "4-stage escalation into full clown logic",
            "fields": [
                {"name": "step_1", "label": "Stage 1", "placeholder": "I will start tomorrow"},
                {"name": "step_2", "label": "Stage 2", "placeholder": "I just need inspiration first"},
                {"name": "step_3", "label": "Stage 3", "placeholder": "It's too late anyway"},
                {"name": "step_4", "label": "Stage 4", "placeholder": "Why am I not succeeding?"}
            ]
        },
        {
            "key": "same_picture",
            "name": "They're The Same Picture",
            "category": "Corporate Comparison",
            "description": "Pam Beesly comparing two identically flawed things",
            "fields": [
                {"name": "item_1", "label": "Left Picture", "placeholder": "Procrastination"},
                {"name": "item_2", "label": "Right Picture", "placeholder": "Self-sabotage"}
            ]
        },
        {
            "key": "batman_slap",
            "name": "Batman Slapping Robin",
            "category": "Shutting Down Excuses",
            "description": "Batman smacking down Robin's foolish complaint",
            "fields": [
                {"name": "caption", "label": "Excuse Being Slapped", "placeholder": "Shut up and execute!"}
            ]
        },
        {
            "key": "blinking_guy",
            "name": "Blinking White Guy",
            "category": "Disbelief & Shock",
            "description": "Drew Scanlon shocked reaction",
            "fields": [
                {"name": "caption", "label": "Shocking Realization", "placeholder": "When they said focus doesn't matter"}
            ]
        },
        {
            "key": "gta_ah_shit",
            "name": "GTA: Ah Shit Here We Go Again",
            "category": "Relapse & Repeat Mistakes",
            "description": "CJ walking down the alley",
            "fields": [
                {"name": "caption", "label": "Caption", "placeholder": "Opening social media again"}
            ]
        }
    ]

    results = []
    q_clean = q.lower().strip() if q else None

    # First add matching featured archetypes
    for feat in featured_archetypes:
        if not q_clean or q_clean in feat["key"] or q_clean in feat["name"].lower() or q_clean in feat["category"].lower():
            found = engine.find_template(feat["key"])
            filename = found[1].name if found else feat["name"]
            results.append({
                "key": feat["key"],
                "name": feat["name"],
                "filename": filename,
                "category": feat["category"],
                "description": feat["description"],
                "is_featured": True,
                "preview_url": f"/api/memes/templates/{urllib.parse.quote(feat['key'])}/preview",
                "fields": feat["fields"]
            })

    # Then append other templates from catalog up to limit
    for key, path in engine.catalog.items():
        if len(results) >= limit:
            break
        if any(r["key"] == key for r in results):
            continue
        if q_clean and q_clean not in key and q_clean not in path.name.lower():
            continue

        clean_name = path.stem.replace("_", " ").title()
        results.append({
            "key": key,
            "name": clean_name[:40],
            "filename": path.name,
            "category": "HD Meme Template",
            "description": "Classic viral meme template",
            "is_featured": False,
            "preview_url": f"/api/memes/templates/{urllib.parse.quote(key)}/preview",
            "fields": [
                {"name": "caption", "label": "Meme Caption", "placeholder": "Enter punchline or quote..."}
            ]
        })

    return results


@app.get("/api/memes/templates/{template_key}/preview")
async def get_meme_template_preview(template_key: str):
    """Serve a preview image for a specific meme template."""
    import urllib.parse
    raw_key = urllib.parse.unquote(template_key)
    from ai_broll_autopilot.services.meme_engine import MemeEngine
    engine = MemeEngine()

    found = engine.find_template(raw_key)
    if not found:
        if raw_key in engine.catalog:
            p = engine.catalog[raw_key]
        else:
            raise HTTPException(status_code=404, detail=f"Template '{raw_key}' not found")
    else:
        _, p = found

    media_type = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path=str(p), media_type=media_type)


@app.post("/api/memes/render")
async def render_standalone_meme(req: MemeGenerateRequest):
    """Render a standalone meme cutaway image and 9:16 vertical video with punchline SFX."""
    import time
    from ai_broll_autopilot.services.meme_engine import MemeEngine
    engine = MemeEngine()
    work_dir = Config.OUTPUT_DIR / "workspace" / "standalone_memes"
    work_dir.mkdir(parents=True, exist_ok=True)

    shot_id = f"meme_{int(time.time() * 1000)}"
    shot = {
        "shot_id": shot_id,
        "style": "meme",
        "meme_template": req.template_key,
        "meme_captions": req.captions,
        "duration": req.duration
    }
    if req.sfx_file:
        sfx_path = None
        for item in engine.sfx_catalog:
            if item.get("file") == req.sfx_file or Path(item.get("path", "")).name == req.sfx_file:
                sfx_path = item["path"]
                break
        if sfx_path and os.path.exists(sfx_path):
            shot["contextual_sfx"] = {
                "name": req.sfx_file,
                "file": req.sfx_file,
                "path": sfx_path,
                "category": "Meme Stinger",
                "volume": 0.50,
                "start_offset": 0.05,
                "reason": f"Punchline SFX for {req.template_key}"
            }

    rendered_shot = engine.create_meme_broll(shot, work_dir, duration=req.duration)
    v_path = Path(rendered_shot["asset_path"])
    img_path = v_path.with_suffix(".jpg")

    return {
        "status": "success",
        "shot_id": shot_id,
        "template_resolved": rendered_shot.get("meme_template_resolved"),
        "video_url": f"/api/memes/preview/{v_path.name}",
        "image_url": f"/api/memes/preview/{img_path.name}" if img_path.exists() else None,
        "contextual_sfx": rendered_shot.get("contextual_sfx")
    }


@app.get("/api/memes/preview/{filename}")
async def get_meme_preview_file(filename: str):
    """Serve a preview file for a generated standalone meme."""
    p = Config.OUTPUT_DIR / "workspace" / "standalone_memes" / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Preview file not found")
    media_type = "video/mp4" if p.suffix.lower() == ".mp4" else "image/jpeg"
    return FileResponse(path=str(p), media_type=media_type)


@app.post("/api/jobs/{job_id}/shots/{shot_id}/meme")
async def update_shot_to_meme(job_id: str, shot_id: str, req: ShotMemeRequest):
    """Transform or customize an existing shot in a job into a meme cutaway."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.edit_plan or not isinstance(job.edit_plan, dict) or "shots" not in job.edit_plan:
        raise HTTPException(status_code=400, detail="Job has no edit plan")

    target_shot = None
    for s in job.edit_plan["shots"]:
        if s.get("shot_id") == shot_id:
            target_shot = s
            break

    if not target_shot:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found in job")

    from ai_broll_autopilot.services.meme_engine import MemeEngine
    engine = MemeEngine()
    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    work_dir.mkdir(parents=True, exist_ok=True)

    dur = float(req.duration or target_shot.get("duration", (target_shot.get("end_time", 3.0) - target_shot.get("start_time", 0.0))))

    target_shot["style"] = "meme"
    target_shot["meme_template"] = req.template_key
    target_shot["meme_captions"] = req.captions
    target_shot["duration"] = dur

    if req.sfx_file:
        sfx_path = None
        for item in engine.sfx_catalog:
            if item.get("file") == req.sfx_file or Path(item.get("path", "")).name == req.sfx_file:
                sfx_path = item["path"]
                break
        if sfx_path and os.path.exists(sfx_path):
            target_shot["contextual_sfx"] = {
                "name": req.sfx_file,
                "file": req.sfx_file,
                "path": sfx_path,
                "category": "Meme Stinger",
                "volume": 0.50,
                "start_offset": 0.05,
                "reason": f"Punchline SFX for {req.template_key}"
            }

    updated_shot = engine.create_meme_broll(target_shot, work_dir, duration=dur)
    db.save_job(job)

    # Attach preview URLs
    sc = dict(updated_shot)
    sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}"
    sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}/thumb"
    if sc.get("contextual_sfx") and "file" in sc["contextual_sfx"]:
        sc["contextual_sfx"]["audio_url"] = f"/api/sfx/{sc['contextual_sfx']['file']}"

    return {
        "status": "success",
        "job_id": job_id,
        "shot": sc
    }


@app.post("/api/jobs/{job_id}/shots/{shot_id}/auto-meme")
async def auto_generate_shot_meme(job_id: str, shot_id: str):
    """Autonomously analyze dialogue and generate a 100% unique meme cutaway tailored to this shot."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.edit_plan or not isinstance(job.edit_plan, dict) or "shots" not in job.edit_plan:
        raise HTTPException(status_code=400, detail="Job has no edit plan")

    target_shot = None
    for s in job.edit_plan["shots"]:
        if s.get("shot_id") == shot_id:
            target_shot = s
            break

    if not target_shot:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found in job")

    from ai_broll_autopilot.services.meme_engine import MemeEngine
    engine = MemeEngine()
    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    work_dir.mkdir(parents=True, exist_ok=True)

    dur = float(target_shot.get("duration", (target_shot.get("end_time", 3.0) - target_shot.get("start_time", 0.0))))

    # Automatically generate 100% unique meme archetype and witty captions for this shot
    full_context = job.transcript_text or ""
    target_shot["style"] = "meme"
    target_shot = engine.generate_unique_contextual_meme(target_shot, full_context)
    target_shot["duration"] = dur

    updated_shot = engine.create_meme_broll(target_shot, work_dir, duration=dur)
    db.save_job(job)

    # Attach preview URLs
    sc = dict(updated_shot)
    sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}"
    sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}/thumb"
    if sc.get("contextual_sfx") and "file" in sc["contextual_sfx"]:
        sc["contextual_sfx"]["audio_url"] = f"/api/sfx/{sc['contextual_sfx']['file']}"

    return {
        "status": "success",
        "job_id": job_id,
        "shot": sc
    }


# =========================================================================
# Editor Refinement Endpoints: Stock Search, Swap, Trim, Insert, BGM & Subs
# =========================================================================

@app.get("/api/stock/search")
async def search_stock_footage(query: str, per_page: int = 6, orientation: str = "portrait"):
    """Search Pexels API for vertical stock videos to swap in the editor."""
    if not query.strip():
        return []
    return await pexels_service.search_candidates(query=query.strip(), per_page=per_page, orientation=orientation)


@app.post("/api/jobs/{job_id}/shots/{shot_id}/swap-stock")
async def swap_shot_stock_footage(job_id: str, shot_id: str, req: StockSwapRequest):
    """Replace an existing shot's video asset with a chosen Pexels candidate or prompt."""
    job = db.get_job(job_id)
    if not job or not job.edit_plan or "shots" not in job.edit_plan:
        raise HTTPException(status_code=404, detail="Job or edit plan not found")

    target_shot = next((s for s in job.edit_plan["shots"] if s.get("shot_id") == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found")

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    work_dir.mkdir(parents=True, exist_ok=True)
    out_file = work_dir / f"{shot_id}_pexels_swap.mp4"
    target_dur = float(target_shot.get("duration") or (target_shot.get("end_time", 3.0) - target_shot.get("start_time", 0.0)))

    new_asset = None
    if req.download_url:
        new_asset = await pexels_service.download_candidate(req.download_url, out_file, duration=target_dur)
    elif req.prompt:
        new_asset = await pexels_service.search_and_download(req.prompt, out_file, duration=target_dur, orientation="portrait")

    if not new_asset or not Path(new_asset).exists():
        raise HTTPException(status_code=500, detail="Failed to acquire selected stock footage")

    target_shot["asset_path"] = str(Path(new_asset).resolve())
    target_shot["style"] = "stockpile"
    target_shot["search_prompt"] = req.prompt or target_shot.get("search_prompt", "stock video")
    target_shot["status"] = "matched"
    db.save_job(job)

    sc = dict(target_shot)
    sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}"
    sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}/thumb"
    return {"status": "success", "shot": sc}


@app.post("/api/jobs/{job_id}/shots/{shot_id}/upload-custom")
async def upload_custom_shot_clip(job_id: str, shot_id: str, file: UploadFile = File(...)):
    """Upload a custom video file from local disk to replace a shot's B-roll footage."""
    job = db.get_job(job_id)
    if not job or not job.edit_plan or "shots" not in job.edit_plan:
        raise HTTPException(status_code=404, detail="Job or edit plan not found")

    target_shot = next((s for s in job.edit_plan["shots"] if s.get("shot_id") == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found")

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    work_dir.mkdir(parents=True, exist_ok=True)
    raw_custom = work_dir / f"raw_custom_{shot_id}_{file.filename}"
    out_file = work_dir / f"{shot_id}_custom.mp4"

    with open(raw_custom, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    target_dur = float(target_shot.get("duration") or (target_shot.get("end_time", 3.0) - target_shot.get("start_time", 0.0)))
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(raw_custom),
        "-t", f"{target_dur:.2f}",
        "-vf", f"scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={Config.TARGET_FPS}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(Config.VIDEO_CRF),
        "-pix_fmt", "yuv420p", "-an", "-v", "warning",
        str(out_file)
    ]
    res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f"FFmpeg custom clip format error: {res.stderr}")
    raw_custom.unlink(missing_ok=True)

    if not out_file.exists():
        raise HTTPException(status_code=500, detail="Failed to format uploaded custom video clip")

    target_shot["asset_path"] = str(out_file.resolve())
    target_shot["style"] = "custom_upload"
    target_shot["search_prompt"] = file.filename
    target_shot["status"] = "matched"
    db.save_job(job)

    sc = dict(target_shot)
    sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}"
    sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{shot_id}/thumb"
    return {"status": "success", "shot": sc}


@app.patch("/api/jobs/{job_id}/shots/{shot_id}")
async def trim_shot_timeline(job_id: str, shot_id: str, req: ShotTrimRequest):
    """Trim and adjust the start and end boundary timestamps of a shot."""
    job = db.get_job(job_id)
    if not job or not job.edit_plan or "shots" not in job.edit_plan:
        raise HTTPException(status_code=404, detail="Job or edit plan not found")

    target_shot = next((s for s in job.edit_plan["shots"] if s.get("shot_id") == shot_id), None)
    if not target_shot:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found")

    st = round(max(0.0, float(req.start_time)), 2)
    et = round(float(req.end_time), 2)
    if et <= st + 0.3:
        raise HTTPException(status_code=400, detail="End time must be at least 0.3s after start time")

    target_shot["start_time"] = st
    target_shot["end_time"] = et
    target_shot["duration"] = round(et - st, 2)

    # Re-sort shots by start time
    job.edit_plan["shots"].sort(key=lambda s: float(s.get("start_time", 0.0)))
    db.save_job(job)

    return {"status": "success", "shot": target_shot, "shots": job.edit_plan["shots"]}


@app.post("/api/jobs/{job_id}/shots")
async def insert_new_cutaway_shot(job_id: str, req: ShotInsertRequest):
    """Insert a new B-roll or Meme cutaway shot at the specified timeline timestamp."""
    job = db.get_job(job_id)
    if not job or not job.edit_plan:
        raise HTTPException(status_code=404, detail="Job not found")

    if "shots" not in job.edit_plan:
        job.edit_plan["shots"] = []

    st = round(max(0.0, float(req.start_time)), 2)
    dur = round(max(1.0, min(10.0, float(req.duration))), 2)
    et = round(st + dur, 2)
    new_id = f"cutaway_{int(asyncio.get_event_loop().time() * 1000) % 100000}"

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id / "broll"
    work_dir.mkdir(parents=True, exist_ok=True)

    new_shot = {
        "shot_id": new_id,
        "start_time": st,
        "end_time": et,
        "duration": dur,
        "style": req.style,
        "dialogue_quote": req.dialogue_quote or "",
        "search_prompt": req.search_prompt or "focused professional",
        "emotional_core": "Added Highlight",
        "visceral_human_metaphor": "Manual timeline insertion",
        "overlay_type": "cutaway",
        "status": "pending"
    }

    if req.style == "meme":
        from ai_broll_autopilot.services.meme_engine import MemeEngine
        m_engine = MemeEngine()
        new_shot["meme_template"] = req.meme_template or "stepped_in_shit"
        new_shot["meme_captions"] = {"caption": req.dialogue_quote or "Point of emphasis"}
        new_shot = m_engine.create_meme_broll(new_shot, work_dir, duration=dur)
    else:
        # Search and download standard Pexels footage
        p_out = work_dir / f"{new_id}_pexels.mp4"
        asset = await pexels_service.search_and_download(new_shot["search_prompt"], p_out, duration=dur, orientation="portrait")
        if asset and Path(asset).exists():
            new_shot["asset_path"] = str(Path(asset).resolve())
            new_shot["status"] = "matched"

    job.edit_plan["shots"].append(new_shot)
    job.edit_plan["shots"].sort(key=lambda s: float(s.get("start_time", 0.0)))
    db.save_job(job)

    sc = dict(new_shot)
    sc["video_url"] = f"/api/jobs/{job.job_id}/broll/{new_id}"
    sc["thumbnail_url"] = f"/api/jobs/{job.job_id}/broll/{new_id}/thumb"
    return {"status": "success", "shot": sc, "shots": job.edit_plan["shots"]}


@app.delete("/api/jobs/{job_id}/shots/{shot_id}")
async def delete_cutaway_shot(job_id: str, shot_id: str):
    """Delete a specific cutaway shot from the job edit plan."""
    job = db.get_job(job_id)
    if not job or not job.edit_plan or "shots" not in job.edit_plan:
        raise HTTPException(status_code=404, detail="Job or edit plan not found")

    initial_len = len(job.edit_plan["shots"])
    job.edit_plan["shots"] = [s for s in job.edit_plan["shots"] if s.get("shot_id") != shot_id]

    if len(job.edit_plan["shots"]) == initial_len:
        raise HTTPException(status_code=404, detail=f"Shot '{shot_id}' not found")

    db.save_job(job)
    return {"status": "deleted", "shot_id": shot_id, "remaining_count": len(job.edit_plan["shots"])}


@app.get("/api/bgm/tracks")
async def get_bgm_tracks():
    """List all available royalty-free background music tracks."""
    from ai_broll_autopilot.services.bgm_engine import BGMEngine
    engine = BGMEngine()
    return engine.list_tracks()


@app.get("/api/bgm/{track_id}/audio")
async def get_bgm_track_audio(track_id: str):
    """Stream audio preview for a specific background music track."""
    from ai_broll_autopilot.services.bgm_engine import BGMEngine
    engine = BGMEngine()
    p = engine.get_track_path(track_id)
    if not p or not p.exists():
        raise HTTPException(status_code=404, detail=f"BGM track '{track_id}' not found")
    media_type = "audio/mpeg" if p.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(path=str(p), media_type=media_type, filename=p.name)


@app.post("/api/jobs/{job_id}/settings")
async def update_job_render_settings(job_id: str, req: JobSettingsRequest):
    """Update subtitle formatting and background music settings for a job."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.edit_plan:
        job.edit_plan = {"shots": []}

    settings = job.edit_plan.get("render_settings", {})
    if req.subtitles_enabled is not None:
        settings["subtitles_enabled"] = req.subtitles_enabled
    if req.subtitle_style is not None:
        settings["subtitle_style"] = req.subtitle_style
    if req.subtitle_position is not None:
        settings["subtitle_position"] = req.subtitle_position
    if req.bgm_track_id is not None:
        settings["bgm_track_id"] = req.bgm_track_id if req.bgm_track_id != "none" else None
    if req.bgm_volume is not None:
        settings["bgm_volume"] = req.bgm_volume
    if req.bgm_ducking is not None:
        settings["bgm_ducking"] = req.bgm_ducking

    if req.hdr_upscale_enabled is not None:
        settings["hdr_upscale_enabled"] = req.hdr_upscale_enabled
    if req.hdr_output_scale is not None:
        settings["hdr_output_scale"] = req.hdr_output_scale
    if req.hdr_tone is not None:
        settings["hdr_tone"] = req.hdr_tone

    job.edit_plan["render_settings"] = settings
    db.save_job(job)
    return {"status": "success", "render_settings": settings}


@app.post("/api/jobs/{job_id}/rerender")
async def rerender_job_video(job_id: str):
    """Re-render the master composite video with updated shots, kinetic subtitles, and BGM auto-ducking."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.edit_plan or "shots" not in job.edit_plan:
        raise HTTPException(status_code=400, detail="Job has no edit plan")

    from ai_broll_autopilot.services.renderer import Renderer
    from ai_broll_autopilot.services.transition_engine import TransitionEngine
    from ai_broll_autopilot.services.subtitle_engine import SubtitleEngine
    from ai_broll_autopilot.services.bgm_engine import BGMEngine

    renderer = Renderer()
    trans_engine = TransitionEngine()
    sub_engine = SubtitleEngine()
    bgm_engine = BGMEngine()

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    rendered_video = work_dir / f"rendered_{job.source_filename}"

    raw_shots = job.edit_plan.get("shots", [])

    # Compulsory check: ensure Shot 1 (first 5 seconds) is a meme cutaway and has a valid rendered video asset
    from ai_broll_autopilot.services.meme_engine import MemeEngine
    meme_engine = MemeEngine()
    if raw_shots:
        shot_0 = raw_shots[0]
        curr_p = str(shot_0.get("asset_path", "")).lower()
        if shot_0.get("style") != "meme" or not curr_p or "pexels" in curr_p or not os.path.exists(shot_0.get("asset_path", "")):
            logger.info(f"Rerender enforcing compulsory first 5s meme on [{shot_0.get('shot_id')}]...")
            shot_0["style"] = "meme"
            if float(shot_0.get("start_time", 0)) > 2.0:
                shot_0["start_time"] = 1.2
            shot_0["duration"] = min(2.2, max(1.5, float(shot_0.get("duration", 2.0))))
            shot_0["end_time"] = round(shot_0["start_time"] + shot_0["duration"], 2)
            shot_0 = MemeEngine.generate_unique_contextual_meme(shot_0, job.transcript_text or "", client=None)
            shot_0 = meme_engine.create_meme_broll(shot_0, work_dir, duration=shot_0.get("duration", 2.0))
            raw_shots[0] = shot_0
            logger.info(f"Compulsory first 5s meme rendered: {shot_0.get('asset_path')}")

    # Also guarantee any other meme shot in the plan has its video asset rendered
    for idx, s in enumerate(raw_shots):
        if s.get("style") == "meme":
            s_asset = s.get("asset_path")
            if not s_asset or not os.path.exists(s_asset) or "pexels" in str(s_asset).lower():
                s = meme_engine.create_meme_broll(s, work_dir, duration=s.get("duration", 2.0))
                raw_shots[idx] = s

    # Plan transitions and stingers for shots
    shots = await trans_engine.plan_transitions(raw_shots)
    job.edit_plan["shots"] = shots
    db.save_job(job)

    settings = job.edit_plan.get("render_settings", {})
    sub_enabled = settings.get("subtitles_enabled", True)
    sub_style = settings.get("subtitle_style", "hormozi")
    sub_pos = settings.get("subtitle_position", "bottom")

    ass_path = None
    if sub_enabled and job.transcript_segments:
        try:
            ass_dest = work_dir / "subtitles_kinetic.ass"
            sub_engine.generate_ass_file(
                segments=job.transcript_segments,
                output_path=ass_dest,
                style_preset=sub_style,
                position=sub_pos
            )
            if ass_dest.exists():
                ass_path = str(ass_dest.resolve())
        except Exception as se:
            logger.warning(f"Could not generate kinetic subtitles: {se}")

    # Resolve BGM track
    bgm_track_id = settings.get("bgm_track_id")
    bgm_path = None
    bgm_vol = float(settings.get("bgm_volume", 0.15))
    ducking = bool(settings.get("bgm_ducking", True))
    if bgm_track_id:
        p = bgm_engine.get_track_path(bgm_track_id)
        if p and p.exists():
            bgm_path = str(p.resolve())

    hdr_enabled = bool(settings.get("hdr_upscale_enabled", False))
    hdr_scale = float(settings.get("hdr_output_scale", 1.0))
    hdr_tone = str(settings.get("hdr_tone", "vivid"))

    out_path = await renderer.render(
        base_video=job.source_file,
        edit_plan=job.edit_plan,
        output_path=str(rendered_video),
        ass_subtitles_path=ass_path,
        bgm_path=bgm_path,
        bgm_volume=bgm_vol,
        ducking_enabled=ducking,
        upscale_hdr=hdr_enabled,
        hdr_scale=hdr_scale,
        hdr_tone=hdr_tone
    )

    # Also update final output video if exists
    if job.output_video_path:
        final_dest = Path(job.output_video_path)
        final_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, final_dest)

    db.save_job(job)
    return {
        "status": "success",
        "job_id": job_id,
        "video_url": f"/api/jobs/{job_id}/video",
        "file_size": Path(out_path).stat().st_size,
        "subtitles_burned": bool(ass_path),
        "bgm_applied": bool(bgm_path),
        "hdr_enabled": hdr_enabled
    }


@app.post("/api/jobs/{job_id}/upscale-hdr")
async def start_job_hdr_upscale(job_id: str, req: HdrUpscaleRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous SDR2HDR upscaling and HDR10 conversion for a job's master video."""
    import time
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
    candidate_video = work_dir / f"rendered_{job.source_filename}"
    if not candidate_video.exists() and job.output_video_path and Path(job.output_video_path).exists():
        candidate_video = Path(job.output_video_path)

    if not candidate_video.exists():
        raise HTTPException(status_code=400, detail="Master video has not been rendered yet")

    hdr_out = work_dir / f"rendered_{Path(job.source_filename).stem}_hdr10.mp4"

    hdr_tasks[job_id] = {
        "status": "converting",
        "progress": 0.0,
        "processed_frames": 0,
        "total_frames": 0,
        "fps": 0.0,
        "error": None,
        "output_path": str(hdr_out),
        "output_url": f"/api/jobs/{job_id}/hdr-video",
        "started_at": time.time(),
        "metadata": None,
    }

    def _run_hdr_job():
        try:
            from ai_broll_autopilot.services.sdr2hdr_service import SDR2HDREngine
            engine = SDR2HDREngine()

            def _on_progress(processed, total, fps):
                pct = round((processed / max(total, 1)) * 100, 1)
                hdr_tasks[job_id]["progress"] = pct
                hdr_tasks[job_id]["processed_frames"] = processed
                hdr_tasks[job_id]["total_frames"] = total
                hdr_tasks[job_id]["fps"] = round(fps, 2)

            res = engine.convert_and_upscale(
                input_path=str(candidate_video),
                output_path=str(hdr_out),
                output_scale=req.output_scale or 1.0,
                tone=req.tone or "vivid",
                hdr_style=req.hdr_style or "natural",
                fast_mode=req.fast_mode,
                processing_scale=Config.HDR_PROCESSING_SCALE,
                progress_callback=_on_progress,
            )

            hdr_tasks[job_id]["status"] = "completed"
            hdr_tasks[job_id]["progress"] = 100.0
            hdr_tasks[job_id]["metadata"] = res.get("metadata", {})

            # Persist HDR info into job edit_plan
            j = db.get_job(job_id)
            if j:
                if not j.edit_plan:
                    j.edit_plan = {}
                j.edit_plan["hdr_output"] = {
                    "path": str(hdr_out),
                    "url": f"/api/jobs/{job_id}/hdr-video",
                    "metadata": res.get("metadata", {})
                }
                db.save_job(j)

        except Exception as e:
            logger.error(f"SDR2HDR upscale failed for job {job_id}: {e}")
            hdr_tasks[job_id]["status"] = "error"
            hdr_tasks[job_id]["error"] = str(e)

    background_tasks.add_task(_run_hdr_job)
    return {"status": "started", "job_id": job_id, "output_url": f"/api/jobs/{job_id}/hdr-video"}


@app.get("/api/jobs/{job_id}/hdr-status")
async def get_job_hdr_status(job_id: str):
    """Get real-time SDR2HDR upscaling status, progress %, and stream URL."""
    task = hdr_tasks.get(job_id)
    if task:
        return task

    # Check if already completed and persisted
    job = db.get_job(job_id)
    if job and job.edit_plan and "hdr_output" in job.edit_plan:
        hdr_info = job.edit_plan["hdr_output"]
        p = Path(hdr_info.get("path", ""))
        if p.exists():
            return {
                "status": "completed",
                "progress": 100.0,
                "output_url": f"/api/jobs/{job_id}/hdr-video",
                "output_path": str(p),
                "metadata": hdr_info.get("metadata", {})
            }

    return {"status": "idle", "progress": 0.0}


@app.get("/api/jobs/{job_id}/hdr-video")
async def stream_job_hdr_video(job_id: str):
    """Stream the 10-bit Rec.2020 HDR10 video with native range requests."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
    hdr_path = work_dir / f"rendered_{Path(job.source_filename).stem}_hdr10.mp4"

    if not hdr_path.exists():
        if job.edit_plan and "hdr_output" in job.edit_plan:
            cand = Path(job.edit_plan["hdr_output"].get("path", ""))
            if cand.exists():
                hdr_path = cand

    if not hdr_path.exists():
        raise HTTPException(status_code=404, detail="HDR video not found. Run HDR upscaling first.")

    return FileResponse(
        path=str(hdr_path),
        media_type="video/mp4",
        filename=hdr_path.name,
        headers={"Accept-Ranges": "bytes"}
    )


@app.get("/api/sfx-catalog")
async def get_sfx_catalog():
    """Retrieve catalog of all 189 available sound effects and stingers."""
    catalog_path = Config.OUTPUT_DIR / "split_sfx" / "sfx_catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# STOCKPILE → OPENREEL INTELLIGENCE & EDIT PLANNING ENDPOINTS
# =====================================================================

class NicheAnalyzeRequest(BaseModel):
    transcript_text: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DetectClipsRequest(BaseModel):
    transcript_segments: List[Dict[str, Any]]
    video_duration: float
    target_clip_count: Optional[int] = 5
    min_duration: Optional[float] = 25.0
    max_duration: Optional[float] = 75.0
    niche_id: Optional[str] = None


class PlanEditRequest(BaseModel):
    source_media: Dict[str, Any]
    transcript_segments: List[Dict[str, Any]]
    clip_candidate: Optional[Dict[str, Any]] = None
    in_point: Optional[float] = None
    out_point: Optional[float] = None
    niche_id: Optional[str] = None
    style_id: Optional[str] = None
    custom_hook: Optional[str] = None


class ExportOpenReelRequest(BaseModel):
    edit_plan: Dict[str, Any]
    project_name: Optional[str] = None
    output_folder: Optional[str] = None
    resolved_broll_map: Optional[Dict[str, str]] = None


class LibraryIndexRequest(BaseModel):
    directory_path: str
    niche_id: Optional[str] = None
    tags: Optional[List[str]] = None


@app.get("/api/niches")
async def get_niches():
    """Retrieve all available content niche profiles."""
    return [p.to_dict() for p in niche_registry.list_profiles()]


@app.get("/api/styles")
async def get_styles():
    """Retrieve all available visual style profiles for OpenReel."""
    return [s.to_dict() for s in style_registry.list_styles()]


@app.post("/api/analyze-niche")
async def analyze_niche_endpoint(req: NicheAnalyzeRequest):
    """Classify video content into a content niche and extract structural understanding."""
    res = await niche_detector.detect_niche(
        transcript_text=req.transcript_text,
        title=req.title,
        metadata=req.metadata,
    )
    return res.to_dict()


@app.post("/api/detect-clips")
async def detect_clips_endpoint(req: DetectClipsRequest):
    """Extract viral short clips from long-form content using 9-factor scoring."""
    clips = await clip_detector.detect_clips(
        transcript_segments=req.transcript_segments,
        video_duration=req.video_duration,
        target_clip_count=req.target_clip_count or 5,
        min_duration=req.min_duration or 25.0,
        max_duration=req.max_duration or 75.0,
        niche_id=req.niche_id,
    )
    return [c.to_dict() for c in clips]


@app.post("/api/plan-edit")
async def plan_edit_endpoint(req: PlanEditRequest):
    """Generate declarative, non-destructive Edit Plan."""
    cand = None
    if req.clip_candidate:
        from ai_broll_autopilot.services.clip_detector import ClipCandidate
        c = req.clip_candidate
        cand = ClipCandidate(
            id=c.get("id", "clip_01"),
            start_time=c.get("start_time", 0.0),
            end_time=c.get("end_time", req.source_media.get("duration", 30.0)),
            duration=c.get("duration", 30.0),
            title=c.get("title", "Clip"),
            hook_text=c.get("hook_text", ""),
            summary=c.get("summary", ""),
            viral_score=c.get("viral_score", 80.0),
            factor_scores=c.get("factor_scores", {}),
            rationale=c.get("rationale", ""),
            suggested_broll_topics=c.get("suggested_broll_topics", []),
            tags=c.get("tags", []),
        )

    plan = await edit_director.plan_edit(
        source_media=req.source_media,
        transcript_segments=req.transcript_segments,
        clip_candidate=cand,
        in_point=req.in_point,
        out_point=req.out_point,
        niche_id=req.niche_id,
        style_id=req.style_id,
        custom_hook=req.custom_hook,
    )
    return plan.to_dict()


@app.post("/api/export-openreel")
async def export_openreel_endpoint(req: ExportOpenReelRequest):
    """Export EditPlan as OpenReel Schema 1.2.0 project (.oreel / project.json)."""
    p_data = req.edit_plan
    plan = EditPlan(
        plan_id=p_data.get("plan_id", "plan_01"),
        title=p_data.get("title", "OpenReel Project"),
        target_duration=p_data.get("target_duration", 30.0),
        source_media=p_data.get("source_media", {}),
        clip_interval=p_data.get("clip_interval", {"in_point": 0.0, "out_point": 30.0}),
        niche=p_data.get("niche", {}),
        style=p_data.get("style", {}),
        shots=p_data.get("shots", []),
        text_overlays=p_data.get("text_overlays", []),
        subtitles=p_data.get("subtitles", []),
        zooms=p_data.get("zooms", []),
        audio_cues=p_data.get("audio_cues", {}),
    )

    out_folder = Path(req.output_folder) if req.output_folder else (Config.OUTPUT_DIR / "openreel_projects" / plan.plan_id)
    files = openreel_adapter.export_project_files(
        edit_plan=plan,
        output_dir=out_folder,
        resolved_broll_map=req.resolved_broll_map,
    )

    manifest_json = {}
    if files["manifest"].exists():
        with open(files["manifest"], "r", encoding="utf-8") as f:
            manifest_json = json.load(f)

    return {
        "status": "success",
        "plan_id": plan.plan_id,
        "files": {k: str(v) for k, v in files.items()},
        "manifest": manifest_json,
        "openreel_payload": openreel_adapter.create_openreel_project(plan, resolved_broll_map=req.resolved_broll_map),
    }


@app.get("/api/library")
async def get_library_endpoint(niche_id: Optional[str] = None, limit: int = 50):
    """Retrieve cataloged B-roll assets and statistics."""
    stats = broll_library.get_stats()
    assets = broll_library.list_assets(niche_id=niche_id, limit=limit)
    return {
        "stats": stats,
        "assets": assets,
    }


@app.post("/api/library/index")
async def index_library_endpoint(req: LibraryIndexRequest):
    """Index video files from a local directory into the B-roll library."""
    p = Path(req.directory_path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail="Directory not found")
    count = broll_library.index_directory(p, niche_id=req.niche_id, tags=req.tags)
    return {"status": "indexed", "count": count, "stats": broll_library.get_stats()}


# Standalone runner
def main():
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("ai_broll_autopilot.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
