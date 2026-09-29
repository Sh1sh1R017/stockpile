from pathlib import Path

from ai_broll_autopilot.services.caption_motion import (
    CAPTION_MOTION_PROFILES,
    apply_caption_motion,
    normalize_motion_profile,
)
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter


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
