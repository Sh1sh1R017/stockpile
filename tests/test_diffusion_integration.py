"""Automated Integration & Regression Test Suite for Diffusion Studio & OpenReel Integration.

Verifies:
1. Stockpile EditPlan -> Diffusion Studio project conversion.
2. Timeline precision & timing conversion (zero floating-point drift).
3. Video and B-roll layer mapping.
4. Subtitle and caption word-level mapping.
5. SFX and audio separation (Dialogue, BGM ducking, SFX cues).
6. Media asset resolution (persistent URLs, no blob URLs).
7. OpenReel handoff (Diffusion Studio composition -> OpenReel Schema 1.2.0).
8. Project persistence and reload.
9. Zero regression of existing OpenReel workflow.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from starlette.testclient import TestClient

from ai_broll_autopilot.api.app import app
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.diffusion_adapter import diffusion_adapter, DIFFUSION_STUDIO_SCHEMA_VERSION
from ai_broll_autopilot.services.openreel_adapter import openreel_adapter, OPENREEL_SCHEMA_VERSION
from ai_broll_autopilot.services.editor_helper import get_job_edit_plan, get_editor_adapter
from ai_broll_autopilot.utils.timeline_math import TimelinePrecision, NormalizedClipTiming


def get_real_completed_job():
    """Retrieve an existing real completed job from database."""
    db = Database()
    jobs = db.list_jobs()
    for j in jobs:
        if j.output_video_path and Path(j.output_video_path).exists():
            return j
    return None


class TestDiffusionStudioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.job = get_real_completed_job()
        if cls.job:
            cls.edit_plan = get_job_edit_plan(cls.job)
        else:
            cls.edit_plan = None

    def setUp(self):
        if not self.job or not self.edit_plan:
            self.skipTest("No real completed Stockpile job available for testing")

    def test_1_edit_plan_to_diffusion_conversion(self):
        """Test 1: Stockpile EditPlan -> Diffusion Studio project conversion."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            project_name="Test Diffusion Project",
            base_asset_url="http://127.0.0.1:8000/api/jobs/test_job/assets",
        )

        self.assertEqual(comp_data["version"], DIFFUSION_STUDIO_SCHEMA_VERSION)
        self.assertEqual(comp_data["engine"], "diffusion")
        self.assertIn("composition", comp_data)

        comp = comp_data["composition"]
        self.assertEqual(comp["settings"]["width"], 1080)
        self.assertEqual(comp["settings"]["height"], 1920)
        self.assertEqual(comp["settings"]["fps"], 30)
        self.assertGreater(comp["settings"]["duration"], 0)

        # Must have all 7 standard layers
        layers = comp["layers"]
        layer_ids = [l["id"] for l in layers]
        self.assertIn("layer_main_video", layer_ids)
        self.assertIn("layer_broll_video", layer_ids)
        self.assertIn("layer_text_overlays", layer_ids)
        self.assertIn("layer_captions", layer_ids)
        self.assertIn("layer_audio_dialogue", layer_ids)
        self.assertIn("layer_audio_bgm", layer_ids)
        self.assertIn("layer_audio_sfx", layer_ids)

    def test_2_timeline_precision_and_drift_elimination(self):
        """Test 2: Timeline timing conversions are exact and drift-free."""
        # 21.820 to 23.140 must be exactly 1.320
        dur = TimelinePrecision.calc_duration(21.820, 23.140)
        self.assertEqual(dur, 1.320)

        # Seconds to frames and back
        frames = TimelinePrecision.seconds_to_frames(1.320, 30)
        self.assertEqual(frames, 40)
        secs = TimelinePrecision.frames_to_seconds(40, 30)
        self.assertEqual(secs, 1.333)

        # Milliseconds to seconds
        self.assertEqual(TimelinePrecision.ms_to_seconds(1320), 1.320)
        self.assertEqual(TimelinePrecision.seconds_to_ms(1.320), 1320)

        # Timecode
        tc = TimelinePrecision.seconds_to_timecode(65.5, 30)
        self.assertEqual(tc, "00:01:05:15")

        # NormalizedClipTiming contract
        timing = NormalizedClipTiming.create(
            start_time=21.820,
            duration=1.320,
            in_point=5.0,
            fps=30,
        )
        self.assertAlmostEqual(timing.start_time, 21.833, places=2)
        self.assertEqual(timing.in_point, 5.0)

    def test_3_video_and_broll_mapping(self):
        """Test 3: Main video and B-roll cutaway layer mapping."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            base_asset_url="http://127.0.0.1:8000/api/jobs/test_job/assets",
        )
        comp = comp_data["composition"]

        main_layer = next(l for l in comp["layers"] if l["id"] == "layer_main_video")
        self.assertTrue(len(main_layer["clips"]) >= 1)
        main_clip = main_layer["clips"][0]
        self.assertEqual(main_clip["type"], "video")
        self.assertEqual(main_clip["delay"], 0.0)
        self.assertGreater(main_clip["duration"], 0.0)
        self.assertTrue(len(main_clip["range"]) == 2)
        self.assertEqual(main_clip["volume"], 1.0)
        self.assertFalse(main_clip["muted"])

        broll_layer = next(l for l in comp["layers"] if l["id"] == "layer_broll_video")
        for broll_clip in broll_layer["clips"]:
            self.assertEqual(broll_clip["type"], "video")
            self.assertGreaterEqual(broll_clip["delay"], 0.0)
            self.assertGreater(broll_clip["duration"], 0.0)
            # Muted by default so speaker dialogue is not drowned
            self.assertTrue(broll_clip["muted"])

    def test_4_subtitle_and_caption_mapping(self):
        """Test 4: Subtitles and captions with word-level timing preserved."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            base_asset_url="http://127.0.0.1:8000/api/jobs/test_job/assets",
        )
        comp = comp_data["composition"]

        caption_layer = next(l for l in comp["layers"] if l["id"] == "layer_captions")
        # If edit plan has subtitles, verify they map correctly
        if self.edit_plan.subtitles:
            self.assertTrue(len(caption_layer["clips"]) > 0)
            first_sub = caption_layer["clips"][0]
            self.assertEqual(first_sub["type"], "caption")
            self.assertIn("text", first_sub)
            self.assertIn("words", first_sub)
            self.assertIn("highlightColors", first_sub)
            self.assertGreater(first_sub["fontSize"], 0)

    def test_5_sfx_and_audio_mapping(self):
        """Test 5: Audio mix separation (Dialogue, BGM ducking, SFX)."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            base_asset_url="http://127.0.0.1:8000/api/jobs/test_job/assets",
        )
        comp = comp_data["composition"]

        dialogue_layer = next(l for l in comp["layers"] if l["id"] == "layer_audio_dialogue")
        self.assertTrue(len(dialogue_layer["clips"]) >= 1)
        self.assertEqual(dialogue_layer["clips"][0]["role"], "dialogue")
        self.assertEqual(dialogue_layer["clips"][0]["volume"], 1.0)

        bgm_layer = next(l for l in comp["layers"] if l["id"] == "layer_audio_bgm")
        # If BGM is configured, volume must be ducked under speech (0.15)
        for bgm_clip in bgm_layer["clips"]:
            self.assertEqual(bgm_clip["role"], "bgm")
            self.assertLessEqual(bgm_clip["volume"], 0.25)

        sfx_layer = next(l for l in comp["layers"] if l["id"] == "layer_audio_sfx")
        for sfx_clip in sfx_layer["clips"]:
            self.assertEqual(sfx_clip["role"], "sfx")
            self.assertGreaterEqual(sfx_clip["delay"], 0.0)

    def test_6_asset_resolution(self):
        """Test 6: Media assets use persistent URLs, no blob URLs or /tmp paths."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            base_asset_url=f"http://127.0.0.1:8000/api/jobs/{self.job.job_id}/assets",
        )
        comp = comp_data["composition"]

        for layer in comp["layers"]:
            for clip in layer["clips"]:
                source = clip.get("source")
                if source:
                    # Must not be a temporary blob URL or /tmp path
                    self.assertFalse(source.startswith("blob:"), f"Found temporary blob URL in {clip['id']}")
                    self.assertFalse(source.startswith("/tmp"), f"Found /tmp path in {clip['id']}")
                    self.assertTrue(
                        source.startswith("http://") or source.startswith("https://") or source.startswith("file:///"),
                        f"Invalid source URL format: {source}",
                    )

    def test_7_diffusion_to_openreel_handoff(self):
        """Test 7: Diffusion Studio composition -> OpenReel Schema 1.2.0 handoff."""
        comp_data = diffusion_adapter.create_project(
            edit_plan=self.edit_plan,
            base_asset_url=f"http://127.0.0.1:8000/api/jobs/{self.job.job_id}/assets",
        )

        oreel_project = diffusion_adapter.to_openreel_project(
            comp_data,
            project_name="Test Diffusion Handoff",
            project_id=f"proj_{self.job.job_id}",
        )
        self.assertEqual(oreel_project["version"], OPENREEL_SCHEMA_VERSION)
        self.assertIn("project", oreel_project)

        proj = oreel_project["project"]
        self.assertEqual(proj["id"], f"proj_{self.job.job_id}")
        self.assertIn("timeline", proj)
        self.assertIn("mediaLibrary", proj)
        self.assertTrue(len(proj["timeline"]["tracks"]) >= 1)
        self.assertTrue(len(proj["mediaLibrary"]["items"]) >= 1)

        # Verify subtitles array is populated
        self.assertIn("subtitles", proj["timeline"])
        self.assertTrue(len(proj["timeline"]["subtitles"]) >= 1)
        first_sub = proj["timeline"]["subtitles"][0]
        self.assertIn("text", first_sub)
        self.assertIn("startTime", first_sub)
        self.assertIn("endTime", first_sub)

        # Verify all mediaIds referenced by clips exist in mediaLibrary
        media_id_set = {m["id"] for m in proj["mediaLibrary"]["items"]}
        for track in proj["timeline"]["tracks"]:
            for clip in track.get("clips", []):
                if "mediaId" in clip:
                    self.assertIn(clip["mediaId"], media_id_set)

    def test_10_diffusion_to_openreel_api_endpoint(self):
        """Test 10: Endpoint /api/jobs/{job_id}/diffusion-to-openreel produces valid deterministic project."""
        response = self.client.get(f"/api/jobs/{self.job.job_id}/diffusion-to-openreel")
        self.assertEqual(response.status_code, 200)
        oreel_data = response.json()
        self.assertEqual(oreel_data["version"], "1.2.0")
        proj = oreel_data["project"]
        self.assertEqual(proj["id"], f"proj_{self.job.job_id}")
        self.assertIn("subtitles", proj["timeline"])
        self.assertTrue(len(proj["timeline"]["subtitles"]) >= 1)

    def test_8_project_persistence_and_reload(self):
        """Test 8: Project persistence and reload via API endpoint."""
        response = self.client.get(f"/api/jobs/{self.job.job_id}/diffusion-project")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["engine"], "diffusion")

        # Verify file was persisted on disk
        persisted_file = Path("output") / "workspace" / self.job.job_id / "diffusion" / "composition.json"
        self.assertTrue(persisted_file.exists(), f"Persisted file missing at {persisted_file}")

        with open(persisted_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["version"], DIFFUSION_STUDIO_SCHEMA_VERSION)

    def test_9_regression_of_existing_openreel_workflow(self):
        """Test 9: Verify existing OpenReel endpoint and media streaming remain 100% functional."""
        # 1. OpenReel project endpoint
        r_oreel = self.client.get(f"/api/jobs/{self.job.job_id}/openreel-project")
        self.assertEqual(r_oreel.status_code, 200)
        oreel_data = r_oreel.json()
        self.assertEqual(oreel_data["version"], "1.2.0")

        # 2. Polymorphic editor project endpoint
        r_poly_oreel = self.client.get(f"/api/jobs/{self.job.job_id}/editor-project?engine=openreel")
        self.assertEqual(r_poly_oreel.status_code, 200)
        self.assertEqual(r_poly_oreel.json()["version"], "1.2.0")

        r_poly_dif = self.client.get(f"/api/jobs/{self.job.job_id}/editor-project?engine=diffusion")
        self.assertEqual(r_poly_dif.status_code, 200)
        self.assertEqual(r_poly_dif.json()["engine"], "diffusion")

        # 3. Media streaming range requests
        r_stream = self.client.get(
            f"/api/jobs/{self.job.job_id}/assets/final",
            headers={"Range": "bytes=0-1023"}
        )
        self.assertEqual(r_stream.status_code, 206)
        self.assertEqual(r_stream.headers.get("accept-ranges"), "bytes")
        self.assertEqual(len(r_stream.content), 1024)


if __name__ == "__main__":
    unittest.main()
