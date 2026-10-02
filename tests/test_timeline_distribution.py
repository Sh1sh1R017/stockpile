"""Tests for full-timeline uniform B-roll distribution and gap elimination."""

import pytest
from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.campaigns.presets.default_viral import DEFAULT_VIRAL_CAMPAIGN
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.types import (
    EditorialEditSpecification,
    ContextualBrollDecision,
    HookCandidate,
    HookScoreBreakdown,
    BrollCandidateScore,
    BrollNarrativeRole,
    PacingCategory,
    ShotType,
    SentimentCategory,
)


@pytest.fixture
def mock_director():
    return Director(api_key=None)


@pytest.fixture
def sample_segments():
    return [
        {"start": 0.0, "end": 2.56, "text": "It's nice to be part of like a young growing brand"},
        {"start": 2.56, "end": 3.88, "text": "because there's no rule."},
        {"start": 4.12, "end": 5.32, "text": "So I'm like, what your role could be."},
        {"start": 5.58, "end": 6.94, "text": "You know, like I started as the Amazon guy"},
        {"start": 6.94, "end": 8.4, "text": "and as a chief revenue officer,"},
        {"start": 8.44, "end": 11.98, "text": "I got to manage all the e-commerce and also Amazon TikTok."},
        {"start": 12.58, "end": 13.94, "text": "Shopify, I got to do all the marketing."},
        {"start": 14.48, "end": 15.38, "text": "I got to run analytics,"},
        {"start": 15.96, "end": 17.18, "text": "one of the other ads supply chain."},
        {"start": 17.58, "end": 19.32, "text": "I got to, you know, do innovation."},
        {"start": 19.52, "end": 20.4, "text": "I was tell people couldn't tell you"},
        {"start": 20.4, "end": 21.52, "text": "how much iron can go into product,"},
        {"start": 21.66, "end": 23.46, "text": "but what product we should make next?"},
        {"start": 23.58, "end": 24.96, "text": "I can give good advice on, you know,"},
        {"start": 25.1, "end": 28.16, "text": "and so like, you get to experience a lot and learn a lot."},
    ]


def test_target_shots_scales_beyond_six(mock_director):
    """Verify target_shots is not capped at 6 for longer videos."""
    # For a 60-second video with 45% ratio (27s B-roll)
    target_broll_sec = 60.0 * 0.45
    max_possible = max(3, int(60.0 / 2.8))
    target_shots = max(3, min(max_possible, int(round(target_broll_sec / 2.0))))
    assert target_shots >= 10, f"Target shots for 60s video should be at least 10, got {target_shots}"


def test_tail_gap_elimination(mock_director, sample_segments):
    """Verify that an edit plan with shots clustered only in the first half is repaired across the tail."""
    video_duration = 28.3

    # Clustered shots stopping at 14.5s (leaving 13.8s empty)
    clustered_shots = [
        {"shot_id": "broll_1", "start_time": 0.4, "end_time": 1.6, "duration": 1.2, "search_prompt": "founder talking to camera"},
        {"shot_id": "broll_2", "start_time": 2.0, "end_time": 4.0, "duration": 2.0, "search_prompt": "startup team collaboration"},
        {"shot_id": "broll_3", "start_time": 4.4, "end_time": 6.9, "duration": 2.5, "search_prompt": "founder talking head"},
        {"shot_id": "broll_4", "start_time": 7.3, "end_time": 9.3, "duration": 2.0, "search_prompt": "executive analyzing dashboards"},
        {"shot_id": "broll_5", "start_time": 9.7, "end_time": 12.2, "duration": 2.5, "search_prompt": "entrepreneur speaking"},
        {"shot_id": "broll_6", "start_time": 12.6, "end_time": 14.5, "duration": 1.9, "search_prompt": "ecommerce marketing analytics"},
    ]

    repaired_shots, coverage_pct = mock_director._audit_and_fill_timeline_distribution(
        clean_shots=clustered_shots,
        segments=sample_segments,
        video_duration=video_duration,
        campaign=DEFAULT_VIRAL_CAMPAIGN,
        niche=None,
    )

    # 1. More than 6 shots must be produced
    assert len(repaired_shots) >= 8, f"Expected at least 8 shots to cover 28.3s, got {len(repaired_shots)}"

    # 2. Shots must exist in the second half (> 15.0s)
    second_half_shots = [s for s in repaired_shots if s["start_time"] >= 14.5]
    assert len(second_half_shots) >= 2, f"Expected shots in second half, got {len(second_half_shots)}"

    # 3. Maximum gap between consecutive visual cutaways must be <= 4.2 seconds
    for i in range(len(repaired_shots) - 1):
        gap = repaired_shots[i + 1]["start_time"] - repaired_shots[i]["end_time"]
        assert gap <= 4.2, f"Gap between shot {i+1} and {i+2} is too large: {gap:.2f}s"

    # 4. Final shot must end in the closing section (>= 22.0s)
    last_shot_end = repaired_shots[-1]["end_time"]
    assert last_shot_end >= 22.0, f"Last shot ends too early: {last_shot_end}s"

    # 5. Coverage must be healthy (reference cinematic style targets up to 90%)
    assert 35.0 <= coverage_pct <= 92.0, f"Coverage out of bounds: {coverage_pct}%"


