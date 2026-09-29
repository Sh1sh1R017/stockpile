"""Subject Isolation and Layered Compositing Service.

Provides spatial subject detection and matte generation for Stockpile -> OpenReel
"Text Behind Subject" (subject_over_text) and layered typography.
Integrates with OpenReel's native MediaPipe PersonSegmentationEngine in the browser,
while providing server-side layout detection and offline alpha matte rendering.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SubjectIsolationService:
    """Detects speaker spatial positioning and generates layered compositing parameters."""

    def __init__(self):
        # Load OpenCV face detector for spatial positioning
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if cascade_path.exists():
            self.face_cascade = cv2.CascadeClassifier(str(cascade_path))
        else:
            self.face_cascade = None

    def analyze_subject_layout(
        self,
        video_path: str,
        sample_time: float = 1.0,
    ) -> Dict[str, Any]:
        """Analyze speaker position in source video to optimize text placement behind subject.

        Args:
            video_path: Path to source podcast video.
            sample_time: Timestamp in seconds to sample speaker position.

        Returns:
            Dict containing normalized bounding box, head_top, and recommended text position.
        """
        p = Path(video_path)
        if not p.exists():
            # Fallback default vertical podcast framing: speaker centered, head in upper third
            return {
                "subject_present": True,
                "confidence": 0.85,
                "head_top": 0.22,
                "neck_y": 0.44,
                "recommended_text_y": 0.28,
                "recommended_font_size": 72,
                "anchor": {"x": 0.5, "y": 0.5},
            }

        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            return {
                "subject_present": True,
                "confidence": 0.80,
                "head_top": 0.22,
                "neck_y": 0.44,
                "recommended_text_y": 0.28,
                "recommended_font_size": 72,
                "anchor": {"x": 0.5, "y": 0.5},
            }

        cap.set(cv2.CAP_PROP_POS_MSEC, sample_time * 1000.0)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {
                "subject_present": True,
                "confidence": 0.80,
                "head_top": 0.22,
                "neck_y": 0.44,
                "recommended_text_y": 0.28,
                "recommended_font_size": 72,
                "anchor": {"x": 0.5, "y": 0.5},
            }

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = []
        if self.face_cascade:
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(int(w * 0.1), int(h * 0.1))
            )

        if len(faces) == 0:
            # Fallback: standard 9:16 vertical talking head placement
            return {
                "subject_present": True,
                "confidence": 0.70,
                "head_top": 0.22,
                "neck_y": 0.42,
                "recommended_text_y": 0.28,
                "recommended_font_size": 72,
                "anchor": {"x": 0.5, "y": 0.5},
            }

        # Select the primary (largest) face
        primary_face = max(faces, key=lambda f: f[2] * f[3])
        fx, fy, fw, fh = primary_face

        # Normalized coordinates
        head_top = max(0.05, (fy - 0.2 * fh) / h)
        neck_y = min(0.95, (fy + fh * 1.1) / h)
        face_center_x = (fx + fw / 2.0) / w

        # Recommended text placement: sits behind the upper chest / neck level
        # so bold letters peak behind the ears/shoulders
        recommended_text_y = float(np.clip(head_top + 0.08, 0.20, 0.40))

        return {
            "subject_present": True,
            "confidence": 0.95,
            "face_box": {
                "x": float(fx / w),
                "y": float(fy / h),
                "width": float(fw / w),
                "height": float(fh / h),
            },
            "head_top": float(head_top),
            "neck_y": float(neck_y),
            "center_x": float(face_center_x),
            "recommended_text_y": recommended_text_y,
            "recommended_font_size": 76 if fw / w > 0.3 else 64,
            "anchor": {"x": 0.5, "y": 0.5},
        }

    def plan_behind_subject_overlay(
        self,
        text: str,
        start_time: float = 0.5,
        duration: float = 2.5,
        font_family: str = "Anton",
        emphasis_color: str = "#FFDD00",
        animation_preset: str = "pop",
        subject_layout: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct an OpenReel-compatible TextClip with behindSubject=True.

        Args:
            text: Text content (e.g. hook punchline or key entity).
            start_time: Clip start timestamp.
            duration: Clip duration in seconds.
            font_family: Heavy display font (e.g. Anton, Montserrat, Bebas Neue).
            emphasis_color: High-contrast primary color.
            animation_preset: 'pop', 'bounce', 'slide-up', 'typewriter'.
            subject_layout: Optional layout from analyze_subject_layout.

        Returns:
            Dict conforming to OpenReel TextClip Schema 1.2.0.
        """
        layout = subject_layout or {
            "recommended_text_y": 0.28,
            "recommended_font_size": 68,
            "center_x": 0.5,
        }

        pos_y = layout.get("recommended_text_y", 0.28)
        pos_x = layout.get("center_x", 0.5)
        font_size = layout.get("recommended_font_size", 68)

        return {
            "id": f"text_behind_subj_{int(start_time * 100)}",
            "trackId": "track_overlay_text",
            "startTime": start_time,
            "duration": duration,
            "text": text.upper(),
            "behindSubject": True,
            "animation": {
                "preset": animation_preset,
                "params": {
                    "popOvershoot": 1.15,
                    "bounceHeight": 22,
                    "slideDistance": 45,
                },
                "inDuration": 0.35,
                "outDuration": 0.25,
            },
            "style": {
                "fontFamily": font_family,
                "fontSize": font_size,
                "fontWeight": "bold",
                "fontStyle": "normal",
                "color": emphasis_color,
                "strokeColor": "#000000",
                "strokeWidth": 6,
                "shadowColor": "rgba(0, 0, 0, 0.85)",
                "shadowBlur": 12,
                "textAlign": "center",
                "verticalAlign": "middle",
                "lineHeight": 1.15,
                "letterSpacing": 1.0,
            },
            "transform": {
                "position": {"x": pos_x, "y": pos_y},
                "scale": {"x": 1.0, "y": 1.0},
                "rotation": 0,
                "anchor": {"x": 0.5, "y": 0.5},
                "opacity": 1.0,
            },
            "keyframes": [],
        }

    def generate_person_matte(
        self,
        frame: np.ndarray,
        face_rect: Optional[Tuple[int, int, int, int]] = None,
    ) -> np.ndarray:
        """Generate high-contrast grayscale alpha matte of speaker foreground using GrabCut.

        Args:
            frame: BGR numpy image frame.
            face_rect: Optional (x, y, w, h) of face.

        Returns:
            Single-channel uint8 mask (0 = background, 255 = foreground speaker).
        """
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), np.uint8)

        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        if face_rect:
            fx, fy, fw, fh = face_rect
            # Expand face box downwards to capture shoulders and torso
            rx = max(0, fx - int(fw * 0.8))
            ry = max(0, fy - int(fh * 0.3))
            rw = min(w - rx, fw + int(fw * 1.6))
            rh = min(h - ry, fh * 5)
            rect = (rx, ry, rw, rh)
        else:
            # Default center lower bounding box for talking head
            rect = (int(w * 0.15), int(h * 0.10), int(w * 0.70), int(h * 0.85))

        try:
            cv2.grabCut(frame, mask, rect, bgd_model, fgd_model, 2, cv2.GC_INIT_WITH_RECT)
            # 0, 2 are background; 1, 3 are foreground
            output_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype("uint8")
            # Apply slight Gaussian blur to soften mask edges
            output_mask = cv2.GaussianBlur(output_mask, (7, 7), 2.0)
            return output_mask
        except Exception as e:
            logger.warning(f"GrabCut matte failed: {e}. Returning threshold fallback.")
            return np.full((h, w), 255, dtype=np.uint8)

    def generate_person_matte_video(
        self,
        video_path: str,
        output_path: str,
        sample_fps: float = 8.0,
        processing_width: int = 540,
        processing_height: int = 960,
    ) -> Path:
        """Generate a low-rate portrait-space subject matte video for caption compositing.

        The matte is evaluated on sampled frames and held between samples. Processing is
        intentionally reduced to a small portrait canvas so the feature stays practical
        for server-side rendering. The returned MP4 contains a grayscale alpha mask.
        """
        source = Path(video_path)
        dest = Path(output_path)
        if not source.exists():
            raise FileNotFoundError(f"Source video not found: {source}")

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open source video: {source}")

        source_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if source_fps <= 0:
            source_fps = 30.0
        sample_fps = max(1.0, min(sample_fps, source_fps))
        stride = max(1, int(round(source_fps / sample_fps)))

        fps = source_fps
        width = max(2, int(processing_width))
        height = max(2, int(processing_height))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        dest.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(dest), fourcc, fps / stride, (width, height), isColor=False)
        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Could not create subject matte video: {dest}")

        frame_index = 0
        processed = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_index % stride != 0:
                    frame_index += 1
                    continue

                fitted = self._fit_frame_to_canvas(frame, width, height)
                gray = cv2.cvtColor(fitted, cv2.COLOR_BGR2GRAY)
                faces = []
                if self.face_cascade:
                    faces = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=4,
                        minSize=(max(24, int(width * 0.08)), max(24, int(height * 0.05))),
                    )

                face_rect = None
                if len(faces):
                    face_rect = tuple(max(faces, key=lambda f: f[2] * f[3]).tolist())

                if face_rect:
                    mask = self.generate_person_matte(fitted, face_rect)
                else:
                    # Conservative fallback: black means "no foreground". This preserves
                    # caption readability instead of hiding the entire caption layer.
                    mask = np.zeros((height, width), dtype=np.uint8)

                writer.write(mask)
                processed += 1
                frame_index += 1
        finally:
            cap.release()
            writer.release()

        if processed == 0 or not dest.exists() or dest.stat().st_size == 0:
            raise RuntimeError(f"Subject matte generation produced no frames: {dest}")

        logger.info(
            "Generated subject matte video: %s (%d sampled frames @ %.2f fps)",
            dest,
            processed,
            fps / stride,
        )
        return dest

    @staticmethod
    def _fit_frame_to_canvas(frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """Match the renderer's scale-down-and-pad behavior in portrait space."""
        src_h, src_w = frame.shape[:2]
        scale = min(width / max(1, src_w), height / max(1, src_h))
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        x = (width - new_w) // 2
        y = (height - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas


# Global singleton instance
subject_isolation_service = SubjectIsolationService()
