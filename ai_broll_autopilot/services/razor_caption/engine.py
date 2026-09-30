"""Rapid Razor Caption Engine — top-level orchestrator.

Connects:
  RazorSegmenter → ImportanceScorer → EnergyAnalyzer →
  SpatialEngine → CaptionStateMachine → SfxMapper

Output:
  - List[CaptionEvent]  (enriched, ready for rendering)
  - EditPlan razor_captions list  (serializable JSON schema)
  - ASS subtitle file via existing SubtitleEngine (for FFmpeg burn-in)

Extreme impact words get a dedicated ASS overlay animation that starts tiny,
flies toward the viewer, overshoots and settles. The edit-plan also carries
camera-punch metadata for renderers that support timeline video effects.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .caption_event import CaptionEvent, CaptionMode, EmphasisLevel, SpatialRegion
from .segmenter import RazorSegmenter
from .importance_scorer import ImportanceScorer
from .energy_analyzer import EnergyAnalyzer
from .spatial_engine import SpatialEngine
from .state_machine import CaptionStateMachine
from .sfx_mapper import SfxMapper

logger = logging.getLogger(__name__)


class RazorCaptionEngine:
    """Full pipeline: words in → enriched CaptionEvents + EditPlan schema out."""

    def __init__(
        self,
        mode: CaptionMode = CaptionMode.RAPID_RAZOR,
        enable_behind_subject: bool = True,
        enable_sfx: bool = True,
        max_group_size: int = 5,
        sound_designer=None,
        hook_threshold: float = 0.78,
        strong_threshold: float = 0.62,
        moderate_threshold: float = 0.44,
        preset_name: str = "hormozi",
    ):
        self.mode = mode
        self.segmenter = RazorSegmenter(max_group_size=max_group_size, mode=mode)
        self.preset_name = preset_name
        self.scorer = ImportanceScorer(
            hook_threshold=hook_threshold,
            strong_threshold=strong_threshold,
            moderate_threshold=moderate_threshold,
            enable_behind_subject=enable_behind_subject,
            preset_name=preset_name,
        )
        self.energy_analyzer = EnergyAnalyzer()
        self.spatial_engine = SpatialEngine(enable_subject_avoidance=True)
        self.state_machine = CaptionStateMachine()
        self.sfx_mapper = SfxMapper(sound_designer=sound_designer if enable_sfx else None)

    def process(
        self,
        segments: List[Dict[str, Any]],
        subject_info: Optional[Dict[str, Any]] = None,
        broll_active_times: Optional[List[Tuple[float, float]]] = None,
        beat_times: Optional[List[float]] = None,
        mode: Optional[CaptionMode] = None,
    ) -> List[CaptionEvent]:
        effective_mode = mode or self.mode
        words = self.segmenter.flatten_from_segments(segments)
        if not words:
            logger.warning("RazorCaptionEngine: no words found in segments")
            return []
        events = self.segmenter.segment(words, segments=segments)
        events = self.scorer.score(events)
        events = self.energy_analyzer.analyze(events)
        events = self.spatial_engine.place(
            events,
            subject_info=subject_info,
            broll_active_times=broll_active_times or [],
        )
        events = self.state_machine.wire(events)
        events = self.sfx_mapper.map(events)
        if beat_times:
            events = self._align_beats(events, beat_times)
        for ev in events:
            ev.mode = effective_mode
        logger.info(
            "RazorCaptionEngine: processed %d events | HOOK=%d STRONG=%d MODERATE=%d NORMAL=%d",
            len(events),
            sum(1 for e in events if e.emphasis == EmphasisLevel.HOOK),
            sum(1 for e in events if e.emphasis == EmphasisLevel.STRONG),
            sum(1 for e in events if e.emphasis == EmphasisLevel.MODERATE),
            sum(1 for e in events if e.emphasis.value == 0),
        )
        return events

    def to_edit_plan(self, events: List[CaptionEvent]) -> List[Dict[str, Any]]:
        return [ev.to_edit_plan_entry() for ev in events]

    def to_subtitles(self, events: List[CaptionEvent], preset_name: str = "hormozi") -> List[Dict[str, Any]]:
        """Convert CaptionEvents to canonical EditPlan subtitles format."""
        from .presets import get_preset
        preset = get_preset(preset_name)
        phrases: Dict[int, List[CaptionEvent]] = {}
        for ev in events:
            phrases.setdefault(ev.phrase_id, []).append(ev)

        rechunked: Dict[int, List[CaptionEvent]] = {}
        idx = 0
        for pid in sorted(phrases.keys()):
            ev_list = phrases[pid]
            if len(ev_list) > 4:
                for k in range(0, len(ev_list), 3):
                    rechunked[idx] = ev_list[k:k + 3]
                    idx += 1
            else:
                rechunked[idx] = ev_list
                idx += 1

        subtitles = []
        for p_id in sorted(rechunked.keys()):
            group = rechunked[p_id]
            if not group:
                continue
            words_meta = [
                {
                    "word": ev.word,
                    "start": round(ev.start_time, 4),
                    "end": round(ev.end_time, 4),
                    "semantic_type": ev.semantic_type,
                    "emoji": ev.emoji,
                    "emphasis": ev.emphasis.value,
                    "layer": ev.layer.value,
                    "motionRecipe": ev.motion_recipe,
                    "motionParams": ev.motion_params or {},
                    "videoEffect": ev.video_effect,
                }
                for ev in group
            ]
            # The most important word controls the group-level OpenReel recipe;
            # ordinary words remain normal while the hero word can fly toward the camera.
            hero = max(group, key=lambda ev: (ev.word_importance_score, ev.emphasis.value))
            has_behind = any(ev.requires_behind_subject for ev in group)
            subtitles.append({
                "id": f"sub_{p_id+1:03d}",
                "text": " ".join(ev.word for ev in group),
                "startTime": round(group[0].start_time, 4),
                "endTime": round(group[-1].end_time, 4),
                "animationStyle": hero.motion_recipe.split(":")[-1] if hero.motion_recipe else preset.default_animation,
                "motionProfile": hero.motion_recipe.split(":")[-1] if hero.motion_recipe else preset.default_animation,
                "motionRecipe": hero.motion_recipe or f"motion-anything:{preset.default_animation}",
                "motionParams": hero.motion_params or {},
                "videoEffect": hero.video_effect,
                "behind_subject": has_behind,
                "behindSubject": has_behind,
                "position": hero.region.value,
                "spatial_region": hero.region.value,
                "style": {
                    "fontFamily": preset.font_family,
                    "fontSize": preset.font_size,
                    "color": preset.fill_color,
                    "highlightColor": preset.highlight_color,
                    "strokeColor": preset.stroke_color,
                    "strokeWidth": preset.stroke_width,
                    "preset": preset.key,
                    "uppercase": preset.uppercase,
                    "letterSpacing": preset.letter_spacing,
                    "lineHeight": preset.line_spacing,
                },
                "words": words_meta,
            })
        return subtitles

    def generate_ass(
        self,
        events: List[CaptionEvent],
        output_path: Path,
        style_preset: str = "hormozi",
        position: str = "bottom",
    ) -> Path:
        """Generate the normal ASS layer plus real extreme-word ASS animations."""
        from ..subtitle_engine import SubtitleEngine
        segments = self._events_to_segments(events)
        engine = SubtitleEngine()
        text_emphasis_events = []
        for ev in events:
            if ev.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.HOOK):
                text_emphasis_events.append({
                    "start_time": ev.start_time,
                    "duration": ev.duration,
                    "text": ev.word,
                    "color": "yellow" if ev.emphasis == EmphasisLevel.HOOK else "pink",
                })

        result = engine.generate_ass_file(
            segments=segments,
            output_path=output_path,
            style_preset=style_preset,
            position=position,
            text_emphasis_events=text_emphasis_events if text_emphasis_events else None,
        )
        self._append_camera_impact_events(output_path, events)
        return result

    @staticmethod
    def _ass_time(seconds: float) -> str:
        total_cs = max(0, int(round(seconds * 100)))
        h, rem = divmod(total_cs, 360000)
        m, rem = divmod(rem, 6000)
        s, cs = divmod(rem, 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    @classmethod
    def _append_camera_impact_events(cls, output_path: Path, events: List[CaptionEvent]) -> None:
        """Append oversized ASS events that visually fly toward the viewer.

        ASS transforms provide a real render-time scale/rotation/blur animation,
        so this is not merely metadata for a future editor.
        """
        extreme = [e for e in events if e.motion_recipe == "kinetic:word-impact-camera"]
        if not extreme:
            return

        text = output_path.read_text(encoding="utf-8")
        if "[Events]" not in text:
            return
        additions: List[str] = []
        for ev in extreme:
            start = max(0.0, ev.start_time)
            end = max(start + 0.20, ev.end_time)
            dur_ms = min(560, max(240, int((end - start) * 1000)))
            impact_ms = min(360, max(180, int(dur_ms * 0.64)))
            settle_ms = min(dur_ms, impact_ms + 180)
            # Start tiny, accelerate toward camera, overshoot, then settle.
            # The oversized text intentionally clips at the frame edge.
            anim = (
                "{\\an5\\pos(540,960)\\bord8\\shad5\\blur3"
                "\\fscx18\\fscy18\\frz-4"
                f"\\t(0,{impact_ms},\\fscx172\\fscy172\\blur0\\frz2)"
                f"\\t({impact_ms},{settle_ms},\\fscx125\\fscy125\\frz0)"
                f"\\t({settle_ms},{dur_ms},\\fscx100\\fscy100)}}"
            )
            clean = str(ev.word).replace("{", "\\{").replace("}", "\\}")
            additions.append(
                f"Dialogue: 10,{cls._ass_time(start)},{cls._ass_time(end)},Default,,0,0,0,,{anim}{clean}"
            )

        marker = "\n".join(additions) + "\n"
        text = text.rstrip() + "\n" + marker
        output_path.write_text(text, encoding="utf-8")

    def generate_behind_subject_ass(
        self,
        events: List[CaptionEvent],
        output_path: Path,
        style_preset: str = "hormozi",
    ) -> Optional[Path]:
        """Generate behind-subject ASS layer for HOOK words only."""
        from ..subtitle_engine import SubtitleEngine
        from .caption_event import LayerMode
        behind_events = [ev for ev in events if ev.layer == LayerMode.BEHIND_SUBJECT]
        if not behind_events:
            return None
        segments = self._events_to_segments(behind_events, mark_behind_subject=True)
        engine = SubtitleEngine()
        return engine.generate_ass_file(
            segments=segments,
            output_path=output_path,
            style_preset=style_preset,
            only_behind_subject=True,
        )

    def summary(self, events: List[CaptionEvent]) -> Dict[str, Any]:
        from .energy_analyzer import EnergyLevel
        return {
            "total_events": len(events),
            "hook_words": [e.word for e in events if e.emphasis == EmphasisLevel.HOOK],
            "strong_words": [e.word for e in events if e.emphasis == EmphasisLevel.STRONG],
            "behind_subject_words": [e.word for e in events if e.requires_behind_subject],
            "camera_impact_words": [e.word for e in events if e.motion_recipe == "kinetic:word-impact-camera"],
            "energy_distribution": {
                "low": sum(1 for e in events if e.energy == EnergyLevel.LOW),
                "medium": sum(1 for e in events if e.energy == EnergyLevel.MEDIUM),
                "high": sum(1 for e in events if e.energy == EnergyLevel.HIGH),
            },
            "sfx_events": {
                e.sfx_event: sum(1 for ev in events if ev.sfx_event == e.sfx_event)
                for e in events if e.sfx_event
            },
            "regions": {
                r.value: sum(1 for e in events if e.region == r)
                for r in SpatialRegion
            },
        }

    @staticmethod
    def _events_to_segments(events: List[CaptionEvent], mark_behind_subject: bool = False) -> List[Dict[str, Any]]:
        if not events:
            return []
        phrases: Dict[int, List[CaptionEvent]] = {}
        for ev in events:
            phrases.setdefault(ev.phrase_id, []).append(ev)
        segments = []
        for phrase_id in sorted(phrases.keys()):
            group = phrases[phrase_id]
            words = [{"word": ev.word, "start": ev.start_time, "end": ev.end_time} for ev in group]
            segments.append({
                "text": " ".join(ev.word for ev in group),
                "start": group[0].start_time,
                "end": group[-1].end_time,
                "words": words,
                "behind_subject": mark_behind_subject,
            })
        return segments

    @staticmethod
    def _align_beats(events: List[CaptionEvent], beat_times: List[float]) -> List[CaptionEvent]:
        MAX_SNAP_SEC = 0.12
        for ev in events:
            if not ev.segment_break_before:
                continue
            nearest = min(beat_times, key=lambda b: abs(b - ev.start_time), default=None)
            if nearest is None:
                continue
            if abs(nearest - ev.start_time) <= MAX_SNAP_SEC:
                ev.start_time = nearest
                ev.beat_aligned = True
                ev.nearest_beat_time = nearest
        return events
