"""Master Orchestrator coordinating the complete AI B-Roll Autopilot pipeline."""

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

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
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.subject_caption import annotate_segments_for_subject_captions, has_behind_subject_segments
from ai_broll_autopilot.services.subject_isolation import subject_isolation_service
from ai_broll_autopilot.services.qc_service import edit_quality_service
from ai_broll_autopilot.services.broll_super_director import broll_super_director

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


    async def enqueue_short_edit(
        self,
        parent_job_id: str,
        start: float,
        end: float,
        title: str,
        source: str = "manual",
        batch_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        caption_style: Optional[str] = None,
        caption_motion: Optional[str] = None,
        subtitles_behind_subject: Optional[bool] = None,
    ) -> str:
        """Create a child job that edits only one interval of a long-form parent job."""
        parent = self.db.get_job(parent_job_id)
        if not parent:
            raise ValueError("Parent job not found")
        source_path = Path(parent.source_file)
        if not source_path.exists():
            raise ValueError("Parent source video is not available")

        start_f = max(0.0, float(start))
        end_f = float(end)
        if end_f <= start_f:
            raise ValueError("Short end timestamp must be greater than start timestamp")

        child = Job.create(str(source_path), campaign_id=parent.campaign_id)
        safe_title = re.sub(r"[^A-Za-z0-9._ -]+", "", str(title or "Short")).strip()[:70] or "Short"
        child.source_filename = f"{source_path.stem} - {safe_title}.mp4"
        child.transcript_segments = parent.transcript_segments
        child.transcript_text = parent.transcript_text

        from ai_broll_autopilot.services.shorts_workflow import workflow_record
        parent_plan = parent.edit_plan or {}
        parent_niche = (parent_plan.get("niche") or {}).get("id") or parent_plan.get("niche_id")
        parent_style = (parent_plan.get("style") or {}).get("id") or parent_plan.get("style_id")
        child.edit_plan = {
            "workflow": workflow_record(
                parent_job_id=parent_job_id,
                source=source,
                start=start_f,
                end=end_f,
                title=safe_title,
                batch_id=batch_id,
                candidate_id=candidate_id,
                caption_style=caption_style,
                caption_motion=caption_motion,
                subtitles_behind_subject=subtitles_behind_subject,
                niche_id=parent_niche,
                style_id=parent_style,
            ),
        }

        await self.queue.enqueue(child)

        parent_plan = parent.edit_plan or {}
        children = parent_plan.setdefault("short_edits", [])
        children.append({
            "job_id": child.job_id,
            "title": safe_title,
            "source": source,
            "start": round(start_f, 3),
            "end": round(end_f, 3),
            "batch_id": batch_id,
            "candidate_id": candidate_id,
            "status": "queued",
        })
        parent.edit_plan = parent_plan
        self.db.save_job(parent)
        return child.job_id

    async def start(self):
        """Start the background autopilot worker queue."""
        logger.info("Initializing AI B-Roll Autopilot worker queue...")
        await self.queue.start(self.process_job)

    async def stop(self):
        """Gracefully shut down autopilot."""
        self.watcher.stop()
        await self.queue.stop()

    async def _prepare_caption_render_assets(
        self,
        source_video: str,
        edit_plan: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        work_dir: Path,
        style_preset: str,
        position: str,
        custom_margin_v: Optional[int] = None,
        hook_text: Optional[str] = None,
        hook_duration: Optional[float] = None,
        suppress_hook: bool = False,
        text_emphasis_events: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Prepare the single canonical caption stack used by production rendering.

        CaptionCompositor owns Razor events, semantic hook promotion, normal-vs-
        behind-subject separation, and matte generation. Keeping this wrapper
        preserves the Orchestrator API while removing the old parallel subtitle
        implementation that could burn the hook twice.
        """
        from ai_broll_autopilot.services.caption_compositor import CaptionCompositor

        render_settings = edit_plan.get("render_settings", {}) if edit_plan else {}
        # Behind-subject hook treatment is the default production behavior when
        # no explicit user setting exists. An explicit false remains authoritative.
        if "subtitles_behind_subject" not in render_settings and (
            not edit_plan or "subtitles_behind_subject" not in edit_plan
        ):
            render_settings = dict(render_settings)
            render_settings["subtitles_behind_subject"] = True
            if edit_plan is not None:
                edit_plan["render_settings"] = render_settings
                edit_plan["subtitles_behind_subject"] = True

        compositor = CaptionCompositor(
            target_width=Config.TARGET_WIDTH,
            target_height=Config.TARGET_HEIGHT,
        )
        return await compositor.prepare_caption_render_assets(
            source_video=source_video,
            edit_plan=edit_plan,
            transcript_segments=transcript_segments,
            work_dir=work_dir,
            style_preset=style_preset,
            position=position,
            custom_margin_v=(
                custom_margin_v
                if render_settings.get("subtitle_y_percent") is None
                else None
            ),
            hook_text=None if suppress_hook else hook_text,
            hook_duration=hook_duration,
            suppress_hook=suppress_hook,
            text_emphasis_events=text_emphasis_events,
            caption_motion=render_settings.get("caption_motion", "word-pop"),
            custom_colors=render_settings.get("custom_colors"),
            enable_emojis=render_settings.get("enable_emojis", True),
            words_per_beat=int(render_settings.get("words_per_beat", 3) or 3),
        )

    async def process_job(self, job: Job):
        """Process a single job end-to-end through the state machine."""
        workflow = (job.edit_plan or {}).get("workflow") if job.edit_plan else None
        if workflow and workflow.get("type") == "short_edit":
            await self._process_short_edit_job(job)
            return

        from ai_broll_autopilot.campaigns import campaign_registry
        campaign = campaign_registry.get_campaign(job.campaign_id)
        logger.info(f"=== Starting Autopilot for Job {job.job_id} [Campaign: {campaign.name}] ({job.source_filename}) ===")
        work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. INGESTING
            self._update_state(job, JobState.INGESTING, progress=0.1, msg=f"Validating input for '{campaign.name}'")
            duration = get_video_duration(job.source_file)
            # Keep the canonical source duration available to later export stages.
            total_duration = duration
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

            # Audio-aware B-roll Super Director: identify the most impactful
            # dialogue moments from both words and vocal delivery before retrieval.
            try:
                niche_ctx = (edit_plan.get("niche") or {}).get("name") if isinstance(edit_plan, dict) else None
                style_ctx = (edit_plan.get("style") or {}).get("name") if isinstance(edit_plan, dict) else None
                super_analysis = await broll_super_director.analyze(
                    source_video=job.source_file,
                    transcript_segments=job.transcript_segments or [],
                    video_duration=duration,
                    output_dir=work_dir / "broll_super",
                    niche=niche_ctx or getattr(campaign, "name", "generic"),
                    style=style_ctx or getattr(campaign, "subtitle_style", "clean_podcast"),
                    target_shots=max(3, len(edit_plan.get("shots", []) or [])),
                )
                edit_plan = broll_super_director.apply_to_plan(
                    edit_plan,
                    super_analysis,
                    duration,
                )
                if super_analysis.get("moments"):
                    logger.info(
                        "B-roll Super Director selected %d emotional opportunities using %s",
                        len(super_analysis["moments"]),
                        super_analysis.get("model"),
                    )
            except Exception as super_err:
                logger.warning("B-roll Super Director skipped; preserving existing Director plan: %s", super_err)

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

                    # The reference treatment is intentionally cut-driven. Keep the
                    # transition lane clean and remove automatically attached stingers.
                    style_data = job.edit_plan.get("style") or {}
                    reference_editing = bool(
                        job.edit_plan.get("reference_editing")
                        or style_data.get("reference_style")
                        or style_data.get("id") in {"cinematic_social_editorial", "cinematic_editorial"}
                    )
                    if reference_editing:
                        for shot in job.edit_plan["shots"]:
                            shot["transition"] = {
                                "type_in": "cut",
                                "duration_in": 0.0,
                                "type_out": "cut",
                                "duration_out": 0.0,
                            }

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

            # 6b. Prepare kinetic subtitles and optional behind-subject caption layers
            ass_path = None
            behind_subject_ass_path = None
            subject_matte_path = None
            if job.transcript_segments and campaign.subtitles_required:
                ass_path, behind_subject_ass_path, subject_matte_path = await self._prepare_caption_render_assets(
                    source_video=job.source_file,
                    edit_plan=edit_plan,
                    transcript_segments=job.transcript_segments,
                    work_dir=work_dir,
                    style_preset=((edit_plan.get("style") or {}).get("caption_preset") or campaign.subtitle_style),
                    position=((edit_plan.get("style") or {}).get("caption_position") or campaign.subtitle_position),
                    custom_margin_v=(0 if str(edit_plan.get("editing_style") or (edit_plan.get("style") or {}).get("id") or campaign.subtitle_style) == "cinematic_editorial" else campaign.subtitle_margin_v),
                    hook_text=hook_txt,
                    hook_duration=duration if campaign.id == "curious_mike" else 4.0,
                    suppress_hook=bool(frame_overlay_path),
                    text_emphasis_events=edit_plan.get("text_emphasis_graphics"),
                )
                if behind_subject_ass_path and subject_matte_path:
                    logger.info(f"Behind-subject captions enabled: {behind_subject_ass_path}")
                elif ass_path:
                    logger.info(f"Kinetic subtitles generated at: {ass_path}")

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
                behind_subject_ass_path=behind_subject_ass_path,
                subject_matte_path=subject_matte_path,
                bgm_path=bgm_path,
                bgm_volume=0.14,
                upscale_hdr=getattr(job, "upscale_hdr", False),
                hdr_scale=1.0,
                hdr_tone="vivid",
                watermark_path=wm_path,
                watermark_position=wm_pos,
                watermark_scale=wm_scale,
                preserve_dialogue_only=getattr(campaign, "preserve_dialogue_only", False),
                frame_overlay_path=frame_overlay_path,
                viewport=getattr(campaign, "frame_viewport", None),
                source_start_time=0.0,
                render_duration=duration,
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
                    behind_subject_ass_path=behind_subject_ass_path,
                    subject_matte_path=subject_matte_path,
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

            # 8.6 Generate Native OpenReel Project Bundle (.oreel / project.json / manifest)
            try:
                openreel_dir = Path(delivery_res["final_video"]).parent / "openreel"
                openreel_dir.mkdir(parents=True, exist_ok=True)
                plan_dict = job.edit_plan or {}
                source_meta = {
                    "path": job.source_file,
                    "duration": total_duration,
                    "title": job.source_filename,
                }
                plan_obj = EditPlan(
                    plan_id=f"plan_{job.job_id}",
                    title=f"Edit: {Path(job.source_filename).stem}",
                    target_duration=total_duration,
                    source_media=source_meta,
                    clip_interval={"in_point": 0.0, "out_point": total_duration},
                    niche=plan_dict.get("niche", {"name": "Podcast", "id": "generic"}),
                    style=plan_dict.get("style", {"name": "Clean Podcast", "id": "clean_podcast"}),
                    shots=plan_dict.get("shots", []),
                    text_overlays=plan_dict.get("text_overlays", []),
                    subtitles=plan_dict.get("subtitles", []),
                    zooms=plan_dict.get("zooms", []),
                    audio_cues=plan_dict.get("audio_cues", {}),
                )
                openreel_adapter.export_project_files(
                    edit_plan=plan_obj,
                    output_dir=openreel_dir,
                    project_filename=f"{job.job_id}.oreel",
                )
                logger.info(f"Generated OpenReel Project Bundle at: {openreel_dir}")
            except Exception as oreel_err:
                logger.warning(f"Could not generate OpenReel project bundle: {oreel_err}")

            # 9. COMPLETED
            self._update_state(
                job, JobState.COMPLETED, progress=1.0,
                msg=f"Job completed successfully: {job.output_video_path}"
            )
            logger.info(f"=== COMPLETED Job {job.job_id} -> {job.output_video_path} ===")

        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)
            self._update_state(job, JobState.FAILED, progress=job.progress, error=str(e), msg=f"Failed: {e}")


    async def _process_short_edit_job(self, job: Job):
        """Run a child short through Stockpile's editorial and render pipeline."""
        from ai_broll_autopilot.campaigns import campaign_registry
        from ai_broll_autopilot.services.edit_director import edit_director, EditPlan
        from ai_broll_autopilot.services.razor_caption import RazorCaptionEngine
        from ai_broll_autopilot.services.shorts_workflow import normalize_clip_transcript, build_clip_candidate

        workflow = (job.edit_plan or {}).get("workflow", {})
        interval = workflow.get("source_interval", {})
        source_start = float(interval.get("start", 0.0))
        source_end = float(interval.get("end", 0.0))
        campaign = campaign_registry.get_campaign(job.campaign_id)
        work_dir = Config.OUTPUT_DIR / "workspace" / job.job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        broll_dir = work_dir / "broll"

        try:
            self._update_state(job, JobState.INGESTING, progress=0.10, msg="Preparing selected short interval")
            full_duration = get_video_duration(job.source_file)
            source_start = max(0.0, min(source_start, full_duration))
            source_end = max(source_start + 0.25, min(source_end, full_duration))
            short_duration = source_end - source_start

            if not job.transcript_segments:
                self._update_state(job, JobState.TRANSCRIBING, progress=0.20, msg="Transcribing source for selected short")
                transcription_result = await self.transcriber.transcribe(job.source_file)
                job.transcript_text = transcription_result["text"]
                job.transcript_segments = transcription_result["segments"]
            else:
                self._update_state(job, JobState.TRANSCRIBING, progress=0.20, msg="Reusing parent transcript")

            niche_id = workflow.get("niche_id") or ((job.edit_plan or {}).get("niche", {}) or {}).get("id") or getattr(campaign, "niche_id", None) or "generic"
            style_id = workflow.get("style_id") or ((job.edit_plan or {}).get("style", {}) or {}).get("id") or "clean_podcast"

            self._update_state(job, JobState.DIRECTING, progress=0.35, msg="Building Stockpile edit for selected moment")
            normalized = {
                "id": workflow.get("candidate_id") or job.job_id,
                "start": source_start,
                "end": source_end,
                "title": workflow.get("title") or Path(job.source_filename).stem,
                "hook_text": workflow.get("title") or "",
                "summary": workflow.get("title") or "",
            }
            clip_candidate = build_clip_candidate(normalized, full_duration)
            plan_obj = await edit_director.plan_edit(
                source_media={
                    "path": job.source_file,
                    "duration": full_duration,
                    "width": Config.TARGET_WIDTH,
                    "height": Config.TARGET_HEIGHT,
                    "fps": Config.TARGET_FPS,
                    "title": workflow.get("title") or job.source_filename,
                },
                transcript_segments=job.transcript_segments or [],
                clip_candidate=clip_candidate,
                niche_id=niche_id,
                style_id=style_id,
                custom_hook=workflow.get("title") or None,
            )
            plan = plan_obj.to_dict()

            try:
                super_analysis = await broll_super_director.analyze(
                    source_video=job.source_file,
                    transcript_segments=job.transcript_segments or [],
                    video_duration=full_duration,
                    output_dir=work_dir / "broll_super",
                    niche=niche_id,
                    style=style_id,
                    target_shots=max(3, len(plan.get("shots", []) or [])),
                )
                plan = broll_super_director.apply_to_plan(
                    plan,
                    super_analysis,
                    full_duration,
                )
            except Exception as super_err:
                logger.warning("Child B-roll Super Director skipped: %s", super_err)

            render_settings = plan.setdefault("render_settings", {})
            render_settings["caption_engine"] = "rapid_razor"
            render_settings["caption_style"] = workflow.get("caption_style") or campaign.subtitle_style
            render_settings["caption_motion"] = workflow.get("caption_motion") or "word-pop"
            render_settings["subtitles_behind_subject"] = (
                bool(workflow.get("subtitles_behind_subject"))
                if workflow.get("subtitles_behind_subject") is not None
                else True
            )
            plan["workflow"] = workflow

            self._update_state(job, JobState.MATCHING, progress=0.50, msg="Resolving contextual B-roll")
            plan = await self.matcher.resolve_shots(plan, broll_dir)

            self._update_state(job, JobState.PLANNING, progress=0.65, msg="Planning transitions and sound design")
            if plan.get("shots"):
                plan["shots"] = await self.transition_engine.plan_transitions(plan["shots"])
                if not getattr(campaign, "preserve_dialogue_only", False):
                    plan["shots"] = await self.sfx_analyzer.analyze_and_assign_sfx(plan["shots"], work_dir)

            clip_segments = normalize_clip_transcript(job.transcript_segments or [], source_start, source_end)
            razor_engine = RazorCaptionEngine(
                enable_behind_subject=bool(render_settings.get("subtitles_behind_subject", True)),
                enable_sfx=True,
            )
            broll_times = [
                (float(s.get("start_time", 0.0)), float(s.get("end_time", 0.0)))
                for s in plan.get("shots", [])
            ]
            subject_info = await asyncio.to_thread(
                subject_isolation_service.analyze_subject_layout,
                job.source_file,
                max(0.0, source_start + min(1.0, short_duration / 2.0)),
            )
            razor_events = razor_engine.process(
                clip_segments,
                subject_info=subject_info,
                broll_active_times=broll_times,
            )
            plan["razor_captions"] = razor_engine.to_edit_plan(razor_events)

            self._update_state(job, JobState.RENDERING, progress=0.76, msg="Rendering kinetic captions and B-roll")
            rendered_video = work_dir / f"rendered_{job.source_filename}"
            normal_ass = work_dir / "razor_captions.ass"
            normal_events = [
                ev for ev in razor_events
                if not ev.requires_behind_subject
            ]
            razor_engine.generate_ass(
                normal_events,
                output_path=normal_ass,
                style_preset=render_settings.get("caption_style") or campaign.subtitle_style,
                position=getattr(campaign, "subtitle_position", "bottom"),
            )

            behind_ass = None
            matte_path = None
            if any(ev.requires_behind_subject for ev in razor_events) and render_settings.get("subtitles_behind_subject", True):
                behind_ass_path = work_dir / "razor_captions_behind_subject.ass"
                behind_path = razor_engine.generate_behind_subject_ass(
                    razor_events,
                    output_path=behind_ass_path,
                    style_preset=render_settings.get("caption_style") or campaign.subtitle_style,
                )
                if behind_path and behind_path.exists():
                    matte = work_dir / "subject_matte.mp4"
                    await asyncio.to_thread(
                        subject_isolation_service.generate_person_matte_video,
                        job.source_file,
                        str(matte),
                        8.0,
                        540,
                        960,
                        source_start,
                        short_duration,
                    )
                    if matte.exists():
                        behind_ass = str(behind_path.resolve())
                        matte_path = str(matte.resolve())

            bgm_path = None
            if getattr(campaign, "allow_bgm", False):
                try:
                    p = self.bgm_engine.get_track_path(getattr(campaign, "bgm_genre", None) or "upbeat_phonk")
                    if p and p.exists():
                        bgm_path = str(p.resolve())
                except Exception:
                    bgm_path = None

            plan["workflow"]["status"] = "rendering"
            job.edit_plan = plan
            self.db.save_job(job)

            final_rendered_path = await self.renderer.render(
                job.source_file,
                plan,
                str(rendered_video),
                ass_subtitles_path=str(normal_ass.resolve()) if normal_ass.exists() else None,
                behind_subject_ass_path=behind_ass,
                subject_matte_path=matte_path,
                bgm_path=bgm_path,
                bgm_volume=0.14,
                ducking_enabled=True,
                watermark_path=campaign.watermark_asset_path if getattr(campaign, "watermark_required", False) else None,
                watermark_position=getattr(campaign, "watermark_position", "bottom_safe"),
                watermark_scale=getattr(campaign, "watermark_scale", 0.28),
                preserve_dialogue_only=getattr(campaign, "preserve_dialogue_only", False),
                viewport=getattr(campaign, "frame_viewport", None),
                source_start_time=source_start,
                render_duration=short_duration,
            )

            self._update_state(job, JobState.REVIEWING, progress=0.90, msg="Checking generated short")
            try:
                job.review_data = await self.reviewer.review_video(final_rendered_path, plan, work_dir / "review_frames")
            except Exception as review_error:
                logger.warning(f"Short review skipped: {review_error}")
                job.review_data = None

            self._update_state(job, JobState.UPLOADING, progress=0.95, msg="Packaging generated short")
            delivery_res = await self.delivery.deliver(job, final_rendered_path, None)
            job.output_video_path = delivery_res["final_video"]
            job.drive_file_url = delivery_res.get("drive_url")

            try:
                openreel_dir = Path(job.output_video_path).parent / "openreel"
                openreel_dir.mkdir(parents=True, exist_ok=True)
                openreel_adapter.export_project_files(
                    edit_plan=EditPlan.from_dict(plan),
                    output_dir=openreel_dir,
                    project_filename=f"{job.job_id}.oreel",
                )
            except Exception as oreel_error:
                logger.warning(f"OpenReel export for child short skipped: {oreel_error}")

            plan["workflow"]["status"] = "completed"
            plan["render_stale"] = False
            plan["last_render_revision"] = int(plan.get("edit_revision", 1))
            job.edit_plan = plan
            self._update_parent_short_status(job, "COMPLETED")
            self._update_state(job, JobState.COMPLETED, progress=1.0, msg="Edited short completed")
        except Exception as e:
            workflow = (job.edit_plan or {}).setdefault("workflow", {})
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            job.edit_plan = job.edit_plan or {}
            job.edit_plan["workflow"] = workflow
            self._update_parent_short_status(job, "FAILED")
            self._update_state(job, JobState.FAILED, progress=job.progress, error=str(e), msg=f"Short edit failed: {e}")

    def _update_parent_short_status(self, job: Job, status: str):
        """Mirror child short status into its parent EditPlan when the parent still exists."""
        workflow = (job.edit_plan or {}).get("workflow", {}) if job.edit_plan else {}
        parent_id = workflow.get("parent_job_id")
        if not parent_id:
            return

        parent = self.db.get_job(parent_id)
        if not parent or not parent.edit_plan:
            return

        changed = False
        for item in parent.edit_plan.get("short_edits", []):
            if item.get("job_id") == job.job_id:
                item["status"] = status
                changed = True
                break

        if changed:
            self.db.save_job(parent)

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
