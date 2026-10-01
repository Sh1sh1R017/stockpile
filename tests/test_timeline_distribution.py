"""Regression tests for relevance-first B-roll timeline policy."""

import pytest

from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialEditSpecification,
    HookCandidate,
    HookScoreBreakdown,
    PacingCategory,
    SentimentCategory,
)


def _decision(shot_id: str, start: float, end: float) -> ContextualBrollDecision:
    return ContextualBrollDecision(
        shot_id=shot_id,
        moment_id=f"moment_{shot_id}",
        start_time=start,
        end_time=end,
        duration=end - start,
        narrative_role=BrollNarrativeRole.ILLUSTRATE,
        reason="Contextually relevant test visual",
        search_query="test",
        emotional_intent="neutral",
        pacing_category=PacingCategory.NORMAL,
        scores=BrollCandidateScore(
            semantic_match=0.9,
            sentiment_match=0.8,
            action_match=0.8,
            narrative_match=0.9,
            final_score=0.85,
            confidence=0.85,
            decision="ACCEPT",
        ),
        asset_path=f"{shot_id}.mp4",
        status="matched",
    )


def test_timeline_audit_does_not_fill_tail_or_internal_gaps():
    director = Director.__new__(Director)
    source = [
        {"shot_id": "b1", "start_time": 2.0, "end_time": 3.2, "duration": 1.2, "asset_path": "b1.mp4"},
        {"shot_id": "b2", "start_time": 11.0, "end_time": 12.2, "duration": 1.2, "asset_path": "b2.mp4"},
    ]

    audited, coverage = director._audit_and_fill_timeline_distribution(
        clean_shots=source,
        segments=[],
        video_duration=28.0,
        campaign=object(),
    )

    assert audited == source
    assert coverage == pytest.approx((2.4 / 28.0) * 100.0)


def test_timeline_audit_drops_invalid_intervals_without_retiming_valid_ones():
    director = Director.__new__(Director)
    source = [
        {"shot_id": "too_early", "start_time": 0.4, "end_time": 1.1, "duration": 0.7, "asset_path": "a.mp4"},
        {"shot_id": "valid", "start_time": 2.0, "end_time": 3.2, "duration": 1.2, "asset_path": "b.mp4"},
        {"shot_id": "too_long", "start_time": 5.0, "end_time": 8.0, "duration": 3.0, "asset_path": "c.mp4"},
    ]

    audited, _ = director._audit_and_fill_timeline_distribution(
        clean_shots=source,
        segments=[],
        video_duration=20.0,
        campaign=object(),
    )

    assert [s["shot_id"] for s in audited] == ["valid"]
    assert all(s["shot_id"] != "too_long" for s in audited)


def test_quality_gate_reports_stagnation_without_inventing_creative_events():
    gate = EditorialQualityGate()
    hook = HookCandidate(
        candidate_id="h1",
        start_time=0.0,
        end_time=3.0,
        duration=3.0,
        raw_text="Test hook",
        tightened_text="TEST HOOK",
        retention_purpose="STRONG_CLAIM",
        retention_reason="High curiosity",
        scores=HookScoreBreakdown(final_score=80.0),
    )
    spec = EditorialEditSpecification(
        spec_id="test_spec",
        title="Test",
        total_duration=25.0,
        hook=hook,
        moments=[],
        broll_shots=[_decision("b1", 1.5, 3.0), _decision("b2", 13.5, 15.0)],
        captions=[],
        sfx_cues=[],
        camera_moves=[],
        energy_curve=[],
        metadata={},
    )

    repaired, report = gate.audit_and_repair(spec)

    assert repaired.camera_moves == []
    pacing_check = next(c for c in report.checks if c.name == "pacing_stagnation")
    assert pacing_check.passed is False
    assert any("Visual stagnation" in msg for msg in report.recommendations)
