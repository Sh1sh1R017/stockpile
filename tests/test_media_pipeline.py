"""Automated Regression & Media Infrastructure Test Suite.

Verifies:
1. MediaValidator probing (container layout, moov/mdat offsets, GOP, codecs, non-negative timestamps).
2. Auto-remediation with faststart and non-negative TS normalization.
3. HTTP Streaming compliance (GET 200, HEAD, Range 206 partial content, 416 bounds, Accept-Ranges, Content-Range).
4. Job ID resolution across unencoded, single-encoded (%28), and double-encoded (%2528) URLs.
5. OpenReel project JSON generation and multitrack collision-prevention rules.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from starlette.testclient import TestClient

from ai_broll_autopilot.services.media_validator import media_validator, MediaValidationResult
from ai_broll_autopilot.api.app import app
from ai_broll_autopilot.core.database import Database


def get_test_job():
    """Retrieve an existing completed job from database."""
    db = Database()
    jobs = db.list_jobs()
    for j in jobs:
        if j.output_video_path and Path(j.output_video_path).exists():
            return j
    return None


class TestMediaValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.job = get_test_job()

    def test_probe_existing_media(self):
        if not self.job:
            self.skipTest("No existing rendered media found to probe")

        target_file = Path(self.job.output_video_path)
        self.assertTrue(target_file.exists(), f"Video file not found at {target_file}")

        report = media_validator.validate(target_file, auto_remedy=True)

        self.assertTrue(report.is_valid, f"Media validation failed: {report.errors}")
        self.assertTrue(bool(report.video_codec), "Video stream missing")
        self.assertTrue(bool(report.audio_codec), "Audio stream missing")
        self.assertEqual(report.pixel_format, "yuv420p", f"Expected yuv420p, got {report.pixel_format}")
        self.assertTrue(report.has_faststart, "moov atom must precede mdat atom for progressive streaming")
        self.assertFalse(report.has_negative_ts, "Packet timestamps must be non-negative")

    def test_remediation_non_faststart(self):
        test_file = Path("input/0819(5).mp4")
        if not test_file.exists():
            self.skipTest("Reference input file input/0819(5).mp4 not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_copy = Path(tmpdir) / "test_copy.mp4"
            shutil.copyfile(test_file, temp_copy)

            report = media_validator.validate(temp_copy, auto_remedy=True)
            self.assertTrue(report.is_valid)
            self.assertTrue(report.has_faststart)
            self.assertFalse(report.has_negative_ts)


class TestHttpStreamingEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.job = get_test_job()

    def test_get_job_video_full(self):
        if not self.job:
            self.skipTest("No test job available")

        response = self.client.get(f"/api/jobs/{self.job.job_id}/assets/final")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("accept-ranges"), "bytes")
        self.assertIn("video/mp4", response.headers.get("content-type", ""))
        self.assertGreater(int(response.headers.get("content-length", 0)), 0)

    def test_get_job_video_head(self):
        if not self.job:
            self.skipTest("No test job available")

        response = self.client.head(f"/api/jobs/{self.job.job_id}/assets/final")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("accept-ranges"), "bytes")
        self.assertIn("video/mp4", response.headers.get("content-type", ""))
        self.assertGreater(int(response.headers.get("content-length", 0)), 0)
        self.assertEqual(len(response.content), 0)

    def test_get_job_video_range_start(self):
        if not self.job:
            self.skipTest("No test job available")

        headers = {"Range": "bytes=0-1023"}
        response = self.client.get(f"/api/jobs/{self.job.job_id}/assets/final", headers=headers)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers.get("accept-ranges"), "bytes")
        self.assertEqual(len(response.content), 1024)

        content_range = response.headers.get("content-range", "")
        self.assertTrue(content_range.startswith("bytes 0-1023/"))

    def test_get_job_video_range_suffix(self):
        if not self.job:
            self.skipTest("No test job available")

        headers = {"Range": "bytes=-500"}
        response = self.client.get(f"/api/jobs/{self.job.job_id}/assets/final", headers=headers)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.content), 500)
        self.assertEqual(response.headers.get("accept-ranges"), "bytes")

    def test_get_job_video_invalid_range(self):
        if not self.job:
            self.skipTest("No test job available")

        headers = {"Range": "bytes=999999999-9999999999"}
        response = self.client.get(f"/api/jobs/{self.job.job_id}/assets/final", headers=headers)
        self.assertEqual(response.status_code, 416)

    def test_cors_headers_exposed(self):
        if not self.job:
            self.skipTest("No test job available")

        response = self.client.get(
            f"/api/jobs/{self.job.job_id}/assets/final",
            headers={"Origin": "http://localhost:5173"}
        )
        exposed = response.headers.get("access-control-expose-headers", "").lower()
        self.assertIn("accept-ranges", exposed)
        self.assertIn("content-range", exposed)
        self.assertIn("content-length", exposed)


class TestUrlEncodingRobustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.job = get_test_job()

    def test_job_id_with_special_characters(self):
        if not self.job:
            self.skipTest("No test job available")

        # Test single encoded
        single_encoded = self.job.job_id.replace("(", "%28").replace(")", "%29")
        r1 = self.client.get(f"/api/jobs/{single_encoded}/assets/final", headers={"Range": "bytes=0-100"})
        self.assertEqual(r1.status_code, 206)

        # Test double encoded (%28 -> %2528)
        double_encoded = self.job.job_id.replace("(", "%2528").replace(")", "%2529")
        r2 = self.client.get(f"/api/jobs/{double_encoded}/assets/final", headers={"Range": "bytes=0-100"})
        self.assertEqual(r2.status_code, 206)

        # Test project endpoint with single and double encoding
        p1 = self.client.get(f"/api/jobs/{single_encoded}/openreel-project")
        self.assertEqual(p1.status_code, 200)
        p2 = self.client.get(f"/api/jobs/{double_encoded}/openreel-project")
        self.assertEqual(p2.status_code, 200)


class TestOpenReelProjectStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.job = get_test_job()

    def test_rendered_mode_multitrack_collision_prevention(self):
        if not self.job:
            self.skipTest("No test job available")

        response = self.client.get(f"/api/jobs/{self.job.job_id}/openreel-project?mode=rendered")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["version"], "1.2.0")
        project = data.get("project", data)
        tracks = project["timeline"]["tracks"]
        video_tracks = [t for t in tracks if t["type"] == "video"]
        self.assertTrue(len(video_tracks) >= 1)

        # Track 1 (Master render) must not be hidden
        self.assertFalse(video_tracks[0].get("hidden", False))

        # If secondary B-roll video track exists in rendered mode, it must be hidden to prevent collision
        if len(video_tracks) > 1:
            self.assertTrue(video_tracks[1].get("hidden"), "Secondary B-roll track must be hidden in rendered mode")

        # Media library should contain the master asset with streaming URL
        items = project["mediaLibrary"]["items"]
        self.assertTrue(len(items) >= 1)
        master_item = items[0]
        self.assertEqual(master_item["type"], "video")
        self.assertTrue(master_item["url"].startswith("http://127.0.0.1:8000/api/jobs/"))


if __name__ == "__main__":
    unittest.main()
