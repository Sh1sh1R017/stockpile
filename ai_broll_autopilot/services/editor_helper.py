"""Editor helper utilities for resolving canonical EditPlans and managing editor engines."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.job import Job
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.editor_base import EditorAdapter
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter
from ai_broll_autopilot.services.diffusion_adapter import diffusion_adapter
from ai_broll_autopilot.utils.timeline_math import TimelinePrecision

logger = logging.getLogger(__name__)


def get_job_edit_plan(job: Job) -> EditPlan:
    """Extract or construct a canonical EditPlan from a Job record."""
    if job.edit_plan and isinstance(job.edit_plan, dict):
        plan_dict = job.edit_plan
        total_dur = float(
            plan_dict.get("total_duration")
            or plan_dict.get("target_duration")
            or 30.0
        )
        clip_interval = plan_dict.get("clip_interval", {"in_point": 0.0, "out_point": total_dur})

        # 1. Resolve subtitles: fallback to job.transcript_segments if plan_dict.get("subtitles") is empty
        subtitles = plan_dict.get("subtitles") or []
        if not subtitles and job.transcript_segments:
            subtitles = []
            for idx, seg in enumerate(job.transcript_segments):
                subtitles.append({
                    "id": f"sub_{seg.get('id', idx+1)}",
                    "startTime": float(seg.get("start", 0.0)),
                    "endTime": float(seg.get("end", 0.0)),
                    "text": str(seg.get("text", "")).strip(),
                    "words": [
                        {
                            "word": w.get("word", ""),
                            "start": float(w.get("start", 0.0)),
                            "end": float(w.get("end", 0.0)),
                        }
                        for w in seg.get("words", [])
                    ],
                })

        # 2. Resolve text_overlays: fallback to hook_text and text_emphasis_graphics
        text_overlays = plan_dict.get("text_overlays") or []
        if not text_overlays:
            text_overlays = []
            hook = plan_dict.get("hook_text")
            if hook:
                # Opening-hook typography: deliberately oversized and centered behind the
                # subject, rather than looking like a normal subtitle/caption card.
                hook_clean = " ".join(str(hook).split())
                hook_display = hook_clean.upper()
                # A single strong hook word gets the tall editorial treatment from the
                # reference style; multi-word hooks stay readable as one centered phrase.
                if len(hook_clean.split()) == 1 and len(hook_clean) <= 18:
                    hook_display = "\n".join(list(hook_display))
                text_overlays.append({
                    "id": "opening_hook_behind_subject",
                    "kind": "opening_hook_typography",
                    "text": hook_display,
                    "start_time": 0.15,
                    "duration": 2.8,
                    "position": "center",
                    "behind_subject": True,
                    "animation": "pop",
                    "font_size": 180,
                    "style": {
                        "fontSize": 180,
                        "fontWeight": 900,
                        "color": "#FFFFFF",
                        "outlineColor": "#000000",
                        "outlineWidth": 7,
                        "shadow": True,
                    },
                    "transform": {
                        "position": {"x": 0.5, "y": 0.52},
                        "scale": 1.0,
                    },
                })
            for idx, gr in enumerate(plan_dict.get("text_emphasis_graphics", [])):
                text_overlays.append({
                    "id": f"text_graphic_{idx+1}",
                    "text": gr.get("text", ""),
                    "start_time": float(gr.get("start_time", 0.0)),
                    "duration": float(gr.get("duration", 2.0)),
                    "position": gr.get("position", "center"),
                    "behind_subject": gr.get("behind_subject", False),
                    "animation": gr.get("animation", "pop"),
                })

        # Normalize hook-style behind-subject overlays even when the AI planner already
        # supplied one. This keeps the opening hook visually consistent with the reference
        # treatment instead of silently falling back to subtitle-sized typography.
        for overlay in text_overlays:
            overlay_id = str(overlay.get("id", "")).lower()
            if not overlay.get("behind_subject") or not (
                "hook" in overlay_id or overlay.get("kind") == "opening_hook_typography"
            ):
                continue
            style = overlay.setdefault("style", {})
            style.setdefault("fontSize", 180)
            style.setdefault("fontWeight", 900)
            style.setdefault("color", "#FFFFFF")
            style.setdefault("outlineColor", "#000000")
            style.setdefault("outlineWidth", 7)
            transform = overlay.setdefault("transform", {})
            transform.setdefault("position", {"x": 0.5, "y": 0.52})
            overlay.setdefault("start_time", 0.15)
            overlay.setdefault("duration", 2.8)
            overlay["position"] = "center"

            raw_text = " ".join(str(overlay.get("text", "")).split())
            if raw_text and len(raw_text.split()) == 1 and len(raw_text) <= 18:
                overlay["text"] = "\n".join(list(raw_text.upper()))

        # 3. Resolve audio cues & sfx: extract stinger sfx from shots transitions
        audio_cues = plan_dict.get("audio_cues") or {}
        if not isinstance(audio_cues, dict):
            audio_cues = {}
        sfx_list = audio_cues.get("sfx") or []
        if not sfx_list:
            sfx_list = []
            for idx, shot in enumerate(plan_dict.get("shots", [])):
                trans = shot.get("transition")
                stinger = None
                if isinstance(trans, dict):
                    stinger = trans.get("stinger_sfx")
                if not stinger:
                    stinger = shot.get("stinger_sfx")
                if stinger and isinstance(stinger, dict):
                    sfx_path = stinger.get("path") or stinger.get("file")
                    if sfx_path:
                        sfx_list.append({
                            "id": f"sfx_shot_{shot.get('shot_id', idx+1)}",
                            "file": sfx_path,
                            "time": float(shot.get("start_time", 0.0)),
                            "duration": 0.8,
                            "volume": float(stinger.get("volume", 0.45)),
                        })
            if sfx_list:
                audio_cues["sfx"] = sfx_list

        editorial_spec = plan_dict.get("editorial_spec")
        quality_report = plan_dict.get("quality_report")

        # Dynamically generate editorial intelligence spec if missing and transcript is available
        if not editorial_spec and job.transcript_segments:
            try:
                from ai_broll_autopilot.services.editorial.pipeline import editorial_pipeline
                from ai_broll_autopilot.niches import niche_registry
                from ai_broll_autopilot.styles import style_registry

                n_id = plan_dict.get("niche", {}).get("niche_id", "generic") if isinstance(plan_dict.get("niche"), dict) else "generic"
                s_id = (
                    plan_dict.get("editing_style")
                    or (plan_dict.get("style", {}) or {}).get("style_id")
                    or (plan_dict.get("style", {}) or {}).get("id")
                    or "clean_podcast"
                )
                n_prof = niche_registry.get_profile(n_id)
                s_prof = style_registry.get_style(s_id)

                spec, q_report = editorial_pipeline.process(
                    source_media={
                        "path": job.source_file,
                        "duration": total_dur,
                        "title": job.source_filename,
                    },
                    transcript_segments=job.transcript_segments,
                    video_duration=total_dur,
                    available_broll_assets=[],
                    clip_interval=(float(clip_interval.get("in_point", 0.0)), float(clip_interval.get("out_point", total_dur))),
                    niche_profile=n_prof,
                    style_profile=s_prof,
                )
                editorial_spec = spec.to_dict()
                quality_report = q_report.to_dict()
                plan_dict["editorial_spec"] = editorial_spec
                plan_dict["quality_report"] = quality_report
            except Exception as e:
                logger.warning(f"Could not generate dynamic editorial spec: {e}")

        return EditPlan(
            plan_id=plan_dict.get("plan_id", f"plan_{job.job_id}"),
            title=plan_dict.get("title", f"Edit: {Path(job.source_filename).stem}"),
            target_duration=total_dur,
            source_media=plan_dict.get("source_media", {
                "path": job.source_file,
                "duration": total_dur,
                "title": job.source_filename,
            }),
            clip_interval={
                "in_point": float(clip_interval.get("in_point", 0.0)),
                "out_point": float(clip_interval.get("out_point", total_dur)),
            },
            niche=plan_dict.get("niche", {"niche_id": "generic", "name": "General"}),
            style=plan_dict.get("style", {"style_id": "clean_podcast", "name": "Clean Podcast"}),
            version=plan_dict.get("version", "2.1"),
            cuts=plan_dict.get("cuts", []),
            keep_intervals=plan_dict.get("keep_intervals", []),
            a_roll_ranges=plan_dict.get("a_roll_ranges", []),
            shots=plan_dict.get("shots", []),
            text_overlays=text_overlays,
            graphics=plan_dict.get("graphics", []),
            subtitles=subtitles,
            zooms=plan_dict.get("zooms", []),
            audio_cues=audio_cues,
            cadence_profile=plan_dict.get("cadence_profile", {}),
            editorial_spec=editorial_spec,
            quality_report=quality_report,
            visual_qa=plan_dict.get("visual_qa"),
            review_items=plan_dict.get("review_items", []),
            razor_captions=plan_dict.get("razor_captions", []),
            subtitles_behind_subject=bool(plan_dict.get("subtitles_behind_subject", False)),
            render_settings=plan_dict.get("render_settings", {}),
            render_stale=bool(plan_dict.get("render_stale", False)),
            edit_revision=int(plan_dict.get("edit_revision", 1)),
            openshorts_jobs=plan_dict.get("openshorts_jobs", []),
            last_render_revision=plan_dict.get("last_render_revision"),
        )

    # Fallback when job has no edit plan yet
    dur = 30.0
    fallback_subs = []
    fallback_editorial_spec = None
    fallback_quality_report = None
    if job.transcript_segments:
        for idx, seg in enumerate(job.transcript_segments):
            fallback_subs.append({
                "id": f"sub_{seg.get('id', idx+1)}",
                "startTime": float(seg.get("start", 0.0)),
                "endTime": float(seg.get("end", 0.0)),
                "text": str(seg.get("text", "")).strip(),
                "words": [
                    {
                        "word": w.get("word", ""),
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                    }
                    for w in seg.get("words", [])
                ],
            })
        try:
            from ai_broll_autopilot.services.editorial.pipeline import editorial_pipeline
            from ai_broll_autopilot.niches import niche_registry
            from ai_broll_autopilot.styles import style_registry

            n_prof = niche_registry.get_profile("generic")
            s_prof = style_registry.get_style("clean_podcast")
            spec, q_report = editorial_pipeline.process(
                source_media={"path": job.source_file, "duration": dur, "title": job.source_filename},
                transcript_segments=job.transcript_segments,
                video_duration=dur,
                available_broll_assets=[],
                clip_interval=(0.0, dur),
                niche_profile=n_prof,
                style_profile=s_prof,
            )
            fallback_editorial_spec = spec.to_dict()
            fallback_quality_report = q_report.to_dict()
        except Exception as e:
            logger.warning(f"Could not generate fallback editorial spec: {e}")

    return EditPlan(
        plan_id=f"plan_{job.job_id}",
        title=f"Draft: {Path(job.source_filename).stem}",
        target_duration=dur,
        source_media={"path": job.source_file, "duration": dur, "title": job.source_filename},
        clip_interval={"in_point": 0.0, "out_point": dur},
        niche={"niche_id": "generic", "name": "General"},
        style={"style_id": "clean_podcast", "name": "Clean Podcast"},
        shots=[],
        text_overlays=[],
        subtitles=fallback_subs,
        zooms=[],
        audio_cues={},
        editorial_spec=fallback_editorial_spec,
        quality_report=fallback_quality_report,
    )


def get_editor_adapter(engine_name: Optional[str] = None) -> EditorAdapter:
    """Return the designated EditorAdapter based on configuration or explicit parameter."""
    engine = (engine_name or Config.EDITOR_ENGINE or "openreel").strip().lower()
    if engine == "diffusion":
        return diffusion_adapter
    return openreel_adapter
