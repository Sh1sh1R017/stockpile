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
from ai_broll_autopilot.services.subtitle_engine import SubtitleEngine
from ai_broll_autopilot.services.bgm_engine import BGMEngine

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
        self.sub_engine = SubtitleEngine()
        self.bgm_engine = BGMEngine()
        self.watcher = InputWatcher(Config.INPUT_DIR, self.enqueue_file_sync)

    def enqueue_file_sync(self, file_path: str):
        """Synchronous hook for watcher thread."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.enqueue_file(file_path), loop)
        except Exception:
            asyncio.run(self.enqueue_file(file_path))

    async def enqueue_file(self, file_path: str, campaign_id: str = "default") -> str:
        """Create and enqueue a new job from a file path."""
        job = Job.create(file_path, campaign_id=campaign_id)
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
        from ai_broll_autopilot.campaigns import campaign_registry
        campaign = campaign_registry.get_campaign(job.campaign_id)
        logger.info(f"=== Starting Autopilot for Job {job.job_id} [Campaign: {campaign.name}] ({job.source_filename}) ===")
        work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. INGESTING
            self._update_state(job, JobState.INGESTING, progress=0.1, msg=f"Validating input for '{campaign.name}'")
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
            self._update_state(job, JobState.DIRECTING, progress=0.35, msg=f"AI Director tailoring for '{campaign.name}'")
            moment_id_cand = getattr(job, "moment_id", None)
            if not moment_id_cand and job.campaign_id == "curious_mike":
                import re
                m_match = re.search(r"c(\d{1,2})", job.source_filename, re.IGNORECASE)
                if m_match:
                    moment_id_cand = f"C{int(m_match.group(1)):02d}"

            edit_plan = await self.director.create_edit_plan(
                job.transcript_text,
                job.transcript_segments,
                duration,
                campaign_id=job.campaign_id,
                curated_moment_id=moment_id_cand
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
                # 5a. AutoTransition recommendation: confident hard cuts with subtle whoosh for Curious Mike
                if campaign.id == "curious_mike":
                    for s in job.edit_plan["shots"]:
                        s["transition"] = {
                            "type_in": "cut",
                            "duration_in": 0.0,
                            "type_out": "cut",
                            "duration_out": 0.0,
                            "stinger_sfx": {
                                "file": "whoosh.mp3",
                                "path": "assets/sfx/whoosh.mp3",
                                "volume": 0.18
                            }
                        }
                else:
                    job.edit_plan["shots"] = await self.transition_engine.plan_transitions(job.edit_plan["shots"])

                # 5b. Video Sound Effect Vision Analysis: skip for Curious Mike to keep dialogue pure
                if not getattr(campaign, "preserve_dialogue_only", False) and campaign.id != "curious_mike":
                    job.edit_plan["shots"] = await self.sfx_analyzer.analyze_and_assign_sfx(job.edit_plan["shots"], work_dir)
                else:
                    logger.info(f"Campaign '{campaign.name}' enforces pure dialogue with editorial SFX only; skipping Foley vision analysis.")
                self.db.save_job(job)

            # 6. RENDERING: Kinetic Subtitles, Auto-Ducked BGM, AutoTransitions, Foley SFX, HDR10, Watermark
            self._update_state(job, JobState.RENDERING, progress=0.75, msg=f"Compositing timeline for '{campaign.name}'")
            rendered_video = work_dir / f"rendered_{job.source_filename}"

            # 6a. Generate authentic podcast torn paper frame overlay (with duotone hook & watermark)
            frame_overlay_path = None
            hook_txt = edit_plan.get("hook_text") or ""
            if getattr(campaign, "frame_overlay_required", False):
                try:
                    from ai_broll_autopilot.services.podcast_frame_engine import PodcastFrameEngine
                    frame_engine = PodcastFrameEngine()
                    frame_dest = work_dir / "campaign_frame.png"
                    frame_engine.generate_frame_overlay(
                        hook_text=hook_txt,
                        output_path=frame_dest,
                        watermark_text="YT: @mpj" if campaign.id == "curious_mike" else ""
                    )
                    if frame_dest.exists():
                        frame_overlay_path = str(frame_dest.resolve())
                        logger.info(f"Podcast frame overlay generated at: {frame_overlay_path}")
                except Exception as fe:
                    logger.warning(f"Could not generate podcast frame overlay: {fe}")

            # 6b. Generate kinetic subtitles with campaign styling and safe vertical positioning
            ass_path = None
            if job.transcript_segments and campaign.subtitles_required:
                try:
                    ass_dest = work_dir / "subtitles_kinetic.ass"
                    self.sub_engine.generate_ass_file(
                        segments=job.transcript_segments,
                        output_path=ass_dest,
                        style_preset=campaign.subtitle_style,
                        position=campaign.subtitle_position,
                        custom_margin_v=campaign.subtitle_margin_v,
                        hook_text=hook_txt,
                        hook_duration=duration if campaign.id == "curious_mike" else 4.0,
                        suppress_hook=bool(frame_overlay_path),
                        text_emphasis_events=edit_plan.get("text_emphasis_graphics"),
                    )
                    if ass_dest.exists():
                        ass_path = str(ass_dest.resolve())
                        logger.info(f"Kinetic subtitles generated at: {ass_path}")
                except Exception as se:
                    logger.warning(f"Could not generate kinetic subtitles: {se}")

            # 6c. Background Music: only if campaign allows it
            bgm_path = None
            if campaign.allow_bgm:
                try:
                    bgm_genre = campaign.bgm_genre or "upbeat_phonk"
                    p = self.bgm_engine.get_track_path(bgm_genre)
                    if p and p.exists():
                        bgm_path = str(p.resolve())
                        logger.info(f"BGM track selected: {p.name}")
                except Exception as be:
                    logger.warning(f"Could not resolve BGM track: {be}")

            # 6d. Watermark branding (compulsory for Curious Mike YT: @mpj)
            wm_path = campaign.watermark_asset_path if (campaign.watermark_required and not frame_overlay_path) else None
            wm_pos = campaign.watermark_position
            wm_scale = campaign.watermark_scale

            final_rendered_path = await self.renderer.render(
                job.source_file,
                job.edit_plan,
                str(rendered_video),
                ass_subtitles_path=ass_path,
                bgm_path=bgm_path,
                bgm_volume=0.14,
                upscale_hdr=False if campaign.id == "curious_mike" else True,
                hdr_scale=1.0,
                hdr_tone="vivid",
                watermark_path=wm_path,
                watermark_position=wm_pos,
                watermark_scale=wm_scale,
                preserve_dialogue_only=getattr(campaign, "preserve_dialogue_only", False),
                frame_overlay_path=frame_overlay_path,
                viewport=getattr(campaign, "frame_viewport", None),
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
                    str(rendered_video),
                    ass_subtitles_path=ass_path,
                    bgm_path=bgm_path,
                    bgm_volume=0.14,
                    ducking_enabled=True,
                    watermark_path=wm_path,
                    watermark_position=wm_pos,
                    watermark_scale=wm_scale,
                    preserve_dialogue_only=getattr(campaign, "preserve_dialogue_only", False),
                    frame_overlay_path=frame_overlay_path,
                    viewport=getattr(campaign, "frame_viewport", None),
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
