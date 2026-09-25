"""Comprehensive Multi-Niche End-to-End Test Suite for Stockpile -> OpenReel Integration.

Verifies:
1. Niche & Style Profiles registration & OpenReel compatibility
2. Automated Niche Detection across 5 distinct domains
3. 9-Factor Viral Clip Detection
4. Declarative EditPlan generation
5. Native OpenReel Schema 1.2.0 (.oreel / project.json) multitrack project export
"""

import asyncio
import json
import tempfile
from pathlib import Path

from ai_broll_autopilot.niches import niche_registry
from ai_broll_autopilot.styles import style_registry
from ai_broll_autopilot.services.niche_detector import niche_detector, content_analyzer
from ai_broll_autopilot.services.clip_detector import clip_detector
from ai_broll_autopilot.services.edit_director import edit_director
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter, OPENREEL_SCHEMA_VERSION
from ai_broll_autopilot.services.broll_library import broll_library
from ai_broll_autopilot.services.subject_isolation import subject_isolation_service
from ai_broll_autopilot.services.qc_service import edit_quality_service


def test_niches_and_styles_registered():
    """Verify built-in profiles and styles are properly registered and schema-compliant."""
    niches = niche_registry.list_profiles()
    assert len(niches) >= 12
    niche_ids = niche_registry.list_ids()
    assert "sports_basketball" in niche_ids
    assert "business_startup" in niche_ids
    assert "tech_ai" in niche_ids
    assert "gaming" in niche_ids
    assert "comedy" in niche_ids
    assert "generic" in niche_ids

    styles = style_registry.list_styles()
    assert len(styles) >= 7
    style_ids = style_registry.list_ids()
    assert "sports_editorial" in style_ids
    assert "clean_podcast" in style_ids
    assert "business_editorial" in style_ids
    assert "gaming_fast" in style_ids

    # Verify OpenReel formatting methods
    sports_style = style_registry.get_style("sports_editorial")
    sub_style = sports_style.to_openreel_subtitle_style()
    assert sub_style["fontFamily"] == "Montserrat"
    assert sub_style["color"] == "#FFFFFF"
    assert sub_style["highlightColor"] == "#FFDD00"

    text_style = sports_style.to_openreel_text_style()
    assert text_style["fontWeight"] == "bold"
    assert text_style["strokeWidth"] == 5


def test_niche_detection_5_domains():
    """Verify heuristic and semantic classification across 5 distinct domains."""
    domains = [
        {
            "name": "Basketball",
            "text": "Collin Sexton was an absolute beast on the court at the gym, doing crossovers and dunking on everyone in the tournament.",
            "expected_niche": "sports_basketball",
            "expected_style": "sports_editorial",
        },
        {
            "name": "Startup Business",
            "text": "We pitched 50 venture capital investors for our SaaS startup and closed our seed round after showing our product revenue growth.",
            "expected_niche": "business_startup",
            "expected_style": "business_editorial",
        },
        {
            "name": "AI & Tech",
            "text": "Training neural networks on a massive GPU datacenter with custom Python CUDA kernels optimizes model inference speeds.",
            "expected_niche": "tech_ai",
            "expected_style": "clean_podcast",
        },
        {
            "name": "Gaming",
            "text": "The final boss fight in Unreal Engine had insane graphics, but shader compilation dropped my FPS during the multiplayer raid.",
            "expected_niche": "gaming",
            "expected_style": "gaming_fast",
        },
        {
            "name": "Comedy",
            "text": "The standup comedian was telling hilarious jokes on stage, making the entire crowd roar with laughter and funny reactions.",
            "expected_niche": "comedy",
            "expected_style": "gaming_fast",
        },
    ]

    for d in domains:
        res = asyncio.run(niche_detector.detect_niche(d["text"]))
        assert res.niche_id == d["expected_niche"], f"Expected {d['expected_niche']} for {d['name']}, got {res.niche_id}"
        assert res.suggested_style_id == d["expected_style"]
        assert res.confidence >= 0.50
        assert len(res.detected_keywords) > 0


