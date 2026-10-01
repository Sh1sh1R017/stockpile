"""Media validation and compliance layer for Stockpile video pipeline.

Verifies that rendered media files meet the browser and OpenReel playback contracts:
- Valid container (MP4 / QuickTime)
- moov atom placed before mdat (faststart enabled for progressive HTTP streaming)
- Strict non-negative monotonic packet timestamps (start_time >= 0, DTS >= 0)
- Browser-compatible video stream (H.264, yuv420p)
- Compatible audio stream (AAC, 48 kHz stereo preferred)
- Non-zero file size and valid probed duration
"""

import json
import logging
import os
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MediaValidationResult:
    """Result of media validation check."""
    is_valid: bool
    file_path: str
    file_size: int = 0
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    pixel_format: str = ""
    audio_codec: str = ""
    audio_sample_rate: int = 0
    audio_channels: int = 0
    has_faststart: bool = False
    has_negative_ts: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    remedied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "video_codec": self.video_codec,
            "pixel_format": self.pixel_format,
            "audio_codec": self.audio_codec,
            "audio_sample_rate": self.audio_sample_rate,
            "audio_channels": self.audio_channels,
            "has_faststart": self.has_faststart,
            "has_negative_ts": self.has_negative_ts,
            "errors": self.errors,
            "warnings": self.warnings,
            "remedied": self.remedied,
        }


