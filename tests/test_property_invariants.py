"""Property-based tests for transcript time-base and timeline invariants."""

from hypothesis import given, strategies as st

from ai_broll_autopilot.services.transcript_scope import scope_segments
from ai_broll_autopilot.services.editorial.invariants import collect_plan_invariant_violations


@given(
    clip_in=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    clip_len=st.floats(min_value=1.0, max_value=40.0, allow_nan=False, allow_infinity=False),
)
def test_scoped_transcript_is_always_clip_relative(clip_in: float, clip_len: float):
    clip_out = clip_in + clip_len
    segments = [
        {
            "start": clip_in - 2.0,
            "end": clip_out + 2.0,
            "text": "edge",
            "words": [
                {"word": "left", "start": clip_in - 1.0, "end": clip_in + 0.2},
                {"word": "middle", "start": clip_in + 0.5, "end": clip_in + min(1.0, clip_len)},
                {"word": "right", "start": clip_out - 0.2, "end": clip_out + 1.0},
            ],
        }
    ]

    scoped = scope_segments(segments, clip_in, clip_out)

    assert scoped
    for segment in scoped:
        assert 0.0 <= segment["start"] <= segment["end"] <= max(1.0, clip_len)
        for word in segment["words"]:
            assert segment["start"] - 1e-6 <= word["start"] <= word["end"] <= segment["end"] + 1e-6


@given(
    start=st.floats(min_value=1.2, max_value=20.0, allow_nan=False, allow_infinity=False),
    duration=st.floats(min_value=0.65, max_value=1.8, allow_nan=False, allow_infinity=False),
)
def test_valid_broll_interval_shape_has_no_invariant_violation(start: float, duration: float):
    end = start + duration
    plan = {
        "target_duration": end + 0.5,
        "shots": [
            {
                "shot_id": "b1",
                "start_time": start,
                "end_time": end,
                "duration": duration,
                "asset_path": "b1.mp4",
                "approved_start_time": start,
                "approved_end_time": end,
                "width": 1080,
                "height": 1920,
                "source_duration": duration + 1.0,
                "speed": 1.0,
            }
        ],
    }
    violations = collect_plan_invariant_violations(plan)
    assert not violations