def test_viral_clip_detection_scoring():
    """Verify multi-factor 9-dimensional scoring and window extraction."""
    segments = [
        {"start": 0.0, "end": 4.0, "text": "Why does nobody understand the secret to viral video editing?"},
        {"start": 4.0, "end": 12.0, "text": "Most creators make the mistake of using generic stock footage that bores the audience to death."},
        {"start": 12.0, "end": 20.0, "text": "Instead, every single B-roll cutaway should directly amplify the emotional punchline!"},
        {"start": 20.0, "end": 30.0, "text": "When you align the rhythm of speech with bold typography, your viewer retention skyrockets."},
        {"start": 30.0, "end": 35.0, "text": "And that is how you build a real audience."}
    ]

    clips = asyncio.run(clip_detector.detect_clips(
        transcript_segments=segments,
        video_duration=35.0,
        target_clip_count=2,
        min_duration=15.0,
        max_duration=40.0,
    ))

    assert len(clips) >= 1
    top_clip = clips[0]
    assert top_clip.viral_score > 60.0
    assert "hook_strength" in top_clip.factor_scores
    assert "novelty" in top_clip.factor_scores
    assert "emotional_resonance" in top_clip.factor_scores
    assert top_clip.recommended_aspect_ratio == "9:16"


def test_edit_director_and_openreel_export_all_5_niches():
    """Verify full end-to-end plan generation and OpenReel export across 5 niches."""
    test_cases = [
        ("sports_basketball", "sports_editorial", "Collin Sexton Dunk"),
        ("business_startup", "business_editorial", "Founder Fundraising Pitch"),
        ("tech_ai", "clean_podcast", "AI Neural Network Architecture"),
        ("gaming", "gaming_fast", "Unreal Engine Boss Fight"),
        ("comedy", "gaming_fast", "Standup Crowd Laughs"),
    ]

    for niche_id, style_id, clip_title in test_cases:
        source_media = {
            "path": f"C:/media/{niche_id}_sample.mp4",
            "duration": 45.0,
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "title": clip_title,
        }

        segments = [
            {"start": 0.0, "end": 3.2, "text": f"Here is the key insight about {clip_title}."},
            {"start": 3.2, "end": 8.5, "text": f"Everyone in the room was completely shocked by what happened next."},
            {"start": 8.5, "end": 15.0, "text": "This completely changed the game for everyone involved."},
        ]

        # 1. Generate EditPlan
        plan = asyncio.run(edit_director.plan_edit(
            source_media=source_media,
            transcript_segments=segments,
            in_point=0.0,
            out_point=15.0,
            niche_id=niche_id,
            style_id=style_id,
        ))

        assert plan.plan_id.startswith("plan_")
        assert plan.target_duration == 15.0
        assert plan.niche["id"] == niche_id
        assert plan.style["id"] == style_id
        assert len(plan.shots) >= 1
        assert len(plan.subtitles) == 3
        assert len(plan.text_overlays) >= 1

        # 2. Export OpenReel project bundle
        temp_dir = Path(tempfile.mkdtemp())
        files = openreel_adapter.export_project_files(plan, temp_dir)

        assert files["oreel"].exists()
        assert files["project_json"].exists()
        assert files["manifest"].exists()
        assert files["plan"].exists()

        # 3. Validate OpenReel Schema 1.2.0 compatibility
        with open(files["oreel"], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["version"] == OPENREEL_SCHEMA_VERSION
        proj = data["project"]
        assert proj["settings"]["width"] == 1080
        assert proj["settings"]["height"] == 1920
        assert proj["settings"]["fps"] == 30

        # Validate multitrack separation
        tracks = proj["timeline"]["tracks"]
        track_names = [t["name"] for t in tracks]
        assert "Speaker / A-Roll" in track_names
        assert "B-Roll Cutaways" in track_names
        assert "Background Music" in track_names

        # Validate non-destructive A-Roll clip
        main_track = next(t for t in tracks if t["id"] == "track_video_main")
        assert len(main_track["clips"]) == 1
        main_clip = main_track["clips"][0]
        assert main_clip["duration"] == 15.0
        assert main_clip["transform"]["fitMode"] == "cover"

        # Validate B-roll clips placed as cutaways
        broll_track = next(t for t in tracks if t["id"] == "track_video_broll")
        assert len(broll_track["clips"]) == len(plan.shots)
        for bc in broll_track["clips"]:
            assert bc["duration"] > 0
            assert bc["startTime"] >= 0

        # Validate timed subtitles with word highlights
        subs = proj["timeline"]["subtitles"]
        assert len(subs) == 3
        for sub in subs:
            assert "words" in sub
            assert len(sub["words"]) > 0
            assert "style" in sub
            assert "highlightColor" in sub["style"]

        # Validate text callouts
        text_clips = proj["textClips"]
        assert len(text_clips) >= 1
        assert text_clips[0]["style"]["fontFamily"] != ""

        # Validate manifest
        with open(files["manifest"], "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["openreel_schema_version"] == OPENREEL_SCHEMA_VERSION
        assert manifest["niche_id"] == niche_id
        assert manifest["style_id"] == style_id
        assert manifest["resolution"] == "1080x1920 (9:16 vertical)"


def test_broll_library_indexing_and_search():
    """Verify local-first B-roll catalog queries."""
    stats = broll_library.get_stats()
    assert "total_assets" in stats
    assert "niche_counts" in stats

    # Search generic
    results = broll_library.search_local("reaction", niche_id="generic")
    assert isinstance(results, list)


def test_subject_isolation_and_behind_subject():
    """Verify subject isolation layout and behindSubject OpenReel text overlay generation."""
    # Test layout estimation
    layout = subject_isolation_service.analyze_subject_layout("dummy_path.mp4")
    assert layout["subject_present"] is True
    assert 0.15 <= layout["recommended_text_y"] <= 0.40

    # Test behindSubject TextClip construction
    clip = subject_isolation_service.plan_behind_subject_overlay(
        text="COLLIN SEXTON",
        start_time=0.5,
        duration=2.5,
        font_family="Anton",
        emphasis_color="#FFDD00",
        animation_preset="pop",
        subject_layout=layout,
    )
    assert clip["behindSubject"] is True
    assert clip["text"] == "COLLIN SEXTON"
    assert clip["animation"]["preset"] == "pop"
    assert clip["style"]["fontFamily"] == "Anton"
    assert clip["transform"]["position"]["y"] == layout["recommended_text_y"]
    assert 0.0 <= clip["transform"]["position"]["x"] <= 1.0


def test_edit_quality_service():
    """Verify 5-metric Quality Control auditing and scoring."""
    source_media = {
        "path": "sample.mp4",
        "duration": 20.0,
    }
    plan = asyncio.run(edit_director.plan_edit(
        source_media=source_media,
        transcript_segments=[
            {"start": 0.0, "end": 4.0, "text": "This is an incredible moment."},
            {"start": 4.0, "end": 10.0, "text": "We are breaking down the entire strategy right here."},
        ],
        in_point=0.0,
        out_point=10.0,
        niche_id="sports_basketball",
        style_id="sports_editorial",
    ))
    report = edit_quality_service.evaluate_edit_plan(plan)
    assert report.overall_score >= 70.0
    assert len(report.checks) >= 5
    categories = {c.category for c in report.checks}
    assert "pacing" in categories
    assert "typography" in categories
    assert "safe_zone" in categories
    assert "audio" in categories


def test_openreel_two_way_sync():
    """Verify bidirectional synchronization of user timeline edits back into EditPlan."""
    from ai_broll_autopilot.services.edit_director import EditPlan

    plan = EditPlan(
        plan_id="plan_sync_test",
        title="Sync Test Plan",
        target_duration=12.0,
        source_media={"path": "test.mp4", "duration": 20.0},
        clip_interval={"in_point": 1.0, "out_point": 13.0},
        niche={"name": "Tech AI", "id": "tech_ai"},
        style={"name": "Cyber Tech", "id": "cyber_tech"},
        shots=[
            {"shot_id": "shot_1", "start_time": 2.0, "duration": 3.0, "end_time": 5.0},
            {"shot_id": "shot_2", "start_time": 7.0, "duration": 2.5, "end_time": 9.5},
        ],
        text_overlays=[],
        subtitles=[],
        zooms=[],
        audio_cues={},
    )

    project = openreel_adapter.create_openreel_project(plan)

    # Simulate user in OpenReel editor moving shot_1 from 2.0 to 3.5s and trimming shot_2 to 2.0s
    for track in project["project"]["timeline"]["tracks"]:
        if track["id"] == "track_video_broll":
            track["clips"][0]["startTime"] = 3.5
            track["clips"][0]["duration"] = 3.0
            track["clips"][1]["startTime"] = 8.0
            track["clips"][1]["duration"] = 2.0

    updated_plan = openreel_adapter.update_edit_plan_from_openreel(plan, project)
    assert updated_plan.shots[0]["start_time"] == 3.5
    assert updated_plan.shots[0]["duration"] == 3.0
    assert updated_plan.shots[0]["end_time"] == 6.5
    assert updated_plan.shots[1]["start_time"] == 8.0
    assert updated_plan.shots[1]["duration"] == 2.0
    assert updated_plan.shots[1]["end_time"] == 10.0


