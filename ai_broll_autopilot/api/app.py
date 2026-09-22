"""FastAPI REST API server for AI B-Roll Autopilot.

Exposes REST endpoints for the Next.js Web Dashboard, real-time job monitoring,
video uploads, video streaming, emotional feedback submission, and Google Drive cloud sync.
"""

import asyncio
import json
import logging
import os
import shutil
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
            "-q:v", "2",
            str(thumb_path)
        ]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
        except Exception as e:
            logger.error(f"Failed to generate thumb for {shot_id}: {e}")

    if not thumb_path.exists():
        raise HTTPException(status_code=500, detail="Could not extract thumbnail")

    return FileResponse(
        path=str(thumb_path),
        media_type="image/jpeg",
        filename=thumb_path.name,
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
async def upload_video(file: UploadFile = File(...)):
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

    logger.info(f"Uploaded file saved to: {target_file}")

    # Enqueue job
    job_id = await orchestrator.enqueue_file(str(target_file))

    return {
        "status": "queued",
        "job_id": job_id,
        "filename": target_file.name,
        "message": f"Successfully uploaded and enqueued {target_file.name}",
    }


@app.post("/api/jobs/youtube")
async def import_youtube_video(req: YouTubeJobRequest):
    """Import a video from YouTube URL, download with yt-dlp, and enqueue for autopilot processing."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    logger.info(f"Importing YouTube video from URL: {url}")
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
        job_id = await orchestrator.enqueue_file(str(downloaded_file))

        return {
            "status": "queued",
            "job_id": job_id,
            "filename": downloaded_file.name,
            "message": f"Successfully imported and enqueued {downloaded_file.name}",
        }
    except Exception as e:
        logger.error(f"Error importing YouTube video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import YouTube video: {str(e)}")


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
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()
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

    # Plan transitions and stingers for shots
    shots = await trans_engine.plan_transitions(job.edit_plan["shots"])
    job.edit_plan["shots"] = shots

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

    out_path = await renderer.render(
        base_video=job.source_file,
        edit_plan=job.edit_plan,
        output_path=str(rendered_video),
        ass_subtitles_path=ass_path,
        bgm_path=bgm_path,
        bgm_volume=bgm_vol,
        ducking_enabled=ducking
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
        "bgm_applied": bool(bgm_path)
    }


@app.get("/api/sfx-catalog")
async def get_sfx_catalog():
    """Retrieve catalog of all 189 available sound effects and stingers."""
    catalog_path = Config.OUTPUT_DIR / "split_sfx" / "sfx_catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Standalone runner
def main():
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("ai_broll_autopilot.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
