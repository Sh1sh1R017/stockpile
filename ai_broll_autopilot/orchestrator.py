"""Master Orchestrator coordinating the complete AI B-Roll Autopilot pipeline."""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.core.job import Job, JobState
from ai_broll_autopilot.core.queue import JobQueue
from ai_broll_autopilot.services.transcriber import Transcriber
from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.services.matcher import Matcher
from ai_broll_autopilot.services.renderer import Renderer
from ai_broll_autopilot.services.reviewer import Reviewer
from ai_broll_autopilot.services.delivery import DeliveryService
from ai_broll_autopilot.services.watcher import InputWatcher
from ai_broll_autopilot.services.video_sfx_analyzer import VideoSFXAnalyzer
from ai_broll_autopilot.services.transition_engine import TransitionEngine

logger = logging.getLogger(__name__)


def get_video_duration(file_path: str) -> float:
    """Probe video duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.check_output(cmd).decode().strip()
        return float(res)
    except Exception as e:
        logger.warning(f"Could not probe video duration: {e}. Defaulting to 30.0s.")
        return 30.0


class Orchestrator:
    """Master workflow orchestrator managing state transitions and task dispatch."""

    def __init__(self):
        Config.ensure_directories()
        self.db = Database()
        self.queue = JobQueue(self.db, max_concurrent=1)
        self.transcriber = Transcriber()
        self.director = Director()
        self.matcher = Matcher(self.db)
        self.renderer = Renderer()
        self.reviewer = Reviewer()
        self.delivery = DeliveryService()
        self.sfx_analyzer = VideoSFXAnalyzer()
        self.transition_engine = TransitionEngine()
        self.watcher = InputWatcher(Config.INPUT_DIR, self.enqueue_file_sync)

    def enqueue_file_sync(self, file_path: str):
        """Synchronous hook for watcher thread."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.enqueue_file(file_path), loop)
        except Exception:
            asyncio.run(self.enqueue_file(file_path))

    async def enqueue_file(self, file_path: str) -> str:
        """Create and enqueue a new job from a file path."""
        job = Job.create(file_path)
        await self.queue.enqueue(job)
        return job.job_id

    async def start(self):
        """Start the background autopilot worker queue."""
        logger.info("Initializing AI B-Roll Autopilot worker queue...")
        await self.queue.start(self.process_job)

    async def stop(self):
        """Gracefully shut down autopilot."""
        self.watcher.stop()
        await self.queue.stop()

    async def process_job(self, job: Job):
        """Process a single job end-to-end through the state machine."""
        logger.info(f"=== Starting Autopilot for Job {job.job_id}: {job.source_filename} ===")
        work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. INGESTING
            self._update_state(job, JobState.INGESTING, progress=0.1, msg="Validating input video")
            duration = get_video_duration(job.source_file)
            logger.info(f"Input video duration: {duration:.2f}s")

            # 2. TRANSCRIBING
            self._update_state(job, JobState.TRANSCRIBING, progress=0.2, msg="Transcribing audio with Whisper")
            transcription_result = await self.transcriber.transcribe(job.source_file)
            job.transcript_text = transcription_result["text"]
            job.transcript_segments = transcription_result["segments"]
            self.db.save_job(job)
            logger.info(f"Transcription completed ({len(job.transcript_segments)} segments)")

            # 3. DIRECTING
            self._update_state(job, JobState.DIRECTING, progress=0.35, msg="AI Director generating Visual Edit Plan")
            edit_plan = await self.director.create_edit_plan(
                job.transcript_text,
                job.transcript_segments,
                duration
            )
            job.edit_plan = edit_plan
            self.db.save_job(job)

            # 4. MATCHING
            self._update_state(job, JobState.MATCHING, progress=0.5, msg="Matching & acquiring B-roll assets")
            broll_dir = work_dir / "broll"
            resolved_plan = await self.matcher.resolve_shots(edit_plan, broll_dir)
            job.edit_plan = resolved_plan
            self.db.save_job(job)

            # 5. PLANNING: AutoTransitions & AI Sound Effects
            self._update_state(job, JobState.PLANNING, progress=0.65, msg="Planning AutoTransitions & AI Sound Effects")
            if "shots" in job.edit_plan and job.edit_plan["shots"]:
                # 5a. AutoTransition recommendation (yaojie-shen/AutoTransition approach)
                job.edit_plan["shots"] = await self.transition_engine.plan_transitions(job.edit_plan["shots"])
                # 5b. Video Sound Effect Vision Analysis (sieve-community/video-sound-effect approach)
                job.edit_plan["shots"] = await self.sfx_analyzer.analyze_and_assign_sfx(job.edit_plan["shots"], work_dir)
                self.db.save_job(job)

            # 6. RENDERING
            self._update_state(job, JobState.RENDERING, progress=0.75, msg="Compositing B-roll onto base video")
            rendered_video = work_dir / f"rendered_{job.source_filename}"
            final_rendered_path = await self.renderer.render(
                job.source_file,
                job.edit_plan,
                str(rendered_video)
            )

            # 7. REVIEWING & AUTO-REPAIR LOOP
            self._update_state(job, JobState.REVIEWING, progress=0.85, msg="Independent AI Reviewer inspecting quality")
            review_result = await self.reviewer.review_video(
                final_rendered_path,
                job.edit_plan,
                work_dir / "review_frames"
            )
            job.review_data = review_result
            self.db.save_job(job)

            # Auto-repair loop if needed (max 2 attempts)
            while review_result.get("verdict") == "REPAIR" and job.repair_count < 2:
                job.repair_count += 1
                self._update_state(
                    job, JobState.REPAIRING, progress=0.88,
                    msg=f"Auto-repair pass {job.repair_count}: {review_result.get('feedback')}"
                )
                repaired_plan = self.reviewer.apply_repairs(job.edit_plan, review_result)
                job.edit_plan = repaired_plan

                # Re-resolve any pending or updated shots
                resolved_plan = await self.matcher.resolve_shots(job.edit_plan, broll_dir)
                job.edit_plan = resolved_plan

                self._update_state(job, JobState.RENDERING, progress=0.90, msg="Re-rendering after repair")
                final_rendered_path = await self.renderer.render(
                    job.source_file,
                    job.edit_plan,
                    str(rendered_video)
                )

                self._update_state(job, JobState.REVIEWING, progress=0.92, msg="Re-inspecting after repair")
                review_result = await self.reviewer.review_video(
                    final_rendered_path,
                    job.edit_plan,
                    work_dir / f"review_frames_pass_{job.repair_count}"
                )
                job.review_data = review_result
                self.db.save_job(job)

            # 8. UPLOADING / PACKAGING
            self._update_state(job, JobState.UPLOADING, progress=0.95, msg="Delivering final video and assets")
            srt_text = transcription_result.get("srt")
            delivery_res = await self.delivery.deliver(job, final_rendered_path, srt_text)

            job.output_video_path = delivery_res["final_video"]
            job.drive_file_url = delivery_res["drive_url"]

            # Generate Feedback Survey & Emotional Score Report for Continuous Learning
            try:
                survey_data = {
                    "job_id": job.job_id,
                    "source_video": job.source_filename,
                    "summary": job.edit_plan.get("summary", ""),
                    "shots": []
                }
                for shot in job.edit_plan.get("shots", []):
                    survey_data["shots"].append({
                        "shot_id": shot.get("shot_id"),
                        "start_time": shot.get("start_time"),
                        "end_time": shot.get("end_time"),
                        "dialogue_quote": shot.get("dialogue_quote", ""),
                        "emotional_core": shot.get("emotional_core", "Human emotion"),
                        "visceral_human_metaphor": shot.get("visceral_human_metaphor", ""),
                        "asset_title": Path(shot.get("asset_path", "")).name if shot.get("asset_path") else "",
                        "emotional_score": 9,
                        "feedback_prompt": f"Did this visual metaphor connect emotionally with '{shot.get('dialogue_quote', '')}'?"
                    })
                survey_path = Path(delivery_res["final_video"]).parent / "feedback_survey.json"
                with open(survey_path, "w", encoding="utf-8") as sf:
                    json.dump(survey_data, sf, indent=2)
                logger.info(f"Generated Feedback Survey at: {survey_path.name}")
            except Exception as fe:
                logger.warning(f"Could not generate feedback survey: {fe}")

            # 9. COMPLETED
            self._update_state(
                job, JobState.COMPLETED, progress=1.0,
                msg=f"Job completed successfully: {job.output_video_path}"
            )
            logger.info(f"=== COMPLETED Job {job.job_id} -> {job.output_video_path} ===")

        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)
            self._update_state(job, JobState.FAILED, progress=job.progress, error=str(e), msg=f"Failed: {e}")

    def _update_state(
        self,
        job: Job,
        state: JobState,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        msg: str = ""
    ):
        old_state = job.status.value
        job.transition_to(state, error=error, progress=progress)
        self.db.save_job(job)
        self.db.record_transition(job.job_id, old_state, state.value, msg or error or "")
