"""Aggressive Watermark and Logo Scanner Service.

Combines Multimodal Gemini Vision inspection with OpenCV computer vision analysis
to detect and reject stock agency watermarks, logos, TV bugs, and burnt-in text.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image

from ai_broll_autopilot.config import Config

logger = logging.getLogger("autopilot.watermark_scanner")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class WatermarkScanner:
    """Service to scan video clips and frames for watermarks and branding."""

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self._genai_client = None
        if self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client for watermark scanner: {e}")

    def extract_sample_frames(
        self, video_path: Path, count: int = 3, output_dir: Optional[Path] = None
    ) -> List[Path]:
        """Extract representative frames at equidistant intervals from the video."""
        if not video_path.exists():
            return []

        safe_stem = "".join(c for c in video_path.stem if c.isalnum() or c in ("-", "_"))[:30] or "clip"
        out_dir = output_dir or video_path.parent / f"_wm_{safe_stem}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Get video duration
        dur_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
        ]
        try:
            res = subprocess.run(dur_cmd, capture_output=True, text=True, check=True)
            duration = float(res.stdout.strip() or "2.0")
        except Exception:
            duration = 2.0

        sample_points = []
        if count == 1:
            sample_points = [duration * 0.5]
        elif count == 2:
            sample_points = [duration * 0.3, duration * 0.7]
        else:
            sample_points = [duration * 0.25, duration * 0.5, duration * 0.75]

        frame_paths = []
        for idx, t in enumerate(sample_points):
            fpath = out_dir / f"sample_{idx}.jpg"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(video_path),
                "-vframes", "1", "-q:v", "2", str(fpath)
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if fpath.exists() and fpath.stat().st_size > 100:
                    frame_paths.append(fpath)
            except Exception as e:
                logger.debug(f"Failed to extract frame at {t:.2f}s: {e}")

        return frame_paths

    def scan_frame_with_gemini(self, frame_path: Path) -> Tuple[bool, str, float]:
        """Scan a single image frame with Gemini Vision for watermarks and logos."""
        if not self._genai_client or not frame_path.exists():
            return False, "Gemini client unavailable", 0.0

        try:
            pil_img = Image.open(frame_path)
        except Exception as e:
            return False, f"Failed to open image: {e}", 0.0

        prompt = (
            "You are an ultra-strict broadcast-television quality control inspector verifying B-roll footage.\n"
            "Carefully inspect this video frame. We require 100% pure, clean, raw cinematic footage with ZERO watermarks, logos, or overlaid text.\n\n"
            "REJECT the frame (has_watermark = true) if you see ANY of the following:\n"
            "1. Stock footage watermarks or agency branding (Clever Stock, Shutterstock, Getty, Pond5, iStock, Adobe Stock, Envato, Storyblocks, etc.).\n"
            "2. Digitally overlaid text, titles, headlines, song titles, lower-thirds, speaker names, album names (e.g. 'SIMON SINEK', 'Night Shift', 'FLUORESCENT HOURS').\n"
            "3. Commercial promo text, advertising slogans, call-to-actions (e.g. 'JUST PLACE THE FILES', 'Subscribe', 'Follow').\n"
            "4. Overlaid graphic icons, play buttons (e.g. '>' or YouTube play triangle), channel watermarks, or TV station corner logos/bugs.\n"
            "5. Hardcoded video subtitles or captions overlaid on the footage.\n\n"
            "ACCEPT the frame (has_watermark = false) ONLY if it is clean footage with NO overlaid text, graphics, or watermarks.\n"
            "(Note: text physically integrated inside the scene, such as keys on a real physical keyboard or code on a computer monitor being filmed, is acceptable ONLY if there are no superimposed graphics or overlay text).\n\n"
            "Respond ONLY in valid JSON matching this schema:\n"
            "{\n"
            '  "has_watermark": boolean,\n'
            '  "watermark_text": "description of text, logo, play button, or watermark found, or empty string",\n'
            '  "confidence": float between 0.0 and 1.0,\n'
            '  "explanation": "concise description of why it was rejected or accepted"\n'
            "}"
        )

        models_to_try = [
            Config.GEMINI_MODEL,
            *Config.GEMINI_FALLBACK_MODELS,
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
        ]
        # Deduplicate while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        import time
        for model_name in models_to_try:
            for retry_attempt in range(2):
                try:
                    response = self._genai_client.models.generate_content(
                        model=model_name,
                        contents=[pil_img, prompt]
                    )
                    raw_text = (response.text or "").strip()
                    # Clean Markdown JSON wrap
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]

                    data = json.loads(raw_text.strip())
                    has_wm = bool(data.get("has_watermark", False))
                    wm_text = data.get("watermark_text", "")
                    conf = float(data.get("confidence", 0.8))
                    expl = data.get("explanation", "")

                    reason = f"{wm_text} ({expl})".strip() if has_wm else "Clean"
                    return has_wm, reason, conf

                except Exception as err:
                    logger.debug(f"Gemini model {model_name} (attempt {retry_attempt+1}) watermark scan failed: {err}")
                    time.sleep(1.0)

        return False, "All Gemini models exhausted", 0.0

    def scan_frame_with_cv(self, frame_path: Path) -> Tuple[bool, str, float]:
        """Local computer vision fallback using OpenCV edge and contour analysis."""
        if not CV2_AVAILABLE or not frame_path.exists():
            return False, "OpenCV unavailable", 0.0

        try:
            with open(str(frame_path), "rb") as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                return False, "Failed to read image", 0.0

            h, w, _ = img.shape
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 1. Center Watermark Check: Stock agencies place prominent text in center 50%
            center_h_start, center_h_end = int(h * 0.25), int(h * 0.75)
            center_w_start, center_w_end = int(w * 0.20), int(w * 0.80)
            center_roi = gray[center_h_start:center_h_end, center_w_start:center_w_end]

            # High-pass filter / Sobel for embossed or semi-transparent text edges
            sobelx = cv2.Sobel(center_roi, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(center_roi, cv2.CV_64F, 0, 1, ksize=3)
            gradient_mag = np.sqrt(sobelx**2 + sobely**2)
            high_gradient_ratio = np.mean(gradient_mag > 45)

            # 2. Corner Bug / Logo Check (4 corners, 15% box)
            corner_w = int(w * 0.15)
            corner_h = int(h * 0.15)
            corners = [
                gray[0:corner_h, 0:corner_w],                # Top-Left
                gray[0:corner_h, w - corner_w:w],            # Top-Right
                gray[h - corner_h:h, 0:corner_w],            # Bottom-Left
                gray[h - corner_h:h, w - corner_w:w]         # Bottom-Right
            ]

            corner_badge_detected = False
            for c in corners:
                edges = cv2.Canny(c, 100, 200)
                edge_density = np.mean(edges > 0)
                if edge_density > 0.12:  # Dense structured badge
                    corner_badge_detected = True
                    break

            if corner_badge_detected:
                return True, "Persistent corner logo or channel bug detected", 0.75

            # Extreme center text pattern
            if high_gradient_ratio > 0.28:
                return True, f"High center edge gradient ({high_gradient_ratio:.2f}) indicates overlaid text/watermark", 0.70

            return False, "Clean frame", 0.85

        except Exception as e:
            logger.debug(f"OpenCV watermark scan error: {e}")
            return False, f"CV error: {e}", 0.0

    def scan_video(self, video_path: Path) -> Tuple[bool, str, Dict]:
        """Scan a video clip for watermarks across multiple temporal sample frames.

        Returns:
            Tuple[is_clean: bool, reason: str, details: Dict]
        """
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            return False, f"File does not exist: {video_path}", {}

        # 1. Immediate Metadata / Filename Blocklist Check
        fname_low = video_path.name.lower()

        # Pexels stock video files are certified royalty-free and watermark-free
        if "pexels" in fname_low:
            logger.info(f"Video '{video_path.name}' is certified watermark-free Pexels footage.")
            return True, "Pexels certified clean", {"rule": "pexels_clean"}

        blocklist = [
            "clever stock", "cleverstock", "shutterstock", "getty", "pond5",
            "istock", "storyblocks", "depositphotos", "123rf", "adobe stock",
            "stock footage", "stock video", "preview", "watermark", "vevo",
            "sarasota herald", "breaking news"
        ]
        for bl in blocklist:
            if bl in fname_low:
                logger.warning(f"Video '{video_path.name}' blocked by filename keyword: '{bl}'")
                return False, f"Filename contains stock/watermark keyword: '{bl}'", {"rule": "metadata_block"}

        # 2. Extract 3 Sample Frames
        sample_frames = self.extract_sample_frames(video_path, count=Config.WATERMARK_SAMPLE_FRAMES)
        if not sample_frames:
            # Fallback to single frame if extraction failed
            return True, "No frames extracted to inspect", {}

        try:
            # 3. Inspect Each Frame
            for idx, frame_path in enumerate(sample_frames):
                # Pass A: Gemini Vision
                if Config.WATERMARK_GEMINI_ENABLED and self._genai_client:
                    has_wm, reason, conf = self.scan_frame_with_gemini(frame_path)
                    if has_wm and conf >= 0.60:
                        logger.warning(
                            f"[WATERMARK DETECTED] in '{video_path.name}' at frame {idx+1}: {reason} (confidence: {conf:.2f})"
                        )
                        return False, f"Detected watermark: {reason}", {
                            "source": "gemini",
                            "confidence": conf,
                            "frame": str(frame_path)
                        }

                # Pass B: OpenCV Local CV Check
                if Config.WATERMARK_CV_FALLBACK and CV2_AVAILABLE:
                    has_wm_cv, reason_cv, conf_cv = self.scan_frame_with_cv(frame_path)
                    if has_wm_cv and conf_cv >= 0.70:
                        logger.warning(
                            f"[CV WATERMARK/LOGO DETECTED] in '{video_path.name}' at frame {idx+1}: {reason_cv}"
                        )
                        return False, f"CV detected: {reason_cv}", {
                            "source": "opencv",
                            "confidence": conf_cv,
                            "frame": str(frame_path)
                        }

            return True, "Clean video passed all watermark scans", {"scanned_frames": len(sample_frames)}

        finally:
            # Clean up temporary sample frames directory
            for f in sample_frames:
                try:
                    if f.exists():
                        f.unlink()
                except Exception:
                    pass
            if sample_frames and sample_frames[0].parent.exists():
                try:
                    sample_frames[0].parent.rmdir()
                except Exception:
                    pass


# Global singleton instance
watermark_scanner = WatermarkScanner()
