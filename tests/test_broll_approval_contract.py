import pytest

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.services.editorial.broll_intelligence import BrollIntelligence
from ai_broll_autopilot.services.editorial.types import (
    BrollNarrativeRole,
    EditorialMoment,
    NarrativeRole,
    PacingCategory,
    SentimentCategory,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine


def make_moment():
    return EditorialMoment(
        moment_id="m1",
        start_time=2.0,
        end_time=5.0,
        duration=3.0,
        text="A person opens the shipping box.",
        semantic_topic="shipping box",
        action="opens",
        sentiment=SentimentCategory.NEUTRAL,
        narrative_role=NarrativeRole.EXAMPLE,
        pacing_requirement=PacingCategory.NORMAL,
        visual_opportunity=0.9,
    )


def test_empty_candidate_pool_retains_a_roll():
    result = BrollIntelligence().evaluate_and_plan_shot(
        moment=make_moment(),
        available_assets=[],
        variety_engine=VisualVarietyEngine(),
    )
    assert result is None


def test_rejected_top_candidate_does_not_hide_eligible_candidate(monkeypatch):
    engine = BrollIntelligence()

    from ai_broll_autopilot.services.editorial.types import BrollCandidateScore

    scores = iter([
        BrollCandidateScore(
            semantic_match=0.90,
            narrative_match=0.30,
            final_score=0.95,
            confidence=0.95,
            decision="RETAIN_A_ROLL",
        ),
        BrollCandidateScore(
            semantic_match=0.85,
            narrative_match=0.90,
            final_score=0.80,
            confidence=0.80,
            decision="ACCEPT",
        ),
    ])
    monkeypatch.setattr(engine, "score_candidate_asset", lambda **_: next(scores))

    result = engine.evaluate_and_plan_shot(
        moment=make_moment(),
        available_assets=[
            {"file_path": "rejected.mp4"},
            {"file_path": "eligible.mp4"},
        ],
        variety_engine=VisualVarietyEngine(),
    )
    assert result is not None
    assert result.asset_path == "eligible.mp4"


def test_timeline_audit_never_expands_long_or_fills_gaps():
    director = Director.__new__(Director)

    shots, coverage = director._audit_and_fill_timeline_distribution(
        clean_shots=[
            {
                "shot_id": "broll_1",
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
                "asset_path": "clip.mp4",
            }
        ],
        segments=[],
        video_duration=20.0,
        campaign=object(),
    )

    assert len(shots) == 1
    assert shots[0]["start_time"] == 2.0
    assert shots[0]["end_time"] == 3.2
    assert shots[0]["duration"] == 1.2
    assert coverage == pytest.approx(6.0)


def test_timeline_audit_drops_out_of_contract_interval():
    director = Director.__new__(Director)

    shots, _ = director._audit_and_fill_timeline_distribution(
        clean_shots=[
            {
                "shot_id": "hero",
                "start_time": 2.0,
                "end_time": 8.0,
                "duration": 6.0,
                "asset_path": "clip.mp4",
            }
        ],
        segments=[],
        video_duration=20.0,
        campaign=object(),
    )

    assert shots == []