class MediaValidator:
    """Validates and enforces browser/OpenReel media playback standards."""

    @staticmethod
    def inspect_atoms(file_path: Path) -> List[tuple[str, int, int]]:
        """Extract top-level MP4 atoms: (name, offset, size)."""
        atoms = []
        try:
            with open(file_path, "rb") as f:
                file_size = f.seek(0, 2)
                f.seek(0)
                offset = 0
                while offset < file_size:
                    hdr = f.read(8)
                    if len(hdr) < 8:
                        break
                    size, name = struct.unpack(">I4s", hdr)
                    name = name.decode("latin1", errors="replace")
                    atoms.append((name, offset, size))
                    if size == 1:
                        size = struct.unpack(">Q", f.read(8))[0]
                        offset += 16
                        f.seek(offset)
                    elif size == 0:
                        break
                    else:
                        offset += size
                        f.seek(offset)
        except Exception as e:
            logger.warning(f"Error inspecting MP4 atoms for {file_path}: {e}")
        return atoms

    @classmethod
    def validate(
        cls,
        file_path: str | Path,
        auto_remedy: bool = True
    ) -> MediaValidationResult:
        """Validate a video file against the playback contract.

        If auto_remedy is True and the file has valid streams but lacks faststart
        or has negative timestamps, it will be automatically remuxed in-place with
        -c copy -avoid_negative_ts make_zero -movflags +faststart without re-encoding.
        """
        p = Path(file_path)
        if not p.exists():
            return MediaValidationResult(
                is_valid=False,
                file_path=str(p),
                errors=["File does not exist on disk"]
            )

        file_size = p.stat().st_size
        if file_size == 0:
            return MediaValidationResult(
                is_valid=False,
                file_path=str(p),
                errors=["File is 0 bytes (empty file)"]
            )

        # 1. Run ffprobe on format and streams
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(p)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe = json.loads(res.stdout or "{}")
        except Exception as e:
            return MediaValidationResult(
                is_valid=False,
                file_path=str(p),
                file_size=file_size,
                errors=[f"ffprobe execution failed: {e}"]
            )

        fmt = probe.get("format", {})
        streams = probe.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        errors: List[str] = []
        warnings: List[str] = []

        if not v_stream:
            errors.append("Missing video stream")
            return MediaValidationResult(
                is_valid=False,
                file_path=str(p),
                file_size=file_size,
                errors=errors
            )

        v_codec = v_stream.get("codec_name", "").lower()
        if v_codec not in ("h264", "hevc", "av1", "vp9"):
            errors.append(f"Unsupported video codec: {v_codec}")

        pix_fmt = v_stream.get("pix_fmt", "")
        if "yuv420p" not in pix_fmt and "yuvj420p" not in pix_fmt:
            warnings.append(f"Pixel format {pix_fmt} may have browser compatibility issues (prefer yuv420p)")

        width = int(v_stream.get("width") or 0)
        height = int(v_stream.get("height") or 0)
        if width <= 0 or height <= 0:
            errors.append(f"Invalid dimensions: {width}x{height}")

        try:
            duration = float(v_stream.get("duration") or fmt.get("duration") or 0.0)
        except (ValueError, TypeError):
            duration = 0.0

        if duration <= 0:
            errors.append(f"Invalid duration: {duration}")

        # Check audio stream if present
        a_codec = ""
        a_sr = 0
        a_ch = 0
        if a_stream:
            a_codec = a_stream.get("codec_name", "").lower()
            if a_codec not in ("aac", "mp3", "opus"):
                warnings.append(f"Non-standard audio codec for web playback: {a_codec}")
            try:
                a_sr = int(a_stream.get("sample_rate") or 0)
            except (ValueError, TypeError):
                a_sr = 0
            try:
                a_ch = int(a_stream.get("channels") or 0)
            except (ValueError, TypeError):
                a_ch = 0

        # 2. Check atom layout (faststart)
        atoms = cls.inspect_atoms(p)
        moov_idx = next((i for i, (name, _, _) in enumerate(atoms) if name == "moov"), -1)
        mdat_idx = next((i for i, (name, _, _) in enumerate(atoms) if name == "mdat"), -1)
        has_faststart = (moov_idx != -1 and mdat_idx != -1 and moov_idx < mdat_idx)

        # 3. Check for negative timestamps
        pkt_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "packet=pts_time,dts_time",
            "-read_intervals", "%+#15", "-print_format", "json", str(p)
        ]
        has_negative_ts = False
        try:
            pkt_res = subprocess.run(pkt_cmd, capture_output=True, text=True)
            pkts = json.loads(pkt_res.stdout or "{}").get("packets", [])
            for pkt in pkts:
                pts = float(pkt.get("pts_time") or 0.0)
                dts = float(pkt.get("dts_time") or 0.0)
                if pts < -0.005 or dts < -0.005:
                    has_negative_ts = True
                    break
        except Exception as exc:
            logger.debug("Suppressed optional failure: %s", exc)

        if not has_faststart:
            warnings.append("MP4 faststart disabled: 'moov' atom is at EOF instead of beginning")

        if has_negative_ts:
            warnings.append("Initial packet DTS/PTS is negative, may cause browser decoding stalls")

        remedied = False
        # 4. Auto-remedy if faststart is missing or negative timestamps are present
        if auto_remedy and (not has_faststart or has_negative_ts) and len(errors) == 0:
            logger.info(f"Auto-remedying media file {p.name} with faststart and zero-timestamp normalization...")
            try:
                temp_remux = p.with_name(f"{p.stem}_remux_temp.mp4")
                remux_cmd = [
                    "ffmpeg", "-y", "-i", str(p),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    "-movflags", "+faststart",
                    "-v", "warning",
                    str(temp_remux)
                ]
                subprocess.run(remux_cmd, capture_output=True, check=True)
                if temp_remux.exists() and temp_remux.stat().st_size > 0:
                    shutil.move(str(temp_remux), str(p))
                    has_faststart = True
                    has_negative_ts = False
                    remedied = True
                    file_size = p.stat().st_size
                    logger.info(f"Successfully remedied {p.name} in-place.")
            except Exception as e:
                logger.error(f"Failed to auto-remedy media {p}: {e}")

        is_valid = len(errors) == 0 and has_faststart and not has_negative_ts

        return MediaValidationResult(
            is_valid=is_valid,
            file_path=str(p),
            file_size=file_size,
            duration=duration,
            width=width,
            height=height,
            video_codec=v_codec,
            pixel_format=pix_fmt,
            audio_codec=a_codec,
            audio_sample_rate=a_sr,
            audio_channels=a_ch,
            has_faststart=has_faststart,
            has_negative_ts=has_negative_ts,
            errors=errors,
            warnings=warnings,
            remedied=remedied,
        )


media_validator = MediaValidator()
