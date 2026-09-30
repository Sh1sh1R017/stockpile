"""Comprehensive unit and regression tests for CaptionCompositor and True Behind-Subject Hook Editing."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import cv2
import numpy as np
import pytest

from ai_broll_autopilot.services.caption_compositor import (
    CaptionCompositor, caption_compositor, SemanticLayer
)
from ai_broll_autopilot.services.razor_caption.caption_event import (
    CaptionEvent, CaptionMode, EmphasisLevel, LayerMode, AnimationType
)
from ai_broll_autopilot.services.subject_isolation import SubjectIsolationService, subject_isolation_service
from ai_broll_autopilot.services.timeline import TimelineEngine as Timeline
from ai_broll_autopilot.services.openreel_adapter import OpenReelAdapter
from ai_broll_autopilot.services.edit_director import EditPlan


@pytest.fixture
def temp_work_dir():
    d = Path(tempfile.mkdtemp(prefix="test_compositor_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_transcript():
    return [
        {
            "start": 0.0,
            "end": 3.0,
            "text": "You were completely wrong about this company.",
            "words": [
                {"word": "You", "start": 0.0, "end": 0.3},
                {"word": "were", "start": 0.3, "end": 0.6},
                {"word": "completely", "start": 0.6, "end": 1.2},
                {"word": "wrong", "start": 1.2, "end": 1.8},
                {"word": "about", "start": 1.8, "end": 2.1},
                {"word": "this", "start": 2.1, "end": 2.4},
                {"word": "company.", "start": 2.4, "end": 3.0},
            ]
        }
    ]


@pytest.fixture
def dummy_video(temp_work_dir):
    """Create a minimal 1-second 1080x1920 test video."""
    video_path = temp_work_dir / "dummy_source.mp4"
    w, h = 1080, 1920
    fps = 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h), isColor=True)
    frame = np.full((h, w, 3), 40, dtype=np.uint8)
    # Draw a human-like silhouette proxy
    cv2.circle(frame, (540, 600), 180, (200, 180, 160), -1)  # head
    cv2.ellipse(frame, (540, 1200), (320, 500), 0, 0, 360, (100, 80, 180), -1)  # torso
    for _ in range(30):
        writer.write(frame)
    writer.release()
    return str(video_path)


# ==============================================================================
# 1. Semantic Layer & Razor Hook Separation Tests
# ==============================================================================

class TestCaptionCompositorLayers:

    def test_razor_hook_event_marked_behind_subject(self):
        """A. Razor HOOK event marked behind_subject."""
        ev = CaptionEvent(
            word="WRONG",
            start_time=1.2,
            end_time=1.8,
            emphasis=EmphasisLevel.HOOK,
            layer=LayerMode.BEHIND_SUBJECT,
        )
        assert ev.is_hook_word is True
        assert ev.requires_behind_subject is True

    def test_hook_event_actually_enters_behind_subject_render_list(self, temp_work_dir, dummy_video):
        """B. Hook event actually enters behind-subject render list."""
        async def _run():
            edit_plan = {
                "subtitles_behind_subject": True,
                "render_settings": {"subtitles_behind_subject": True},
                "razor_captions": [
                    {
                        "text": "YOU",
                        "start": 0.0,
                        "end": 0.5,
                        "emphasis": {"level": 0},
                        "layer": "above_subject",
                    },
                    {
                        "text": "WRONG",
                        "start": 1.0,
                        "end": 2.0,
                        "emphasis": {"level": 3},
                        "layer": "behind_subject",
                    }
                ]
            }

            compositor = CaptionCompositor()
            normal_ass, behind_ass, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan=edit_plan,
                transcript_segments=[{"text": "YOU WRONG", "start": 0.0, "end": 2.0}],
                work_dir=temp_work_dir,
                style_preset="hormozi",
            )

            assert behind_ass is not None
            assert Path(behind_ass).exists()
            behind_content = Path(behind_ass).read_text(encoding="utf-8")
            assert "WRONG" in behind_content
            assert "YOU" not in behind_content
        asyncio.run(_run())

    def test_global_normal_subtitles_remain_above_subject(self, temp_work_dir, dummy_video):
        """C. Global normal subtitles remain above subject."""
        async def _run():
            edit_plan = {
                "subtitles_behind_subject": True,
                "render_settings": {"subtitles_behind_subject": True},
                "razor_captions": [
                    {
                        "text": "NORMAL",
                        "start": 0.0,
                        "end": 0.5,
                        "emphasis": {"level": 0},
                        "layer": "above_subject",
                    },
                    {
                        "text": "HOOK_WORD",
                        "start": 0.5,
                        "end": 1.0,
                        "emphasis": {"level": 3},
                        "layer": "behind_subject",
                    }
                ]
            }

            compositor = CaptionCompositor()
            normal_ass, behind_ass, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan=edit_plan,
                transcript_segments=[{"text": "NORMAL HOOK_WORD", "start": 0.0, "end": 1.0}],
                work_dir=temp_work_dir,
            )

            assert normal_ass is not None
            normal_content = Path(normal_ass).read_text(encoding="utf-8")
            assert "NORMAL" in normal_content
            assert "HOOK_WORD" not in normal_content
        asyncio.run(_run())

    def test_regression_hook_text_in_behind_subject_layer(self, temp_work_dir, dummy_video):
        """REGRESSION TEST: hook_text = 'YOU WERE WRONG' enters behind-subject layer when enabled."""
        async def _run():
            edit_plan = {
                "hook_text": "YOU WERE WRONG",
                "subtitles_behind_subject": True,
                "render_settings": {"subtitles_behind_subject": True},
                "razor_captions": [
                    {"text": "YOU", "start": 0.0, "end": 0.4, "emphasis": {"level": 0}, "layer": "above_subject"},
                    {"text": "WERE", "start": 0.4, "end": 0.8, "emphasis": {"level": 0}, "layer": "above_subject"},
                    {"text": "WRONG", "start": 0.8, "end": 1.5, "emphasis": {"level": 3}, "layer": "behind_subject"},
                ]
            }

            compositor = CaptionCompositor()
            normal_ass, behind_ass, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan=edit_plan,
                transcript_segments=[{"text": "YOU WERE WRONG", "start": 0.0, "end": 1.5}],
                work_dir=temp_work_dir,
                hook_text="YOU WERE WRONG",
            )

            assert behind_ass is not None
            behind_content = Path(behind_ass).read_text(encoding="utf-8")
            assert "WRONG" in behind_content, "Hook word 'WRONG' must be in behind-subject layer"
        asyncio.run(_run())

    def test_hook_text_not_silently_discarded_when_behind_disabled(self, temp_work_dir, dummy_video):
        """D. Hook text is NOT silently discarded when behind-subject is disabled."""
        async def _run():
            edit_plan = {
                "hook_text": "YOU WERE WRONG",
                "subtitles_behind_subject": False,
                "render_settings": {"subtitles_behind_subject": False},
                "razor_captions": [
                    {"text": "WRONG", "start": 0.0, "end": 1.0, "emphasis": {"level": 3}, "layer": "behind_subject"}
                ]
            }

            compositor = CaptionCompositor()
            normal_ass, behind_ass, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan=edit_plan,
                transcript_segments=[{"text": "WRONG", "start": 0.0, "end": 1.0}],
                work_dir=temp_work_dir,
                hook_text="YOU WERE WRONG",
            )

            assert behind_ass is None
            assert matte is None
            assert normal_ass is not None
            normal_content = Path(normal_ass).read_text(encoding="utf-8")
            assert "WRONG" in normal_content
        asyncio.run(_run())

    def test_subject_matte_generated_when_behind_hook_exists(self, temp_work_dir, dummy_video):
        """E. Subject matte generated when behind-hook exists."""
        async def _run():
            edit_plan = {
                "subtitles_behind_subject": True,
                "render_settings": {"subtitles_behind_subject": True},
                "razor_captions": [
                    {"text": "MASSIVE", "start": 0.0, "end": 1.0, "emphasis": {"level": 3}, "layer": "behind_subject"}
                ]
            }

            compositor = CaptionCompositor()
            normal_ass, behind_ass, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan=edit_plan,
                transcript_segments=[{"text": "MASSIVE", "start": 0.0, "end": 1.0}],
                work_dir=temp_work_dir,
            )

            assert matte is not None
            assert Path(matte).exists()
            assert Path(matte).stat().st_size > 0
        asyncio.run(_run())

    def test_no_transcript_no_crash(self, temp_work_dir, dummy_video):
        """H. No transcript -> returns None tuple cleanly without crash."""
        async def _run():
            compositor = CaptionCompositor()
            normal, behind, matte = await compositor.prepare_caption_render_assets(
                source_video=dummy_video,
                edit_plan={},
                transcript_segments=[],
                work_dir=temp_work_dir,
            )
            assert normal is None
            assert behind is None
            assert matte is None
        asyncio.run(_run())

    def test_segmentation_failure_normal_caption_fallback(self, temp_work_dir, dummy_video):
        """I. Segmentation failure gracefully falls back to normal top captions."""
        async def _run():
            edit_plan = {
                "subtitles_behind_subject": True,
                "render_settings": {"subtitles_behind_subject": True},
                "razor_captions": [
                    {"text": "HOOK", "start": 0.0, "end": 1.0, "emphasis": {"level": 3}, "layer": "behind_subject"}
                ]
            }

            compositor = CaptionCompositor()
            with patch.object(
                subject_isolation_service,
                "generate_person_matte_video",
                side_effect=RuntimeError("GPU OOM / segmentation crash")
            ):
                normal, behind, matte = await compositor.prepare_caption_render_assets(
                    source_video=dummy_video,
                    edit_plan=edit_plan,
                    transcript_segments=[{"text": "HOOK", "start": 0.0, "end": 1.0}],
                    work_dir=temp_work_dir,
                )

            # Fallback to normal layer only
            assert normal is not None
            assert behind is None
            assert matte is None
            normal_content = Path(normal).read_text(encoding="utf-8")
            assert "HOOK" in normal_content
        asyncio.run(_run())


# ==============================================================================
# 2. Person Segmentation & Multi-Person Tests
# ==============================================================================

class TestSubjectIsolationBackend:

    def test_multi_person_mask_combination(self):
        """G. Multiple persons: union of detected person regions."""
        service = SubjectIsolationService()
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)

        # Draw two separate person shapes (host + guest)
        cv2.circle(frame, (350, 800), 120, (200, 180, 160), -1)  # Person 1
        cv2.circle(frame, (730, 800), 120, (200, 180, 160), -1)  # Person 2

        matte = service.generate_person_matte(frame)
        assert matte is not None
        assert matte.shape == (1920, 1080)
        assert matte.dtype == np.uint8

        # Verify both left and right person areas have positive mask weight
        left_val = np.mean(matte[700:900, 250:450])
        right_val = np.mean(matte[700:900, 630:830])
        # Center gap between speakers has lower or zero weight
        center_val = np.mean(matte[700:900, 480:600])

        assert left_val > 0
        assert right_val > 0
        assert left_val > center_val or right_val > center_val


# ==============================================================================
# 3. Timeline Filtergraph Stack & Compositing Order
# ==============================================================================

class TestTimelineFiltergraphCompositor:

    def test_timeline_filtergraph_creates_proper_layers(self, temp_work_dir):
        """F. Renderer creates: background -> caption_under_subject -> subject_fg -> final."""
        timeline = Timeline(target_width=1080, target_height=1920, target_fps=30)
        behind_ass = temp_work_dir / "behind.ass"
        normal_ass = temp_work_dir / "normal.ass"
        behind_ass.write_text("[Script Info]\n", encoding="utf-8")
        normal_ass.write_text("[Script Info]\n", encoding="utf-8")

        shots = [
            {"asset_path": "broll.mp4", "start_time": 4.0, "end_time": 7.0, "transition": {}}
        ]

        filtergraph, final_v, final_a = timeline.build_filtergraph(
            shots=shots,
            audio_sfx_list=[],
            ass_subtitles_path=str(normal_ass),
            behind_subject_ass_path=str(behind_ass),
            subject_matte_stream_idx=2,
            layout_mode="single",
        )

        # Assert correct filter names and chain
        assert "subtitles=" in filtergraph
        assert "caption_under_subject" in filtergraph
        assert "alphamerge[subject_fg]" in filtergraph
        assert "subject_caption_layer" in filtergraph

        # Verify B-roll occlusion protection (L):
        # A-roll subject must NOT appear over active B-roll (4.0s to 7.0s)
        assert "between(t,4.00,7.00)" in filtergraph


# ==============================================================================
# 4. OpenReel Round-Trip Compatibility
# ==============================================================================

class TestOpenReelRoundTrip:

    def test_openreel_round_trip_retains_behind_subject(self):
        """J. OpenReel round-trip retains behindSubject flag."""
        plan = EditPlan(
            plan_id="test_plan",
            title="Behind Subject Test",
            target_duration=10.0,
            source_media={"path": "dummy.mp4", "duration": 10.0},
            clip_interval={"in_point": 0.0, "out_point": 10.0},
            niche={"id": "podcast", "name": "Podcast"},
            style={"id": "clean", "name": "Clean"},
            subtitles_behind_subject=True,
            subtitles=[
                {"id": "sub_1", "text": "HOOK WORD", "startTime": 1.0, "endTime": 2.5, "behindSubject": True}
            ],
            render_settings={"subtitles_behind_subject": True, "caption_motion": "word-pop"}
        )

        adapter = OpenReelAdapter()
        project = adapter.create_openreel_project(plan)

        # Inspect subtitles in created project
        subs = project["project"]["timeline"]["subtitles"]
        assert len(subs) >= 1
        assert subs[0].get("behindSubject") is True
        assert "subtitle-behind-subject" in project["project"]["capabilities"]

        # Test sync back from OpenReel
        updated_plan = adapter.update_edit_plan_from_openreel(plan, project)
        assert updated_plan.subtitles_behind_subject is True
        assert updated_plan.subtitles[0]["behind_subject"] is True
