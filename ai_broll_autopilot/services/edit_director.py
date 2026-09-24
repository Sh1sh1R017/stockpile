"""Edit Director Service generating declarative, non-destructive Edit Plans.

Translates speech transcripts, niche content profiles, and visual style preferences
into structured edit plans compatible with OpenReel.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai

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
    """Complete declarative edit plan ready for OpenReel project generation."""
    plan_id: str
    title: str
    target_duration: float
    source_media: Dict[str, Any]
    clip_interval: Dict[str, float]       # {"in_point": float, "out_point": float}
    niche: Dict[str, Any]
    style: Dict[str, Any]
    shots: List[Dict[str, Any]] = field(default_factory=list)          # B-roll cutaways
    text_overlays: List[Dict[str, Any]] = field(default_factory=list)  # Title / graphic callouts
    subtitles: List[Dict[str, Any]] = field(default_factory=list)      # Word-level timed subtitles
    zooms: List[Dict[str, Any]] = field(default_factory=list)          # Keyframe punch-ins
    audio_cues: Dict[str, Any] = field(default_factory=dict)           # BGM and SFX cues

    def to_dict(self) -> Dict[str, Any]:
        return {
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
            "shots": self.shots,
            "text_overlays": self.text_overlays,
            "subtitles": self.subtitles,
            "zooms": self.zooms,
            "audio_cues": self.audio_cues,
        }


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

        # 4. Generate Edit Elements (LLM with deterministic algorithmic fallback)
        plan_data = None
        if self.client and len(clip_segments) > 0:
            try:
                plan_data = await self._plan_with_llm(
                    clip_segments=clip_segments,
                    clip_duration=clip_duration,
                    niche=niche,
                    style=style,
                    custom_hook=custom_hook or (clip_candidate.hook_text if clip_candidate else None),
                )
            except Exception as e:
                logger.warning(f"LLM edit planning failed: {e}. Falling back to algorithmic planner.")

        if not plan_data:
            plan_data = self._plan_algorithmic(
                clip_segments=clip_segments,
                clip_duration=clip_duration,
                niche=niche,
                style=style,
                custom_hook=custom_hook or (clip_candidate.hook_text if clip_candidate else None),
            )

        # 5. Build Subtitles Structure from Segments
        subtitles = self._build_timed_subtitles(clip_segments, style)

        return EditPlan(
            plan_id=plan_id,
            title=title,
            target_duration=clip_duration,
            source_media=source_media,
            clip_interval={"in_point": clip_in, "out_point": clip_out},
            niche=niche.to_dict(),
            style=style.to_dict(),
            shots=plan_data.get("shots", []),
            text_overlays=plan_data.get("text_overlays", []),
            subtitles=subtitles,
            zooms=plan_data.get("zooms", []),
            audio_cues=plan_data.get("audio_cues", {}),
        )

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
        target_shots = max(1, min(6, int(max_broll_seconds / default_shot_dur)))

        formatted_segs = "\n".join([
            f"[{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}"
            for s in clip_segments
        ])

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

DIRECTOR RULES:
1. The speaker's face MUST be visible for the opening hook (first 0.8s to 1.5s).
2. Cutaways MUST directly illustrate spoken keywords or concepts in the transcript.
3. Every B-roll shot MUST specify a clean, 2-4 keyword "search_query" tailored to the niche vocabulary.
4. Add 1-3 high-impact kinetic text overlays (e.g. hook title card at 0.5s–2.0s, key terms, or punchlines).
5. Add 2-4 subtle zoom punch-in keyframes (scale {style.zoom_intensity:.2f}) on emphatic sentences or punchlines.
6. Audio: duck BGM to {style.bgm_ducking_volume} during spoken dialogue; trigger whoosh SFX on B-roll cuts.

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

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

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
        target_shots = max(1, min(5, int(max_broll_seconds / max(1.0, shot_duration))))

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
        step = max(3.0, (clip_duration - 2.0) / (target_shots + 1))

        for i in range(target_shots):
            shot_start = round(allocated_time, 2)
            shot_end = round(min(clip_duration - 0.5, shot_start + shot_duration), 2)
            actual_dur = round(shot_end - shot_start, 2)
            if actual_dur < 1.0:
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
                "search_query": f"{niche.name} {matched_kw}",
                "dialogue_trigger": f"Illustrates {matched_kw}",
                "rationale": f"Contextual cutaway matching topic '{matched_kw}' in {niche.name}.",
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
            sfx_triggers.append({
                "time": shot["start_time"],
                "sound": "whoosh",
                "volume": 0.35,
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
                "style": style.to_openreel_subtitle_style(),
                "words": timed_words,
            })

        return subtitles


# Global instance
edit_director = EditDirectorService()
