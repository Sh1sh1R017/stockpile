"""Rapid Razor Caption Engine — top-level orchestrator.

Connects:
  RazorSegmenter → ImportanceScorer → EnergyAnalyzer →
  SpatialEngine → CaptionStateMachine → SfxMapper

Output:
  - List[CaptionEvent]  (enriched, ready for rendering)
  - EditPlan razor_captions list  (serializable JSON schema)
  - ASS subtitle file via existing SubtitleEngine (for FFmpeg burn-in)

The engine operates in RAPID_RAZOR mode by default but can be set to
NORMAL / MINIMAL / USER_STYLE via the mode parameter.  It does NOT
auto-apply RAPID_RAZOR everywhere — the caller controls mode selection.

GPU-friendly precompute: all timing, position, animation, and mask
relationships are resolved offline in a single sequential pass.
Nothing is computed at render time.

Usage:
    engine = RazorCaptionEngine()
    events = engine.process(
        segments=transcript_segments,
        subject_info=subject_layout_dict,
        mode=CaptionMode.RAPID_RAZOR,
    )
    razor_captions = engine.to_edit_plan(events)
    ass_path = engine.generate_ass(events, output_path=Path("/tmp/razor.ass"))
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .caption_event import CaptionEvent, CaptionMode, EmphasisLevel, SpatialRegion
from .segmenter import RazorSegmenter
from .importance_scorer import ImportanceScorer
from .energy_analyzer import EnergyAnalyzer
from .spatial_engine import SpatialEngine, SubjectBoundingBox
from .state_machine import CaptionStateMachine
from .sfx_mapper import SfxMapper

logger = logging.getLogger(__name__)


class RazorCaptionEngine:
    """Full pipeline: words in → enriched CaptionEvents + EditPlan schema out.

    Parameters
    ----------
    mode : CaptionMode
        Default mode.  Caller should pass mode per-clip.
    enable_behind_subject : bool
        Whether to allow behind-subject compositing for HOOK words.
    enable_sfx : bool
        Whether to assign SFX events (can be disabled by user).
    max_group_size : int
        Maximum words per razor segment (default 5).
    sound_designer : optional
        SoundDesigner instance for blacklist check.  Pass None to skip.
    """

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
    ):
        self.mode = mode
        self.segmenter = RazorSegmenter(max_group_size=max_group_size, mode=mode)
        self.scorer = ImportanceScorer(
            hook_threshold=hook_threshold,
            strong_threshold=strong_threshold,
            moderate_threshold=moderate_threshold,
            enable_behind_subject=enable_behind_subject,
        )
        self.energy_analyzer = EnergyAnalyzer()
        self.spatial_engine = SpatialEngine(enable_subject_avoidance=True)
        self.state_machine = CaptionStateMachine()
        self.sfx_mapper = SfxMapper(sound_designer=sound_designer if enable_sfx else None)

    # ── Primary entry point ────────────────────────────────────────────────

    def process(
        self,
        segments: List[Dict[str, Any]],
        subject_info: Optional[Dict[str, Any]] = None,
        broll_active_times: Optional[List[Tuple[float, float]]] = None,
        beat_times: Optional[List[float]] = None,
        mode: Optional[CaptionMode] = None,
    ) -> List[CaptionEvent]:
        """Full pipeline pass.

        Args:
            segments: Sentence/word-level transcript segments.
                      Each segment must have 'words' list with word/start/end.
            subject_info: Dict from SubjectIsolationService.analyze_subject_layout().
                          Used for spatial placement and behind-subject decisions.
            broll_active_times: List of (start_sec, end_sec) B-roll windows.
            beat_times: Optional list of beat timestamps for beat alignment.
            mode: Override per-call mode.

        Returns:
            List of fully enriched CaptionEvents, ready for rendering.
        """
        effective_mode = mode or self.mode

        # 1. Flatten segments → word list
        words = self.segmenter.flatten_from_segments(segments)
        if not words:
            logger.warning("RazorCaptionEngine: no words found in segments")
            return []

        # 2. Razor segmentation
        events = self.segmenter.segment(words, segments=segments)

        # 3. Importance scoring + emphasis assignment
        events = self.scorer.score(events)

        # 4. Energy analysis (window-level)
        events = self.energy_analyzer.analyze(events)

        # 5. Spatial placement (subject-aware, collision-resolved)
        events = self.spatial_engine.place(
            events,
            subject_info=subject_info,
            broll_active_times=broll_active_times or [],
        )

        # 6. State machine: wire animations
        events = self.state_machine.wire(events)

        # 7. SFX mapping
        events = self.sfx_mapper.map(events)

        # 8. Beat alignment (optional, speech timing takes priority)
        if beat_times:
            events = self._align_beats(events, beat_times)

        # 9. Stamp mode on all events
        for ev in events:
            ev.mode = effective_mode

        logger.info(
            "RazorCaptionEngine: processed %d events | "
            "HOOK=%d STRONG=%d MODERATE=%d NORMAL=%d",
            len(events),
            sum(1 for e in events if e.emphasis == EmphasisLevel.HOOK),
            sum(1 for e in events if e.emphasis == EmphasisLevel.STRONG),
            sum(1 for e in events if e.emphasis == EmphasisLevel.MODERATE),
            sum(1 for e in events if e.emphasis.value == 0),
        )
        return events

    # ── Output serializers ─────────────────────────────────────────────────

    def to_edit_plan(self, events: List[CaptionEvent]) -> List[Dict[str, Any]]:
        """Serialize events to EditPlan razor_captions schema."""
        return [ev.to_edit_plan_entry() for ev in events]

    def generate_ass(
        self,
        events: List[CaptionEvent],
        output_path: Path,
        style_preset: str = "hormozi",
        position: str = "bottom",
    ) -> Path:
        """Generate an ASS subtitle file from CaptionEvents via SubtitleEngine.

        Converts events back to segment dicts that SubtitleEngine understands,
        preserving word-level timing.  This enables FFmpeg burn-in with the
        existing behind-subject compositing pipeline.
        """
        from ..subtitle_engine import SubtitleEngine

        segments = self._events_to_segments(events)
        engine = SubtitleEngine()

        # Text emphasis events for STRONG / HOOK (Level3 styles)
        text_emphasis_events = []
        for ev in events:
            if ev.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.HOOK):
                text_emphasis_events.append({
                    "start_time": ev.start_time,
                    "duration": ev.duration,
                    "text": ev.word,
                    "color": "yellow" if ev.emphasis == EmphasisLevel.HOOK else "pink",
                })

        return engine.generate_ass_file(
            segments=segments,
            output_path=output_path,
            style_preset=style_preset,
            position=position,
            text_emphasis_events=text_emphasis_events if text_emphasis_events else None,
        )

    def generate_behind_subject_ass(
        self,
        events: List[CaptionEvent],
        output_path: Path,
        style_preset: str = "hormozi",
    ) -> Optional[Path]:
        """Generate behind-subject ASS layer for HOOK words only.

        Returns None if no events require behind-subject compositing.
        """
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
        """Return a human-readable summary dict for debugging/QA."""
        from .energy_analyzer import EnergyLevel
        return {
            "total_events": len(events),
            "hook_words": [e.word for e in events if e.emphasis == EmphasisLevel.HOOK],
            "strong_words": [e.word for e in events if e.emphasis == EmphasisLevel.STRONG],
            "behind_subject_words": [e.word for e in events if e.requires_behind_subject],
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

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _events_to_segments(
        events: List[CaptionEvent],
        mark_behind_subject: bool = False,
    ) -> List[Dict[str, Any]]:
        """Convert CaptionEvents back to subtitle-engine-compatible segment dicts."""
        if not events:
            return []

        # Group events by phrase_id → one segment per phrase
        phrases: Dict[int, List[CaptionEvent]] = {}
        for ev in events:
            phrases.setdefault(ev.phrase_id, []).append(ev)

        segments = []
        for phrase_id in sorted(phrases.keys()):
            group = phrases[phrase_id]
            words = [
                {
                    "word": ev.word,
                    "start": ev.start_time,
                    "end": ev.end_time,
                }
                for ev in group
            ]
            seg = {
                "text": " ".join(ev.word for ev in group),
                "start": group[0].start_time,
                "end": group[-1].end_time,
                "words": words,
                "behind_subject": mark_behind_subject,
            }
            segments.append(seg)

        return segments

    @staticmethod
    def _align_beats(
        events: List[CaptionEvent],
        beat_times: List[float],
    ) -> List[CaptionEvent]:
        """Optional: snap segment-break events to nearest beat.

        Speech timing always takes priority — only shift if within ±120ms.
        """
        MAX_SNAP_SEC = 0.12  # 120 ms

        for ev in events:
            if not ev.segment_break_before:
                continue
            # Find nearest beat
            nearest = min(beat_times, key=lambda b: abs(b - ev.start_time), default=None)
            if nearest is None:
                continue
            delta = abs(nearest - ev.start_time)
            if delta <= MAX_SNAP_SEC:
                ev.start_time = nearest
                ev.beat_aligned = True
                ev.nearest_beat_time = nearest

        return events
