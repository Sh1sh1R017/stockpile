from ai_broll_autopilot.services.shorts_workflow import (
    build_clip_candidate,
    normalize_clip_candidate,
    normalize_clip_transcript,
    workflow_record,
)


def test_normalize_clip_candidate_preserves_open_shorts_range():
    result = normalize_clip_candidate(
        {"id": "c1", "start": "12.5", "end": 48.25, "title": "The big idea"},
        index=0,
    )
    assert result is not None
    assert result["id"] == "c1"
    assert result["start"] == 12.5
    assert result["end"] == 48.25
    assert result["duration"] == 35.75
    assert result["source"] == "openshorts"


def test_normalize_clip_candidate_rejects_invalid_range():
    assert normalize_clip_candidate({"start": 10, "end": 10}) is None
    assert normalize_clip_candidate({"start": -1, "end": 4}) is None


def test_normalize_clip_transcript_rebases_words_to_child_clip():
    segments = [
        {
            "start": 10.0,
            "end": 14.0,
            "text": "hello world",
            "words": [
                {"word": "hello", "start": 10.0, "end": 11.0},
                {"word": "world", "start": 12.0, "end": 14.0},
            ],
        }
    ]
    result = normalize_clip_transcript(segments, 11.0, 14.0)
    assert len(result) == 1
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 3.0
    assert result[0]["words"][0]["word"] == "world"
    assert result[0]["words"][0]["start"] == 1.0
    assert result[0]["words"][0]["end"] == 3.0


def test_build_clip_candidate_uses_existing_clip_candidate_type():
    candidate = build_clip_candidate(
        {"id": "c1", "start": 4, "end": 22, "title": "Hook"},
        source_duration=60,
    )
    assert candidate.start_time == 4
    assert candidate.end_time == 22
    assert candidate.duration == 18
    assert candidate.title == "Hook"


def test_workflow_record_is_additive_editplan_metadata():
    record = workflow_record(
        parent_job_id="parent",
        source="openshorts",
        start=2,
        end=40,
        title="Short one",
        batch_id="batch_1",
        candidate_id="openshorts_1",
        caption_style="razor_pop",
        caption_motion="word-pop",
        subtitles_behind_subject=True,
    )
    assert record["type"] == "short_edit"
    assert record["parent_job_id"] == "parent"
    assert record["source_interval"] == {"start": 2.0, "end": 40.0}
    assert record["caption_style"] == "razor_pop"
    assert record["subtitles_behind_subject"] is True
