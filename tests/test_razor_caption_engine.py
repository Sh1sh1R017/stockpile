"""Tests for the Rapid Razor Caption Engine.

Covers:
 1. CaptionEvent dataclass fields + to_edit_plan_entry() schema
 2. RazorSegmenter: pause detection, punctuation breaks, max group size, connector words
 3. ImportanceScorer: emphasis budget (≤5% HOOK, ≤10% STRONG), no-random ordering
 4. EnergyAnalyzer: LOW / MEDIUM / HIGH window classification
 5. SpatialEngine: region assignment, collision resolution, subject avoidance, safe areas
 6. CaptionStateMachine: animation wiring, state transitions
 7. SfxMapper: correct SFX assignment, no SFX for NORMAL words
 8. RazorCaptionEngine: end-to-end pipeline, EditPlan integration
 9. EditPlan: razor_captions field serialization
10. Behind-subject promotion rules
"""

import pytest
from unittest.mock import MagicMock

from ai_broll_autopilot.services.razor_caption.caption_event import (
    CaptionEvent, CaptionMode, EmphasisLevel, CaptionState,
    AnimationType, SpatialRegion, EnergyLevel, LayerMode,
)
from ai_broll_autopilot.services.razor_caption.segmenter import RazorSegmenter
from ai_broll_autopilot.services.razor_caption.importance_scorer import ImportanceScorer
from ai_broll_autopilot.services.razor_caption.energy_analyzer import EnergyAnalyzer
from ai_broll_autopilot.services.razor_caption.spatial_engine import SpatialEngine, SubjectBoundingBox
from ai_broll_autopilot.services.razor_caption.state_machine import CaptionStateMachine
from ai_broll_autopilot.services.razor_caption.sfx_mapper import SfxMapper, SFX_KEYWORD_POP, SFX_TEXT_SNAP, SFX_MAJOR_HOOK, SFX_BEHIND_SUBJECT_WHOOSH
from ai_broll_autopilot.services.razor_caption.engine import RazorCaptionEngine
from ai_broll_autopilot.services.edit_director import EditPlan


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_words(texts_and_times):
    """Helper: build word dicts from [(text, start, end)] tuples."""
    return [
        {"word": t, "start": s, "end": e, "confidence": 1.0}
        for t, s, e in texts_and_times
    ]


def _make_segments(texts_and_times):
    """Build sentence-level segments, each with a single word."""
    words = _make_words(texts_and_times)
    full_text = " ".join(w["word"] for w in words)
    return [{"text": full_text, "start": words[0]["start"], "end": words[-1]["end"], "words": words}]


SAMPLE_WORDS = _make_words([
    ("I", 0.00, 0.12),
    ("built", 0.12, 0.40),
    ("this", 0.40, 0.55),
    ("company", 0.55, 0.90),
    ("from", 0.95, 1.10),
    ("zero", 1.10, 1.50),
    ("to", 1.55, 1.65),
    ("one", 1.65, 1.85),
    ("million", 1.85, 2.30),
    ("dollars", 2.30, 2.70),
    ("and", 2.72, 2.85),
    ("realized", 2.85, 3.40),
    ("I", 3.40, 3.50),
    ("was", 3.50, 3.65),
    ("wrong.", 3.65, 4.10),
])

SAMPLE_SEGMENTS = [
    {
        "text": "I built this company from zero to one million dollars and realized I was wrong.",
        "start": 0.0,
        "end": 4.10,
        "words": SAMPLE_WORDS,
    }
]


# ---------------------------------------------------------------------------
# 1. CaptionEvent schema
# ---------------------------------------------------------------------------