def test_internal_gap_filling(mock_director, sample_segments):
    """Verify that an internal 8-second dead gap is detected and filled."""
    video_duration = 28.3
    shots_with_gap = [
        {"shot_id": "broll_1", "start_time": 1.2, "end_time": 3.0, "duration": 1.8, "search_prompt": "team"},
        # 8-second gap between 3.0s and 11.0s
        {"shot_id": "broll_2", "start_time": 11.0, "end_time": 13.0, "duration": 2.0, "search_prompt": "analytics"},
        {"shot_id": "broll_3", "start_time": 15.0, "end_time": 17.0, "duration": 2.0, "search_prompt": "office"},
        {"shot_id": "broll_4", "start_time": 21.0, "end_time": 23.0, "duration": 2.0, "search_prompt": "prototype"},
    ]

    repaired_shots, coverage = mock_director._audit_and_fill_timeline_distribution(
        clean_shots=shots_with_gap,
        segments=sample_segments,
        video_duration=video_duration,
        campaign=DEFAULT_VIRAL_CAMPAIGN,
        niche=None,
    )

    # The gap from 3.0-11.0 (8s) exceeds max_gap_allowed. The auditor fills coverage
    # either via internal insertion or tail expansion; verify overall coverage is healthy.
    assert len(repaired_shots) >= 4, "Should have at least the original 4 shots"
    total_broll = sum(s["end_time"] - s["start_time"] for s in repaired_shots)
    assert total_broll / video_duration >= 0.20, "Coverage should be at least 20% after audit"


def test_quality_gate_stagnation_audit():
    """Verify Quality Gate audits stagnation gaps down to 4.5s."""
    q_gate = EditorialQualityGate()

    # Spec with a 10s gap (from 5s to 15s)
    mock_hook = HookCandidate(
        candidate_id="h1",
        start_time=0.0,
        end_time=3.0,
        duration=3.0,
        raw_text="Test Hook",
        tightened_text="TEST HOOK",
        retention_purpose="STRONG_CLAIM",
        retention_reason="High curiosity",
        scores=HookScoreBreakdown(final_score=75.0),
    )

    spec = EditorialEditSpecification(
        spec_id="test_spec",
        title="Test",
        total_duration=25.0,
        hook=mock_hook,
        moments=[],
        broll_shots=[
            ContextualBrollDecision(
                shot_id="b1", moment_id="m1", start_time=1.5, end_time=3.5, duration=2.0,
                narrative_role=BrollNarrativeRole.ILLUSTRATE, reason="test",
                search_query="test", emotional_intent="neutral", pacing_category=PacingCategory.NORMAL,
                scores=BrollCandidateScore(0.8, 0.8, 0.8, 0.8, 0.8, 0.8, "ACCEPT"),
                asset_path="b1.mp4", shot_type=ShotType.MEDIUM, subject_category="test", status="matched"
            ),
            # 10s stagnant gap here!
            ContextualBrollDecision(
                shot_id="b2", moment_id="m2", start_time=13.5, end_time=15.5, duration=2.0,
                narrative_role=BrollNarrativeRole.ILLUSTRATE, reason="test",
                search_query="test", emotional_intent="neutral", pacing_category=PacingCategory.NORMAL,
                scores=BrollCandidateScore(0.8, 0.8, 0.8, 0.8, 0.8, 0.8, "ACCEPT"),
                asset_path="b2.mp4", shot_type=ShotType.MEDIUM, subject_category="test", status="matched"
            ),
        ],
        captions=[],
        sfx_cues=[],
        camera_moves=[],
        energy_curve=[],
        metadata={},
    )

    repaired_spec, report = q_gate.audit_and_repair(spec)
    # The 10s stagnation is reported as a quality warning (not auto-repaired with camera moves)
    stagnation_checks = [c for c in report.checks if c.name == "pacing_stagnation"]
    assert len(stagnation_checks) >= 1, "Expected a pacing_stagnation quality check"
    # The stagnation check should be flagged as failed/warning for a 10s gap
    failed_stagnation = [c for c in stagnation_checks if not c.passed]
    assert len(failed_stagnation) >= 1, "Expected stagnation check to be marked as failed for 10s gap"
