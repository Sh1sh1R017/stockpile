"""Edit Director Service generating declarative, non-destructive Edit Plans.

Translates speech transcripts, niche content profiles, and visual style preferences
into structured edit plans compatible with OpenReel.
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.niches import niche_registry, NicheProfile
from ai_broll_autopilot.styles import style_registry, StyleProfile
from ai_broll_autopilot.services.clip_detector import ClipCandidate

logger = logging.getLogger(__name__)


def _clean_json_str(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


@dataclass
class EditPlan:
    """Canonical EditPlan Schema v2.1.
    
    Represents an intelligent, non-destructive edit structure linking:
    - Source media metadata
    - Cuts-First A-roll keep intervals and detected dead-air/filler cuts
    - Contextual, sentiment-aware B-roll shots with strict veto validation
    - Word-level kinetic subtitles in safe area
    - Content-aware motion graphics (numbers, stats, key term badges, lower thirds)
    - Keyframe punch-in camera zooms
    - Multi-track sound design (SFX cues + ducked BGM)
    - Visual QA compliance metrics
    """
    plan_id: str
    title: str
    target_duration: float
    source_media: Dict[str, Any]
    clip_interval: Dict[str, float]       # {"in_point": float, "out_point": float}
    niche: Dict[str, Any]
    style: Dict[str, Any]
    version: str = "2.1"
    cuts: List[Dict[str, Any]] = field(default_factory=list)           # Cuts-First cut candidates
    keep_intervals: List[Any] = field(default_factory=list)            # Contiguous kept intervals
    a_roll_ranges: List[Dict[str, Any]] = field(default_factory=list)  # Mapped A-roll chunks
    shots: List[Dict[str, Any]] = field(default_factory=list)          # B-roll cutaways
    text_overlays: List[Dict[str, Any]] = field(default_factory=list)  # Title / graphic callouts
    graphics: List[Dict[str, Any]] = field(default_factory=list)       # Content-aware kinetic graphics
    subtitles: List[Dict[str, Any]] = field(default_factory=list)      # Word-level timed subtitles
    zooms: List[Dict[str, Any]] = field(default_factory=list)          # Keyframe punch-ins
    audio_cues: Dict[str, Any] = field(default_factory=dict)           # BGM and SFX cues
    cadence_profile: Dict[str, Any] = field(default_factory=dict)      # Rhythm configuration
    editorial_spec: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    visual_qa: Optional[Dict[str, Any]] = None
    review_items: List[Dict[str, Any]] = field(default_factory=list)
    razor_captions: List[Dict[str, Any]] = field(default_factory=list) # Rapid Razor Caption events
    subtitles_behind_subject: bool = False
    hook_text: Optional[str] = None
    render_settings: Dict[str, Any] = field(default_factory=dict)
    render_stale: bool = False
    edit_revision: int = 1
    openshorts_jobs: List[Dict[str, Any]] = field(default_factory=list)
    last_render_revision: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "version": self.version,
            "plan_id": self.plan_id,
            "title": self.title,
            "target_duration": round(self.target_duration, 2),
            "source_media": self.source_media,
            "clip_interval": {
                "in_point": round(self.clip_interval["in_point"], 2),
                "out_point": round(self.clip_interval["out_point"], 2),
            },
            "niche": self.niche,
            "style": self.style,
            "cuts": self.cuts,
            "keep_intervals": self.keep_intervals,
            "a_roll_ranges": self.a_roll_ranges,
            "shots": self.shots,
            "text_overlays": self.text_overlays,
            "graphics": self.graphics,
            "subtitles": self.subtitles,
            "zooms": self.zooms,
            "audio_cues": self.audio_cues,
            "cadence_profile": self.cadence_profile,
            "review_items": self.review_items,
            "razor_captions": self.razor_captions,
            "subtitles_behind_subject": self.subtitles_behind_subject,
            "hook_text": self.hook_text,
            "render_settings": self.render_settings,
            "render_stale": self.render_stale,
            "edit_revision": self.edit_revision,
            "openshorts_jobs": self.openshorts_jobs,
            "last_render_revision": self.last_render_revision,
        }
        if self.editorial_spec:
            d["editorial_spec"] = self.editorial_spec
        if self.quality_report:
            d["quality_report"] = self.quality_report
        if self.visual_qa:
            d["visual_qa"] = self.visual_qa
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EditPlan":
        return cls(
            plan_id=d.get("plan_id", f"plan_{uuid.uuid4().hex[:8]}"),
            title=d.get("title", "Untitled Edit Plan"),
            target_duration=float(d.get("target_duration", 0.0)),
            source_media=d.get("source_media", {}),
            clip_interval=d.get("clip_interval", {"in_point": 0.0, "out_point": float(d.get("target_duration", 0.0))}),
            niche=d.get("niche", {}),
            style=d.get("style", {}),
            version=d.get("version", "2.1"),
            cuts=d.get("cuts", []),
            keep_intervals=d.get("keep_intervals", []),
            a_roll_ranges=d.get("a_roll_ranges", []),
            shots=d.get("shots", []),
            text_overlays=d.get("text_overlays", []),
            graphics=d.get("graphics", []),
            subtitles=d.get("subtitles", []),
            zooms=d.get("zooms", []),
            audio_cues=d.get("audio_cues", {}),
            cadence_profile=d.get("cadence_profile", {}),
            editorial_spec=d.get("editorial_spec"),
            quality_report=d.get("quality_report"),
            visual_qa=d.get("visual_qa"),
            review_items=d.get("review_items", []),
            razor_captions=d.get("razor_captions", []),
            subtitles_behind_subject=bool(d.get("subtitles_behind_subject", False)),
            hook_text=d.get("hook_text"),
            render_settings=d.get("render_settings", {}),
            render_stale=bool(d.get("render_stale", False)),
            edit_revision=int(d.get("edit_revision", 1)),
            openshorts_jobs=d.get("openshorts_jobs", []),
            last_render_revision=d.get("last_render_revision"),
        )


class EditDirectorService:
    """Plans intelligent cuts, B-roll cutaways, subtitles, and graphics based on niche & style."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    async def plan_edit(
        self,
        source_media: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        clip_candidate: Optional[ClipCandidate] = None,
        in_point: Optional[float] = None,
        out_point: Optional[float] = None,
        niche_id: Optional[str] = None,
        style_id: Optional[str] = None,
        custom_hook: Optional[str] = None,
    ) -> EditPlan:
        """Create a complete non-destructive Edit Plan.

        Args:
            source_media: Dict with path, duration, width, height, fps.
            transcript_segments: Whisper speech segments.
            clip_candidate: Optional detected ClipCandidate.
            in_point: Optional override in-point in seconds.
            out_point: Optional override out-point in seconds.
            niche_id: Niche ID (or auto-detect).
            style_id: Style ID (or auto-select).
            custom_hook: Optional custom title/hook card text.

        Returns:
            EditPlan instance.
        """
        # 1. Resolve Clip Boundaries
        if clip_candidate:
            clip_in = clip_candidate.start_time
            clip_out = clip_candidate.end_time
            title = clip_candidate.title
        else:
            clip_in = in_point if in_point is not None else 0.0
            clip_out = out_point if out_point is not None else source_media.get("duration", 60.0)
            title = source_media.get("title", Path(source_media.get("path", "video.mp4")).stem)

        clip_duration = max(1.0, clip_out - clip_in)

        # 2. Filter Transcript Segments for this Clip Interval
        clip_segments = []
        for s in transcript_segments:
            seg_start = s.get("start", 0.0)
            seg_end = s.get("end", 0.0)
            if seg_end > clip_in and seg_start < clip_out:
                # Normalize segment relative to clip start (0.0s)
                clip_segments.append({
                    "start": max(0.0, round(seg_start - clip_in, 2)),
                    "end": min(clip_duration, round(seg_end - clip_in, 2)),
                    "text": s.get("text", "").strip(),
                    "words": s.get("words", []),
                })

        # 3. Resolve Niche and Style Profiles
        niche = niche_registry.get_profile(niche_id)
        style = style_registry.get_style(style_id)

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # -------------------------------------------------------------
        # 4. Cuts-First Retention Analysis
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.retention_engine import retention_engine
        is_podcast = (niche_id == "clean_podcast" or "podcast" in style_id.lower())
        detected_cuts = retention_engine.analyze_and_detect_cuts(
            transcript_segments=clip_segments,
            video_duration=clip_duration,
            is_podcast=is_podcast,
        )
        keep_intervals = retention_engine.compute_keep_intervals(
            video_duration=clip_duration,
            cuts=detected_cuts,
        )

        a_roll_ranges = []
        for s_keep, e_keep in keep_intervals:
            a_roll_ranges.append({
                "start": s_keep,
                "end": e_keep,
                "duration": round(e_keep - s_keep, 2),
                "source_in": round(clip_in + s_keep, 2),
                "source_out": round(clip_in + e_keep, 2),
            })

        cuts_data = [c.to_dict() for c in detected_cuts]

        # -------------------------------------------------------------
        # 5. Execute AI Editorial Intelligence Pipeline
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.editorial.pipeline import editorial_pipeline
        available_assets = []
        try:
            from ai_broll_autopilot.core.database import db
            available_assets = db.list_broll_assets(niche_id=niche_id, limit=60)
        except Exception:
            pass

        spec, quality_report = editorial_pipeline.process(
            source_media=source_media,
            transcript_segments=transcript_segments,
            video_duration=clip_duration,
            available_broll_assets=available_assets,
            custom_hook=custom_hook or (clip_candidate.hook_text if clip_candidate else None),
            clip_interval=(clip_in, clip_out),
            niche_profile=niche,
            style_profile=style,
        )

        # 6. Build Subtitles Structure from Segments
        subtitles = self._build_timed_subtitles(clip_segments, style)

        shots_data = [
            {
                "shot_id": s.shot_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration,
                "category": s.subject_category,
                "search_query": s.search_query,
                "dialogue_trigger": s.reason,
                "rationale": s.reason,
                "narrative_role": s.narrative_role.value,
                "emotional_intent": s.emotional_intent,
                "confidence": s.scores.confidence,
                "pacing_category": s.pacing_category.value,
                "shot_type": s.shot_type.value,
                "asset_path": s.asset_path,
            }
            for s in spec.broll_shots
        ]

        text_overlays_data = [
            {
                "id": c.caption_id,
                "text": c.text,
                "start_time": c.start_time,
                "duration": c.duration,
                "position": c.position,
                "behind_subject": c.behind_subject,
                "emphasis_color": c.highlight_color,
            }
            for c in spec.captions
        ]

        # 6b. Content-Aware Rapid Razor Captions
        razor_captions_data = []
        try:
            from ai_broll_autopilot.services.razor_caption.engine import RazorCaptionEngine
            broll_active_times = [
                (float(s["start_time"]), float(s["end_time"]))
                for s in shots_data if s.get("asset_path")
            ]
            razor_engine = RazorCaptionEngine()
            events = razor_engine.process(
                segments=clip_segments,
                broll_active_times=broll_active_times,
            )
            razor_captions_data = [e.to_edit_plan_entry() for e in events]
        except Exception as re_err:
            logger.warning(f"Could not generate Razor captions: {re_err}")

        # -------------------------------------------------------------
        # 7. Content-Aware Motion Graphics Engine
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.graphics_engine import graphics_engine
        detected_graphics = graphics_engine.generate_graphics(
            transcript_segments=clip_segments,
            video_duration=clip_duration,
            title=title,
            highlight_color=style.highlight_color,
        )
        graphics_data = [g.to_dict() for g in detected_graphics]

        zooms_data = [
            {
                "time": cm.timestamp,
                "scale": cm.scale,
                "duration": cm.duration,
                "reason": cm.reason,
                "easing": "ease-out",
            }
            for cm in spec.camera_moves
        ]

        audio_cues_data = {
            "bgm_ducking": True,
            "bgm_volume": style.bgm_ducking_volume,
            "sfx": [
                {
                    "id": cue.cue_id,
                    "event_type": cue.event_type.value,
                    "time": cue.timestamp,
                    "duration": cue.duration,
                    "file": cue.sound_file,
                    "volume": cue.volume,
                    "reason": cue.reason,
                    "synced_with": cue.synced_with,
                }
                for cue in spec.sfx_cues
            ],
        }

        cadence_profile = {
            "rhythm_pacing": style.broll_cut_pacing,
            "default_shot_duration": style.default_broll_duration,
            "max_broll_ratio": niche.editing.max_broll_ratio,
            "zoom_intensity": style.zoom_intensity,
            "is_podcast": is_podcast,
        }

        # -------------------------------------------------------------
        # 8. Post-Render Visual QA Simulation
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.visual_qa import visual_qa
        qa_result = visual_qa.verify_rendered_video(
            video_path=source_media.get("path", ""),
            target_duration=clip_duration,
        )

        plan = EditPlan(
            plan_id=plan_id,
            title=f"AI Edit: {spec.hook.tightened_text[:40]}",
            target_duration=clip_duration,
            source_media=source_media,
            clip_interval={"in_point": clip_in, "out_point": clip_out},
            niche=niche.to_dict(),
            style=style.to_dict(),
            version="2.1",
            cuts=cuts_data,
            keep_intervals=keep_intervals,
            a_roll_ranges=a_roll_ranges,
            shots=shots_data,
            text_overlays=text_overlays_data,
            graphics=graphics_data,
            subtitles=subtitles,
            razor_captions=razor_captions_data,
            zooms=zooms_data,
            audio_cues=audio_cues_data,
            cadence_profile=cadence_profile,
            editorial_spec=spec.to_dict(),
            quality_report=quality_report.to_dict(),
            visual_qa=qa_result.to_dict(),
            review_items=[
                {"type": "cut", "count": len(cuts_data)},
                {"type": "shot", "count": len(shots_data)},
                {"type": "graphic", "count": len(graphics_data)},
            ],
            render_settings=(
                {
                    "subtitles_enabled": True,
                    "subtitle_style": "cinematic_editorial",
                    "preset": "cinematic_editorial",
                    "subtitle_position": "center",
                    "caption_motion": "word-pop",
                    "words_per_beat": style.caption_words_per_group,
                    "subtitles_behind_subject": False,
                    "custom_colors": {
                        "main": style.primary_color,
                        "second": style.highlight_color,
                    },
                }
                if style.id == "cinematic_social_editorial"
                else {}
            ),
        )

        # -------------------------------------------------------------
        # 9. Iterative Review & Auto-Repair Pass
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.iterative_editor import iterative_editor
        repair_result = iterative_editor.audit_and_repair_plan(plan)
        if repair_result.repaired_items and plan.quality_report:
            plan.quality_report["repaired_items"] = repair_result.repaired_items

        return plan

    async def _plan_with_llm(
        self,
        clip_segments: List[Dict[str, Any]],
        clip_duration: float,
        niche: NicheProfile,
        style: StyleProfile,
        custom_hook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prompt Gemini to create high-retention edit structure respecting niche constraints."""
        max_broll_ratio = niche.editing.max_broll_ratio
        max_broll_seconds = clip_duration * max_broll_ratio
        default_shot_dur = style.default_broll_duration
        target_shots = max(1, min(10, int(round(max_broll_seconds / max(default_shot_dur, 0.5)))))

        formatted_segs = "\n".join([
            f"[{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}"
            for s in clip_segments
        ])

        reference_style_rules = ""
        if style.id == "cinematic_social_editorial":
            reference_style_rules = """
REFERENCE STYLE RULES:
- Open with 0.8–1.3s of clean A-roll, then cut on sentence meaning, reveals, emotional changes, and concrete visual nouns.
- Use B-roll as narrative punctuation; each cutaway must have a literal visual reason tied to the spoken line.
- Prefer 0.8–2.2s B-roll clips, with occasional 2–3 micro-cutaways inside a longer sentence when the visual meaning changes.
- Keep the speaker present between visual inserts; never cover an entire thought with unrelated footage.
- Use large white sentence-aware captions, usually 2–4 words visible at once, centered or slightly above center. Use restrained pale-green emphasis for important words.
- Avoid giant all-caps meme captions, neon styling, constant zooms, and decorative transitions.
- Keep A-roll punch-ins subtle (1.02–1.045x) and only at high-impact moments.
- Use hard cuts by default and reserve SFX for major punctuation.
- Prefer cinematic/archival/documentary imagery and specific real-world visual metaphors over generic stock people smiling at cameras.
- Maintain a black/near-black breathing canvas around framed vertical imagery when possible.
"""

        prompt = f"""You are the Master AI Video Editor & Director for high-retention vertical short-form video (TikTok, YouTube Shorts, Instagram Reels).

CONTENT NICHE: {niche.name} ({niche.id})
DESCRIPTION: {niche.description}
VISUAL KEYWORDS: {', '.join(niche.visual_keywords[:15])}
B-ROLL CATEGORIES: {', '.join(niche.broll_categories)}
AVOID: {', '.join(niche.avoid)}

VISUAL STYLE: {style.name}
DEFAULT B-ROLL PACING: {style.broll_cut_pacing} (~{default_shot_dur}s per shot)
TOTAL CLIP DURATION: {clip_duration:.1f}s
MAX B-ROLL COVERAGE: {max_broll_ratio*100:.0f}% (~{max_broll_seconds:.1f}s total B-roll)
TARGET NUMBER OF B-ROLL SHOTS: {target_shots}

{reference_style_rules}

DIRECTOR RULES:
1. The speaker's face MUST be visible for the opening hook (first 0.8s to 1.3s).
2. Cutaways MUST directly illustrate spoken keywords, objects, actions, places, claims, or emotional consequences in the transcript.
3. Every B-roll shot MUST specify a clean, 4-8 word literal retrieval query tailored to the exact visual event.
4. Prefer 1-3 meaningful text overlays only when they reinforce a hook, named entity, number, or punchline; do not decorate every sentence.
5. Add subtle punch-in keyframes only for genuinely emphatic A-roll moments, never as automatic filler.
6. Audio: duck BGM to {style.bgm_ducking_volume} during spoken dialogue; use whoosh/impact SFX selectively on major visual punctuation.

CLIP TRANSCRIPT:
{formatted_segs}

Respond ONLY with valid JSON matching:
{{
  "hook_title": "{custom_hook or 'KEY TAKEAWAY'}",
  "text_overlays": [
    {{
      "id": "overlay_1",
      "text": "HOOK PHRASE",
      "start_time": 0.5,
      "duration": 2.0,
      "position": "center",
      "emphasis_color": "{style.highlight_color}"
    }}
  ],
  "shots": [
    {{
      "shot_id": "broll_1",
      "start_time": <seconds relative to 0.0>,
      "end_time": <seconds>,
      "duration": <seconds>,
      "category": "<one of the broll categories>",
      "search_query": "<2-4 search keywords for footage>",
      "dialogue_trigger": "<quote from transcript>",
      "rationale": "<why this cutaway enhances viewer retention>"
    }}
  ],
  "zooms": [
    {{
      "time": <seconds>,
      "scale": {style.zoom_intensity},
      "duration": 0.3,
      "easing": "ease-out"
    }}
  ],
  "audio_cues": {{
    "bgm_ducking": true,
    "bgm_volume": {style.bgm_ducking_volume},
    "sfx_triggers": [
      {{"time": 0.5, "sound": "whoosh", "volume": 0.4}}
    ]
  }}
}}"""

        models_to_try = [self.model_name] + [m for m in getattr(Config, "GEMINI_FALLBACK_MODELS", []) if m != self.model_name]
        response = None
        last_err = None
        for model_cand in models_to_try:
            try:
                def _call_model(cand=model_cand):
                    return self.client.models.generate_content(
                        model=cand,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            http_options=types.HttpOptions(
                                retry_options=types.HttpRetryOptions(attempts=1),
                                timeout=10000,
                            )
                        )
                    )
                response = await asyncio.to_thread(_call_model)
                if response and response.text:
                    break
            except Exception as me:
                last_err = me
                continue
        if not response or not response.text:
            raise last_err or RuntimeError("No response from Gemini")

        raw_json = _clean_json_str(response.text)
        return json.loads(raw_json)

    def _plan_algorithmic(
        self,
        clip_segments: List[Dict[str, Any]],
        clip_duration: float,
        niche: NicheProfile,
        style: StyleProfile,
        custom_hook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deterministic rule-based edit director respecting niche and style parameters."""
        max_broll_seconds = clip_duration * niche.editing.max_broll_ratio
        shot_duration = style.default_broll_duration
        reference_style = style.id == "cinematic_social_editorial"
        min_broll = getattr(style, "broll_min_duration", 1.2)
        max_broll = getattr(style, "broll_max_duration", 2.4)
        shot_duration = getattr(style, "default_broll_duration", shot_duration)
        target_shots = max(1, min(10, int(round(max_broll_seconds / max(0.5, shot_duration)))))

        # 1. Identify visual keywords spoken in segments
        niche_kws = {kw.lower(): kw for kw in niche.visual_keywords}
        keyword_hits = []

        for seg in clip_segments:
            st = seg["start"]
            # Skip first 1.0s to preserve speaker hook
            if st < 1.0:
                continue
            text_lower = seg["text"].lower()
            for kw_lower, kw_orig in niche_kws.items():
                if kw_lower in text_lower:
                    keyword_hits.append({
                        "time": st,
                        "keyword": kw_orig,
                        "text": seg["text"],
                    })

        # 2. Schedule B-Roll shots spaced across the timeline
        shots = []
        allocated_time = 1.5  # Start after initial face hook
        step = (
            max(2.0, (clip_duration - 2.0) / (target_shots + 1))
            if reference_style
            else max(3.0, (clip_duration - 2.0) / (target_shots + 1))
        )

        for i in range(target_shots):
            shot_start = round(allocated_time, 2)
            target_dur = min(max_broll, max(min_broll, shot_duration))
            shot_end = round(min(clip_duration - 0.5, shot_start + target_dur), 2)
            actual_dur = round(shot_end - shot_start, 2)
            if actual_dur < max(0.5, min_broll * 0.75):
                break

            # Find matching keyword near this timestamp if possible
            matched_kw = niche.visual_keywords[i % len(niche.visual_keywords)]
            for hit in keyword_hits:
                if abs(hit["time"] - shot_start) <= 2.5:
                    matched_kw = hit["keyword"]
                    break

            cat = niche.broll_categories[i % len(niche.broll_categories)]

            shots.append({
                "shot_id": f"broll_{i+1}",
                "start_time": shot_start,
                "end_time": shot_end,
                "duration": actual_dur,
                "category": cat,
                "search_query": (
                    f"{matched_kw} real world documentary footage"
                    if reference_style
                    else f"{niche.name} {matched_kw}"
                ),
                "dialogue_trigger": f"Illustrates {matched_kw}",
                "rationale": (
                    f"Reference-style literal visual punctuation for '{matched_kw}' in {niche.name}."
                    if reference_style
                    else f"Contextual cutaway matching topic '{matched_kw}' in {niche.name}."
                ),
            })

            allocated_time += actual_dur + step

        # 3. Create Hook Overlay Card
        hook_text = custom_hook
        if not hook_text and clip_segments:
            first_words = clip_segments[0]["text"].split()[:5]
            hook_text = " ".join(first_words).upper()
        if not hook_text:
            hook_text = niche.name.upper()

        text_overlays = [{
            "id": "overlay_hook",
            "text": hook_text,
            "start_time": 0.4,
            "duration": 2.2,
            "position": "center",
            "emphasis_color": style.highlight_color,
        }]

        # 4. Schedule Punch-in Zooms
        zooms = []
        zoom_times = [round(clip_duration * 0.35, 2), round(clip_duration * 0.70, 2)]
        for zt in zoom_times:
            if zt < clip_duration - 2.0:
                zooms.append({
                    "time": zt,
                    "scale": style.zoom_intensity,
                    "duration": 0.25,
                    "easing": "ease-out",
                })

        # 5. Audio Cues
        sfx_triggers = []
        for shot in shots:
            if reference_style and len(sfx_triggers) % 3 != 0:
                continue
            sfx_triggers.append({
                "time": shot["start_time"],
                "sound": "whoosh",
                "volume": 0.20 if reference_style else 0.35,
            })

        audio_cues = {
            "bgm_ducking": True,
            "bgm_volume": style.bgm_ducking_volume,
            "sfx_triggers": sfx_triggers,
        }

        return {
            "hook_title": hook_text,
            "text_overlays": text_overlays,
            "shots": shots,
            "zooms": zooms,
            "audio_cues": audio_cues,
        }

    def _build_timed_subtitles(
        self,
        clip_segments: List[Dict[str, Any]],
        style: StyleProfile,
    ) -> List[Dict[str, Any]]:
        """Construct word-level timed subtitle structures compatible with OpenReel."""
        subtitles = []
        for i, seg in enumerate(clip_segments):
            st = seg["start"]
            et = seg["end"]
            text = seg["text"].strip()
            if not text:
                continue

            words = seg.get("words", [])
            timed_words = []

            if words:
                for w in words:
                    timed_words.append({
                        "text": w.get("word", "").strip(),
                        "startTime": max(0.0, round(w.get("start", st), 2)),
                        "endTime": max(0.0, round(w.get("end", et), 2)),
                    })
            else:
                # Interpolate word timings if not present in transcript segment
                raw_words = text.split()
                if raw_words:
                    word_dur = (et - st) / len(raw_words)
                    for j, rw in enumerate(raw_words):
                        timed_words.append({
                            "text": rw,
                            "startTime": round(st + j * word_dur, 2),
                            "endTime": round(st + (j + 1) * word_dur, 2),
                        })

            subtitles.append({
                "id": f"sub_{i+1:03d}",
                "text": text,
                "startTime": st,
                "endTime": et,
                "animationStyle": style.caption_animation_style,
                "motionProfile": "word-pop",
                "motionRecipe": "motion-anything:word-pop",
                "behind_subject": False,
                "style": style.to_openreel_subtitle_style(),
                "words": timed_words,
            })

        return subtitles


# Global instance
edit_director = EditDirectorService()