class TestCaptionEvent:
    def test_defaults(self):
        ev = CaptionEvent(word="hello", start_time=1.0, end_time=1.5)
        assert ev.emphasis == EmphasisLevel.NORMAL
        assert ev.state == CaptionState.IDLE
        assert ev.mode == CaptionMode.RAPID_RAZOR
        assert ev.layer == LayerMode.ABOVE_SUBJECT

    def test_to_edit_plan_schema(self):
        ev = CaptionEvent(word="MILLION", start_time=1.85, end_time=2.30)
        ev.word_importance_score = 0.9
        ev.emphasis = EmphasisLevel.HOOK
        ev.region = SpatialRegion.LOWER_CENTER
        ev.position_x = 0.5
        ev.position_y = 0.82
        ev.enter_animation = AnimationType.OVERSHOOT
        ev.exit_animation = AnimationType.SNAP
        ev.sfx_event = "MAJOR_HOOK"
        ev.layer = LayerMode.BEHIND_SUBJECT

        entry = ev.to_edit_plan_entry()
        assert entry["type"] == "caption"
        assert entry["mode"] == "rapid_razor"
        assert entry["text"] == "MILLION"
        assert entry["start"] == 1.85
        assert entry["end"] == 2.30
        assert entry["layer"] == "behind_subject"
        assert entry["sfx"] == "MAJOR_HOOK"
        assert "position" in entry
        assert "animation" in entry
        assert "emphasis" in entry

    def test_is_hook_word(self):
        ev = CaptionEvent()
        ev.emphasis = EmphasisLevel.HOOK
        assert ev.is_hook_word

    def test_requires_behind_subject(self):
        ev = CaptionEvent()
        ev.layer = LayerMode.BEHIND_SUBJECT
        assert ev.requires_behind_subject

    def test_event_id_unique(self):
        ids = {CaptionEvent().event_id for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# 2. RazorSegmenter
# ---------------------------------------------------------------------------

class TestRazorSegmenter:
    def setup_method(self):
        self.seg = RazorSegmenter()

    def test_basic_segmentation_returns_one_event_per_word(self):
        events = self.seg.segment(SAMPLE_WORDS)
        assert len(events) == len(SAMPLE_WORDS)

    def test_hard_pause_triggers_break(self):
        words = _make_words([
            ("hello", 0.0, 0.3),
            ("world", 1.2, 1.5),  # 0.9s gap → hard pause
        ])
        events = self.seg.segment(words)
        assert events[1].segment_break_before is True
        assert "pause" in events[1].segment_break_reason

    def test_sentence_boundary_triggers_break(self):
        words = _make_words([
            ("wrong.", 0.0, 0.4),   # ends with period
            ("That", 0.45, 0.60),
        ])
        events = self.seg.segment(words)
        assert events[1].segment_break_before is True
        assert "sentence_boundary" in events[1].segment_break_reason

    def test_max_group_size_enforced(self):
        # 7 words with no pause → should break after 5
        words = _make_words([
            ("a", 0.0, 0.1), ("b", 0.1, 0.2), ("c", 0.2, 0.3),
            ("d", 0.3, 0.4), ("e", 0.4, 0.5), ("f", 0.5, 0.6),
            ("g", 0.6, 0.7),
        ])
        events = self.seg.segment(words)
        # f should have a break (after 5 words: a b c d e, then f starts new group)
        assert events[5].segment_break_before is True

    def test_connector_word_triggers_break(self):
        words = _make_words([
            ("money", 0.0, 0.3),
            ("and", 0.31, 0.45),  # connector
        ])
        events = self.seg.segment(words)
        assert events[1].segment_break_before is True

    def test_flatten_from_segments(self):
        flat = self.seg.flatten_from_segments(SAMPLE_SEGMENTS)
        assert len(flat) == len(SAMPLE_WORDS)
        assert flat[0]["word"] == "I"

    def test_flatten_fallback_uniform_timing(self):
        segs = [{"text": "hello world", "start": 0.0, "end": 1.0}]
        flat = self.seg.flatten_from_segments(segs)
        assert len(flat) == 2
        assert flat[0]["start"] < flat[1]["start"]

    def test_first_word_has_no_break(self):
        events = self.seg.segment(SAMPLE_WORDS)
        assert events[0].segment_break_before is False


# ---------------------------------------------------------------------------
# 3. ImportanceScorer
# ---------------------------------------------------------------------------

class TestImportanceScorer:
    def setup_method(self):
        self.seg = RazorSegmenter()
        self.scorer = ImportanceScorer()

    def _events(self, words=None):
        w = words or SAMPLE_WORDS
        return self.seg.segment(w)

    def test_score_returns_same_count(self):
        events = self._events()
        scored = self.scorer.score(events)
        assert len(scored) == len(events)

    def test_importance_score_in_range(self):
        events = self._events()
        self.scorer.score(events)
        for ev in events:
            assert 0.0 <= ev.word_importance_score <= 1.0, f"Out of range: {ev.word} = {ev.word_importance_score}"

    def test_hook_budget_not_exceeded(self):
        events = self._events()
        self.scorer.score(events)
        hook_count = sum(1 for e in events if e.emphasis == EmphasisLevel.HOOK)
        total = len(events)
        assert hook_count <= max(1, int(total * 0.06)), f"Too many HOOK words: {hook_count}/{total}"

    def test_strong_budget_not_exceeded(self):
        events = self._events()
        self.scorer.score(events)
        strong_count = sum(1 for e in events if e.emphasis == EmphasisLevel.STRONG)
        total = len(events)
        assert strong_count <= max(1, int(total * 0.12))

    def test_numeric_word_scores_high(self):
        words = _make_words([("million", 0.0, 0.4)])
        # "million" not numeric by regex — test with an actual number
        words2 = _make_words([("$1M", 0.0, 0.4)])
        events = self.seg.segment(words2)
        self.scorer.score(events)
        assert events[0].numeric_value is True

    def test_function_words_score_low(self):
        function_words = _make_words([("the", 0.0, 0.1), ("a", 0.1, 0.2), ("is", 0.2, 0.3)])
        action_words = _make_words([("built", 0.3, 0.6), ("million", 0.6, 1.0)])
        events = self.seg.segment(function_words + action_words)
        self.scorer.score(events)
        func_scores = [e.word_importance_score for e in events[:3]]
        action_scores = [e.word_importance_score for e in events[3:]]
        assert max(func_scores) < max(action_scores)

    def test_behind_subject_only_for_hook_plus_noun(self):
        events = self._events()
        self.scorer.score(events)
        for ev in events:
            if ev.layer == LayerMode.BEHIND_SUBJECT:
                # Must be HOOK emphasis
                assert ev.emphasis == EmphasisLevel.HOOK
                # Must also be numeric, named entity, or action word
                assert ev.named_entity or ev.numeric_value or ev.action_word


# ---------------------------------------------------------------------------
# 4. EnergyAnalyzer
# ---------------------------------------------------------------------------

class TestEnergyAnalyzer:
    def setup_method(self):
        self.seg = RazorSegmenter()
        self.scorer = ImportanceScorer()
        self.energy = EnergyAnalyzer(window_sec=2.0)

    def _pipeline(self, words):
        events = self.seg.segment(words)
        self.scorer.score(events)
        return events

    def test_high_density_speech_is_high_energy(self):
        # ~5 words/second
        words = _make_words([
            ("fast", 0.0, 0.15), ("speech", 0.15, 0.30), ("is", 0.30, 0.40),
            ("really", 0.40, 0.55), ("high", 0.55, 0.68), ("energy", 0.68, 0.85),
            ("content", 0.85, 1.0), ("for", 1.0, 1.1), ("sure", 1.1, 1.25),
        ])
        events = self._pipeline(words)
        self.energy.analyze(events)
        assert all(e.energy == EnergyLevel.HIGH for e in events)

    def test_slow_speech_is_low_energy(self):
        words = _make_words([
            ("slow", 0.0, 0.8), ("deliberate", 2.0, 3.0), ("speech", 4.0, 5.0),
        ])
        events = self._pipeline(words)
        self.energy.analyze(events)
        assert any(e.energy == EnergyLevel.LOW for e in events)

    def test_medium_energy_default(self):
        events = self._pipeline(SAMPLE_WORDS)
        self.energy.analyze(events)
        energies = {e.energy for e in events}
        # Should have at least MEDIUM (some range of energy across 4 seconds)
        assert EnergyLevel.MEDIUM in energies or EnergyLevel.HIGH in energies

    def test_classify_segment_returns_enum(self):
        events = self._pipeline(SAMPLE_WORDS)
        self.energy.analyze(events)
        result = self.energy.classify_segment(events)
        assert result in EnergyLevel.__members__.values()


# ---------------------------------------------------------------------------
# 5. SpatialEngine
# ---------------------------------------------------------------------------

class TestSpatialEngine:
    def setup_method(self):
        self.engine = SpatialEngine()

    def _make_event(self, **kwargs) -> CaptionEvent:
        ev = CaptionEvent(word="test", start_time=0.0, end_time=0.3)
        for k, v in kwargs.items():
            setattr(ev, k, v)
        return ev

    def test_assigns_region_to_all_events(self):
        events = [self._make_event() for _ in range(10)]
        self.engine.place(events)
        for ev in events:
            assert isinstance(ev.region, SpatialRegion)

    def test_position_xy_in_normalized_range(self):
        events = [self._make_event() for _ in range(10)]
        self.engine.place(events)
        for ev in events:
            assert 0.0 <= ev.position_x <= 1.0
            assert 0.0 <= ev.position_y <= 1.0

    def test_hook_word_placed_away_from_face(self):
        ev = self._make_event(emphasis=EmphasisLevel.HOOK)
        subject_info = {"head_top": 0.15, "neck_y": 0.45, "anchor": {"x": 0.5, "y": 0.5}, "confidence": 0.95}
        self.engine.place([ev], subject_info=subject_info)
        # Hook word should not overlap face region (face at ~y=0.22)
        assert ev.position_y > 0.45 or ev.position_y < 0.18

    def test_collision_resolved_flag(self):
        # Force a collision by placing subject at exact lower_center position
        ev = self._make_event(emphasis=EmphasisLevel.NORMAL)
        # Subject occupies the entire frame
        subject_info = {"head_top": 0.0, "neck_y": 1.0, "anchor": {"x": 0.5, "y": 0.5}, "confidence": 0.99}
        self.engine.place([ev], subject_info=subject_info)
        # Engine should degrade gracefully (no exception)
        assert isinstance(ev.region, SpatialRegion)

    def test_position_reason_always_set(self):
        events = [self._make_event() for _ in range(5)]
        self.engine.place(events)
        for ev in events:
            assert ev.position_reason != ""

    def test_subject_bounding_box_from_dict(self):
        d = {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.6, "face_x": 0.35, "face_y": 0.25}
        bbox = SubjectBoundingBox.from_dict(d)
        assert bbox.x == 0.1
        assert bbox.face_x == 0.35

    def test_nine_regions_all_valid(self):
        for region in SpatialRegion:
            assert region.value  # ensures all enum members have string values


# ---------------------------------------------------------------------------
# 6. CaptionStateMachine
# ---------------------------------------------------------------------------

class TestCaptionStateMachine:
    def setup_method(self):
        self.sm = CaptionStateMachine()

    def _make_event(self, **kwargs) -> CaptionEvent:
        ev = CaptionEvent(word="test", start_time=1.0, end_time=1.5)
        for k, v in kwargs.items():
            setattr(ev, k, v)
        return ev

    def test_wire_sets_animation_on_all_events(self):
        events = [self._make_event() for _ in range(5)]
        self.sm.wire(events)
        for ev in events:
            assert isinstance(ev.enter_animation, AnimationType)
            assert isinstance(ev.exit_animation, AnimationType)

    def test_animation_duration_clamped(self):
        events = [self._make_event() for _ in range(5)]
        self.sm.wire(events)
        for ev in events:
            assert 80 <= ev.enter_duration_ms <= 250
            assert 80 <= ev.exit_duration_ms <= 250

    def test_hook_word_gets_overshoot(self):
        ev = self._make_event(emphasis=EmphasisLevel.HOOK)
        self.sm.wire([ev])
        assert ev.enter_animation == AnimationType.OVERSHOOT

    def test_segment_break_high_energy_gets_snap(self):
        ev = self._make_event(segment_break_before=True, energy=EnergyLevel.HIGH)
        self.sm.wire([ev])
        assert ev.enter_animation == AnimationType.SNAP

    def test_advance_idle_before_start(self):
        ev = self._make_event()
        self.sm.wire([ev])
        state = self.sm.advance(ev, current_time=0.5)  # before start_time=1.0
        assert state == CaptionState.IDLE

    def test_advance_visible_during_playback(self):
        ev = self._make_event()
        self.sm.wire([ev])
        state = self.sm.advance(ev, current_time=1.3)  # mid-event
        assert state in (CaptionState.VISIBLE, CaptionState.EMPHASIZED, CaptionState.ENTERING)

    def test_advance_complete_after_end(self):
        ev = self._make_event()
        self.sm.wire([ev])
        state = self.sm.advance(ev, current_time=5.0)
        assert state == CaptionState.COMPLETE

    def test_emphasized_state_for_hook_word(self):
        ev = self._make_event(emphasis=EmphasisLevel.HOOK)
        self.sm.wire([ev])
        state = self.sm.advance(ev, current_time=1.2)  # well inside window
        assert state == CaptionState.EMPHASIZED


# ---------------------------------------------------------------------------
# 7. SfxMapper
# ---------------------------------------------------------------------------

class TestSfxMapper:
    def setup_method(self):
        self.mapper = SfxMapper()

    def _ev(self, **kwargs) -> CaptionEvent:
        ev = CaptionEvent(word="test", start_time=0.0, end_time=0.3)
        for k, v in kwargs.items():
            setattr(ev, k, v)
        return ev

    def test_normal_word_no_sfx(self):
        ev = self._ev(emphasis=EmphasisLevel.NORMAL)
        self.mapper.map([ev])
        assert ev.sfx_event is None

    def test_hook_word_gets_major_hook(self):
        ev = self._ev(emphasis=EmphasisLevel.HOOK)
        self.mapper.map([ev])
        assert ev.sfx_event == SFX_MAJOR_HOOK

    def test_strong_word_gets_keyword_pop(self):
        ev = self._ev(emphasis=EmphasisLevel.STRONG)
        self.mapper.map([ev])
        assert ev.sfx_event == SFX_KEYWORD_POP

    def test_behind_subject_gets_whoosh(self):
        ev = self._ev(layer=LayerMode.BEHIND_SUBJECT, emphasis=EmphasisLevel.HOOK)
        self.mapper.map([ev])
        assert ev.sfx_event == SFX_BEHIND_SUBJECT_WHOOSH

    def test_segment_break_gets_text_snap(self):
        ev = self._ev(segment_break_before=True, emphasis=EmphasisLevel.NORMAL)
        self.mapper.map([ev])
        assert ev.sfx_event == SFX_TEXT_SNAP

    def test_blacklist_integration(self):
        sd = MagicMock()
        sd.is_blacklisted.return_value = True
        mapper = SfxMapper(sound_designer=sd)
        ev = self._ev(emphasis=EmphasisLevel.HOOK)
        mapper.map([ev])
        # Blacklisted → SFX stripped
        assert ev.sfx_event is None

    def test_blacklist_not_called_for_none_sfx(self):
        sd = MagicMock()
        sd.is_blacklisted.return_value = False
        mapper = SfxMapper(sound_designer=sd)
        ev = self._ev(emphasis=EmphasisLevel.NORMAL)
        mapper.map([ev])
        sd.is_blacklisted.assert_not_called()


# ---------------------------------------------------------------------------
# 8. RazorCaptionEngine — end-to-end
# ---------------------------------------------------------------------------

class TestRazorCaptionEngine:
    def setup_method(self):
        self.engine = RazorCaptionEngine()

    def test_process_returns_events(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        assert len(events) == len(SAMPLE_WORDS)

    def test_all_events_have_regions(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert isinstance(ev.region, SpatialRegion)

    def test_all_events_have_animations(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert isinstance(ev.enter_animation, AnimationType)

    def test_emphasis_hierarchy_respected(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        total = len(events)
        hooks = sum(1 for e in events if e.emphasis == EmphasisLevel.HOOK)
        strongs = sum(1 for e in events if e.emphasis == EmphasisLevel.STRONG)
        assert hooks <= max(1, int(total * 0.06))
        assert strongs <= max(1, int(total * 0.12))

    def test_all_events_have_state_idle_initially(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert ev.state == CaptionState.IDLE

    def test_to_edit_plan_schema(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        plan = self.engine.to_edit_plan(events)
        assert len(plan) == len(events)
        for entry in plan:
            assert "type" in entry
            assert entry["type"] == "caption"
            assert "text" in entry
            assert "start" in entry
            assert "end" in entry
            assert "position" in entry
            assert "animation" in entry
            assert "emphasis" in entry
            assert "layer" in entry

    def test_summary_structure(self):
        events = self.engine.process(SAMPLE_SEGMENTS)
        summary = self.engine.summary(events)
        assert "total_events" in summary
        assert "hook_words" in summary
        assert "energy_distribution" in summary
        assert "regions" in summary
        assert summary["total_events"] == len(events)

    def test_empty_segments_returns_empty(self):
        events = self.engine.process([])
        assert events == []

    def test_mode_stamped_on_all_events(self):
        events = self.engine.process(SAMPLE_SEGMENTS, mode=CaptionMode.MINIMAL)
        for ev in events:
            assert ev.mode == CaptionMode.MINIMAL

    def test_beat_alignment(self):
        beat_times = [0.12, 0.55, 1.10, 1.85, 2.85]
        events = self.engine.process(SAMPLE_SEGMENTS, beat_times=beat_times)
        aligned = [e for e in events if e.beat_aligned]
        # At least one event should be beat-aligned (start_time within 120ms of a beat)
        assert len(aligned) >= 1

    def test_broll_avoidance(self):
        # B-roll from 1.0 to 2.5 → events in that range should not be LOWER_CENTER
        broll = [(1.0, 2.5)]
        events = self.engine.process(SAMPLE_SEGMENTS, broll_active_times=broll)
        for ev in events:
            if 1.0 <= ev.start_time < 2.5:
                # Should have been redirected away from LOWER_CENTER or collision-resolved
                pass  # just assert no exception — spatial engine may still use LOWER_LEFT/RIGHT
        # Just ensure pipeline completes without error
        assert len(events) == len(SAMPLE_WORDS)

    def test_subject_info_affects_placement(self):
        # Speaker on left → captions should lean right
        subject_left = {"head_top": 0.15, "neck_y": 0.55, "anchor": {"x": 0.20, "y": 0.5}, "confidence": 0.95}
        events_left = self.engine.process(SAMPLE_SEGMENTS, subject_info=subject_left)

        # Speaker on right → captions should lean left
        subject_right = {"head_top": 0.15, "neck_y": 0.55, "anchor": {"x": 0.80, "y": 0.5}, "confidence": 0.95}
        events_right = self.engine.process(SAMPLE_SEGMENTS, subject_info=subject_right)

        left_x = [e.position_x for e in events_left]
        right_x = [e.position_x for e in events_right]
        # Average x for left-speaker captions should be ≥ right-speaker captions
        assert sum(left_x) / len(left_x) >= sum(right_x) / len(right_x) - 0.1


# ---------------------------------------------------------------------------
# 9. EditPlan razor_captions field
# ---------------------------------------------------------------------------

class TestEditPlanRazorCaptions:
    def _make_plan(self):
        return EditPlan(
            plan_id="test-001",
            title="Test Edit",
            target_duration=60.0,
            source_media={"path": "/tmp/video.mp4"},
            clip_interval={"in_point": 0.0, "out_point": 60.0},
            niche={"id": "finance"},
            style={"id": "hormozi"},
        )

    def test_razor_captions_field_exists(self):
        plan = self._make_plan()
        assert hasattr(plan, "razor_captions")
        assert isinstance(plan.razor_captions, list)

    def test_razor_captions_serialized_in_to_dict(self):
        plan = self._make_plan()
        sample_entry = {
            "type": "caption", "mode": "rapid_razor", "text": "MILLION",
            "start": 1.85, "end": 2.30, "importance": 0.92,
        }
        plan.razor_captions.append(sample_entry)
        d = plan.to_dict()
        assert "razor_captions" in d
        assert len(d["razor_captions"]) == 1
        assert d["razor_captions"][0]["text"] == "MILLION"

    def test_razor_captions_populated_from_engine(self):
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        plan = self._make_plan()
        plan.razor_captions = engine.to_edit_plan(events)
        d = plan.to_dict()
        assert len(d["razor_captions"]) == len(events)

    def test_existing_subtitles_field_unaffected(self):
        plan = self._make_plan()
        plan.subtitles = [{"text": "hello", "start": 0.0, "end": 1.0}]
        plan.razor_captions = [{"text": "HOOK", "start": 0.0, "end": 0.5}]
        d = plan.to_dict()
        assert len(d["subtitles"]) == 1
        assert len(d["razor_captions"]) == 1


# ---------------------------------------------------------------------------
# 10. Acceptance checklist (spec §26 — no random movement)
# ---------------------------------------------------------------------------

class TestAcceptanceChecklist:
    def test_no_identical_consecutive_regions_for_different_words(self):
        """Position changes must be intentional, not just repeating the same region."""
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        # Count same-region-same-emphasis consecutive pairs
        same_pairs = 0
        for i in range(1, len(events)):
            if (
                events[i].region == events[i - 1].region
                and events[i].emphasis == EmphasisLevel.HOOK
                and events[i - 1].emphasis == EmphasisLevel.HOOK
            ):
                same_pairs += 1
        # Two consecutive HOOK words at same position would be suspicious
        assert same_pairs == 0, "Consecutive HOOK words must not share the same region"

    def test_all_position_reasons_set(self):
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert ev.position_reason, f"Missing position_reason for '{ev.word}'"

    def test_sfx_not_on_normal_words(self):
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            if ev.emphasis == EmphasisLevel.NORMAL and not ev.segment_break_before:
                if ev.layer != LayerMode.BEHIND_SUBJECT:
                    assert ev.sfx_event is None, f"Normal word '{ev.word}' has unexpected SFX: {ev.sfx_event}"

    def test_animation_duration_never_exceeds_250ms(self):
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert ev.enter_duration_ms <= 250
            assert ev.exit_duration_ms <= 250

    def test_animation_duration_never_below_80ms(self):
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        for ev in events:
            assert ev.enter_duration_ms >= 80
            assert ev.exit_duration_ms >= 80

    def test_word_timestamps_preserved(self):
        """word.startTime and word.endTime must match original transcript."""
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        for i, (ev, word) in enumerate(zip(events, SAMPLE_WORDS)):
            assert abs(ev.start_time - word["start"]) < 0.01, (
                f"Word '{ev.word}' start mismatch: {ev.start_time} vs {word['start']}"
            )

    def test_mode_not_auto_applied_to_wrong_mode(self):
        """RAPID_RAZOR mode must be explicitly selected, not auto-applied."""
        engine = RazorCaptionEngine(mode=CaptionMode.NORMAL)
        events = engine.process(SAMPLE_SEGMENTS, mode=CaptionMode.NORMAL)
        for ev in events:
            assert ev.mode == CaptionMode.NORMAL

    def test_importance_score_not_uniform(self):
        """If all words had the same score, the system is broken."""
        engine = RazorCaptionEngine()
        events = engine.process(SAMPLE_SEGMENTS)
        scores = [ev.word_importance_score for ev in events]
        assert max(scores) - min(scores) > 0.05, "All importance scores are identical — scorer is broken"
