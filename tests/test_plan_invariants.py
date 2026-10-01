"""Regression tests for executable plan invariants."""

from ai_broll_autopilot.services.editorial.invariants import (
    assert_plan_invariants,
    collect_plan_invariant_violations,
)


def test_valid_plan_satisfies_timeline_invariants():
    plan = {
        "target_duration": 10.0,
        "shots": [
            {
                "shot_id": "b1",
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
                "asset_path": "b1.mp4",
                "approved_start_time": 2.0,
                "approved_end_time": 3.2,
                "width": 1080,
                "height": 1920,
                "source_duration": 8.0,
                "speed": 1.25,
            }
        ],
        "transcript_segments": [
            {
                "start": 2.0,
                "end": 3.2,
                "words": [
                    {"word": "hello", "start": 2.1, "end": 2.4},
                    {"word": "world", "start": 2.5, "end": 3.0},
                ],
            }
        ],
    }
    assert_plan_invariants(plan)


def test_invariants_reject_early_overlapping_and_lengthened_broll():
    plan = {
        "target_duration": 10.0,
        "shots": [
            {
                "shot_id": "b1",
                "start_time": 0.5,
                "end_time": 2.0,
                "duration": 1.5,
                "asset_path": "b1.mp4",
                "approved_start_time": 0.5,
                "approved_end_time": 1.2,
            },
            {
                "shot_id": "b2",
                "start_time": 1.8,
                "end_time": 2.6,
                "duration": 0.8,
                "asset_path": "b2.mp4",
                "approved_start_time": 2.1,
                "approved_end_time": 2.6,
            },
        ],
    }

    violations = collect_plan_invariant_violations(plan)
    assert any("hook guard" in item for item in violations)
    assert any("overlaps" in item for item in violations)
    assert any("lengthened" in item for item in violations)


def test_invariants_reject_word_outside_parent_segment():
    plan = {
        "target_duration": 5.0,
        "transcript_segments": [
            {
                "start": 1.0,
                "end": 2.0,
                "words": [{"word": "bad", "start": 0.8, "end": 2.2}],
            }
        ],
    }
    violations = collect_plan_invariant_violations(plan)
    assert any("word outside segment" in item for item in violations)


def test_invariants_reject_orphaned_sfx_targets():
    plan = {
        "target_duration": 5.0,
        "editorial_spec": {
            "broll_shots": [{"shot_id": "b1"}],
            "moments": [{"moment_id": "m1"}],
            "captions": [],
            "camera_moves": [{"id": "cam1"}],
            "sfx_cues": [
                {"cue_id": "s1", "target_id": "missing"},
                {"cue_id": "s2"},
            ],
        },
    }
    violations = collect_plan_invariant_violations(plan)
    assert any("does not exist" in item for item in violations)
    assert any("missing target_id" in item for item in violations)


def test_super_director_cannot_create_or_retime_broll():
    from ai_broll_autopilot.services.broll_super_director import BrollSuperDirector

    director = BrollSuperDirector(api_key=None)
    plan = {
        "target_duration": 12.0,
        "shots": [
            {
                "shot_id": "b1",
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
                "asset_path": "b1.mp4",
            }
        ],
    }
    analysis = {
        "model": "test",
        "moments": [
            {
                "start": 6.0,
                "end": 11.0,
                "recommended_duration": 7.5,
                "broll_priority": 100,
                "search_queries": ["unrelated long hero"],
            }
        ],
    }

    result = director.apply_to_plan(plan, analysis, 12.0)
    assert len(result["shots"]) == 1
    assert result["shots"][0]["start_time"] == 2.0
    assert result["shots"][0]["end_time"] == 3.2
    assert result["shots"][0]["duration"] == 1.2
