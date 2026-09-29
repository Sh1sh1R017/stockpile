from pathlib import Path

from ai_broll_autopilot.services.caption_motion import (
    CAPTION_MOTION_PROFILES,
    apply_caption_motion,
    normalize_motion_profile,
)
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter
from ai_broll_autopilot.services.subtitle_engine import SubtitleEngine
from ai_broll_autopilot.services.subject_caption import annotate_segments_for_subject_captions
from ai_broll_autopilot.services.timeline import TimelineEngine


def test_caption_motion_profiles_are_normalized_and_applied():
    assert "typewriter" in CAPTION_MOTION_PROFILES
    assert "bounce" in CAPTION_MOTION_PROFILES
    assert normalize_motion_profile("unknown") == "word-pop"

    subtitles = [{"id": "sub_1", "text": "HELLO", "animationStyle": "word-highlight"}]
    updated = apply_caption_motion(subtitles, "typewriter")
    assert updated[0]["animationStyle"] == "typewriter"
    assert updated[0]["motionProfile"] == "typewriter"
    assert updated[0]["motionRecipe"] == "motion-anything:typewriter-multi"


def test_openreel_export_uses_raw_source_as_editable_a_roll():
    plan = EditPlan(
        plan_id="editable_test",
        title="Editable",
        target_duration=20.0,
        source_media={"path": "C:/media/raw.mp4", "duration": 120.0},
        clip_interval={"in_point": 10.0, "out_point": 30.0},
        niche={"id": "generic", "name": "Podcast"},
        style={"id": "clean_podcast", "name": "Clean Podcast"},
        shots=[
            {
                "shot_id": "broll_1",
                "start_time": 4.0,
                "end_time": 7.0,
                "duration": 3.0,
                "asset_path": "C:/media/broll_1.mp4",
            }
        ],
        text_overlays=[],
        subtitles=[],
        zooms=[],
        audio_cues={},
    )

    project = openreel_adapter.create_openreel_project(plan)
    main = next(t for t in project["project"]["timeline"]["tracks"] if t["id"] == "track_video_main")
    broll = next(t for t in project["project"]["timeline"]["tracks"] if t["id"] == "track_video_broll")

    assert main["clips"][0]["mediaId"] == "media_source_main"
    assert main["clips"][0]["inPoint"] == 10.0
    assert main["clips"][0]["outPoint"] == 30.0
    assert broll["clips"][0]["mediaId"] == "media_broll_1"
    assert broll["hidden"] is False
    assert broll["muted"] is False


def test_subject_aware_caption_metadata_ass_layers_and_timeline(tmp_path):
    subtitles = [
        {
            "id": "sub_1",
            "text": "PUT THIS BEHIND ME",
            "startTime": 0.0,
            "endTime": 1.5,
            "behind_subject": True,
            "motionProfile": "typewriter",
            "motionRecipe": "motion-anything:typewriter-multi",
            "words": [
                {"text": "PUT", "startTime": 0.0, "endTime": 0.4},
                {"text": "THIS", "startTime": 0.4, "endTime": 0.8},
                {"text": "BEHIND", "startTime": 0.8, "endTime": 1.1},
                {"text": "ME", "startTime": 1.1, "endTime": 1.5},
            ],
        },
        {
            "id": "sub_2",
            "text": "NORMAL CAPTION",
            "startTime": 1.5,
            "endTime": 3.0,
            "behind_subject": False,
            "words": [
                {"text": "NORMAL", "startTime": 1.5, "endTime": 2.2},
                {"text": "CAPTION", "startTime": 2.2, "endTime": 3.0},
            ],
        },
    ]
    transcript = [
        {
            "start": 0.0,
            "end": 1.5,
            "text": "PUT THIS BEHIND ME",
            "words": [
                {"word": "PUT", "start": 0.0, "end": 0.4},
                {"word": "THIS", "start": 0.4, "end": 0.8},
                {"word": "BEHIND", "start": 0.8, "end": 1.1},
                {"word": "ME", "start": 1.1, "end": 1.5},
            ],
        },
        {
            "start": 1.5,
            "end": 3.0,
            "text": "NORMAL CAPTION",
            "words": [
                {"word": "NORMAL", "start": 1.5, "end": 2.2},
                {"word": "CAPTION", "start": 2.2, "end": 3.0},
            ],
        },
    ]

    prepared = annotate_segments_for_subject_captions(transcript, subtitles)
    assert prepared[0]["behind_subject"] is True
    assert prepared[1]["behind_subject"] is False

    engine = SubtitleEngine()
    normal_ass = tmp_path / "normal.ass"
    behind_ass = tmp_path / "behind.ass"
    engine.generate_ass_file(
        segments=prepared,
        output_path=normal_ass,
        style_preset="clean",
        only_behind_subject=False,
    )
    engine.generate_ass_file(
        segments=prepared,
        output_path=behind_ass,
        style_preset="clean",
        only_behind_subject=True,
    )
    normal_text = normal_ass.read_text(encoding="utf-8")
    behind_text = behind_ass.read_text(encoding="utf-8")
    assert "NORMAL" in normal_text
    assert "PUT" not in normal_text
    assert "PUT" in behind_text
    assert "NORMAL" not in behind_text

    matte_path = tmp_path / "subject_matte.mp4"
    matte_path.write_bytes(b"mask-placeholder")
    graph, final_video, _ = TimelineEngine().build_filtergraph(
        shots=[],
        ass_subtitles_path=str(normal_ass),
        behind_subject_ass_path=str(behind_ass),
        subject_matte_stream_idx=1,
    )
    assert "caption_under_subject" in graph
    assert "[subject_src][subject_mask]alphamerge[subject_fg]" in graph
    assert final_video in ("subbed_v", "subject_caption_layer")


def test_openreel_round_trips_subject_caption_metadata():
    plan = EditPlan(
        plan_id="subject_caption_sync",
        title="Subject Caption Sync",
        target_duration=3.0,
        source_media={"path": "C:/media/raw.mp4", "duration": 10.0},
        clip_interval={"in_point": 0.0, "out_point": 3.0},
        niche={"id": "generic", "name": "Podcast"},
        style={"id": "clean_podcast", "name": "Clean Podcast"},
        shots=[],
        text_overlays=[],
        subtitles=[
            {
                "id": "sub_1",
                "text": "BEHIND SUBJECT",
                "startTime": 0.0,
                "endTime": 2.0,
                "animationStyle": "typewriter",
                "motionProfile": "typewriter",
                "motionRecipe": "motion-anything:typewriter-multi",
                "behind_subject": True,
                "style": {"fontFamily": "Arial"},
                "words": [],
            }
        ],
        zooms=[],
        audio_cues={},
    )

    project = openreel_adapter.create_openreel_project(plan)
    sub = project["project"]["timeline"]["subtitles"][0]
    assert sub["behindSubject"] is True
    assert sub["motionProfile"] == "typewriter"
    assert sub["motionRecipe"] == "motion-anything:typewriter-multi"
    assert "subtitle-behind-subject" in project["project"]["capabilities"]

    updated = openreel_adapter.update_edit_plan_from_openreel(plan, project)
    assert updated.subtitles[0]["behind_subject"] is True
    assert updated.subtitles[0]["motionProfile"] == "typewriter"
    assert updated.subtitles[0]["motionRecipe"] == "motion-anything:typewriter-multi"
    assert updated.subtitles[0]["startTime"] == 0.0
    assert updated.subtitles[0]["endTime"] == 2.0
