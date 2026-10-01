"""Property-based tests for clip time-base normalization."""

from hypothesis import given, strategies as st

from ai_broll_autopilot.services.transcript_scope import scope_segments


@given(
    clip_in=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    clip_duration=st.floats(min_value=1, max_value=20, allow_nan=False, allow_infinity=False),
    word_offset=st.floats(min_value=-2, max_value=22, allow_nan=False, allow_infinity=False),
)
def test_scoped_word_times_stay_inside_clip(clip_in, clip_duration, word_offset):
    clip_out = clip_in + clip_duration
    segments = [{
        "start": clip_in - 1,
        "end": clip_out + 1,
        "text": "boundary test",
        "words": [{
            "word": "x",
            "start": clip_in + word_offset,
            "end": clip_in + word_offset + 0.2,
        }],
    }]

    scoped = scope_segments(segments, clip_in, clip_out)

    for segment in scoped:
        assert 0.0 <= segment["start"] <= segment["end"] <= clip_duration
        for word in segment.get("words", []):
            assert 0.0 <= word["start"] <= word["end"] <= clip_duration
            assert segment["start"] - 1e-6 <= word["start"] <= word["end"] <= segment["end"] + 1e-6
