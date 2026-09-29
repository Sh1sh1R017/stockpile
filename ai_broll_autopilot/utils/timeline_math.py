"""Centralized Timeline Timing & Precision Math Infrastructure.

Guarantees exact, drift-free conversions between seconds, milliseconds,
frames, and timecodes across Stockpile, OpenReel, and Diffusion Studio.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Union, Optional


class TimelinePrecision:
    """Precision timing utilities to eliminate floating-point drift across editors."""

    DEFAULT_FPS = 30
    DEFAULT_PRECISION = 3  # Millisecond precision (0.001s)

    @staticmethod
    def quantize(value: Union[float, int, Decimal, str], precision: int = 3) -> float:
        """Quantize a float to exact decimal precision to avoid 0.30000000000000004 issues."""
        if value is None:
            return 0.0
        d = Decimal(str(value))
        exp = Decimal(10) ** -precision
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))

    @classmethod
    def seconds_to_frames(cls, seconds: float, fps: int = DEFAULT_FPS) -> int:
        """Convert fractional seconds to discrete integer frames."""
        return int(round(seconds * fps))

    @classmethod
    def frames_to_seconds(cls, frames: int, fps: int = DEFAULT_FPS) -> float:
        """Convert integer frames back to exact fractional seconds."""
        if fps <= 0:
            fps = cls.DEFAULT_FPS
        val = Decimal(frames) / Decimal(fps)
        return cls.quantize(val, cls.DEFAULT_PRECISION)

    @classmethod
    def seconds_to_ms(cls, seconds: float) -> int:
        """Convert fractional seconds to integer milliseconds."""
        return int(round(seconds * 1000))

    @classmethod
    def ms_to_seconds(cls, ms: int) -> float:
        """Convert integer milliseconds to fractional seconds."""
        return cls.quantize(Decimal(ms) / Decimal(1000), cls.DEFAULT_PRECISION)

    @classmethod
    def calc_duration(cls, start: float, end: float) -> float:
        """Calculate exact duration start -> end without drift."""
        s = Decimal(str(cls.quantize(start)))
        e = Decimal(str(cls.quantize(end)))
        dur = max(Decimal(0), e - s)
        return float(dur.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))

    @classmethod
    def seconds_to_timecode(cls, seconds: float, fps: int = DEFAULT_FPS) -> str:
        """Convert seconds into SMPTE-style timecode HH:MM:SS:FF."""
        total_frames = cls.seconds_to_frames(seconds, fps)
        f = total_frames % fps
        total_seconds = total_frames // fps
        s = total_seconds % 60
        total_minutes = total_seconds // 60
        m = total_minutes % 60
        h = total_minutes // 60
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    @classmethod
    def snap_to_frame(cls, seconds: float, fps: int = DEFAULT_FPS) -> float:
        """Snap a floating-point timestamp to the nearest frame boundary."""
        frames = cls.seconds_to_frames(seconds, fps)
        return cls.frames_to_seconds(frames, fps)


@dataclass(frozen=True)
class NormalizedClipTiming:
    """Normalized, drift-free clip timing contract."""
    start_time: float       # Timeline start (seconds)
    duration: float         # Timeline duration (seconds)
    end_time: float         # Timeline end (seconds)
    in_point: float         # Media source in-point (seconds)
    out_point: float        # Media source out-point (seconds)
    source_duration: float  # Source media duration (seconds)

    @classmethod
    def create(
        cls,
        start_time: float,
        duration: Optional[float] = None,
        end_time: Optional[float] = None,
        in_point: float = 0.0,
        out_point: Optional[float] = None,
        source_duration: Optional[float] = None,
        fps: int = 30,
    ) -> "NormalizedClipTiming":
        start_q = TimelinePrecision.snap_to_frame(start_time, fps)

        if duration is not None:
            dur_q = TimelinePrecision.quantize(duration)
            end_q = TimelinePrecision.snap_to_frame(start_q + dur_q, fps)
            dur_q = TimelinePrecision.calc_duration(start_q, end_q)
        elif end_time is not None:
            end_q = TimelinePrecision.snap_to_frame(end_time, fps)
            dur_q = TimelinePrecision.calc_duration(start_q, end_q)
        else:
            dur_q = 0.0
            end_q = start_q

        in_q = TimelinePrecision.quantize(in_point)
        if out_point is not None:
            out_q = TimelinePrecision.quantize(out_point)
        else:
            out_q = TimelinePrecision.quantize(in_q + dur_q)

        src_dur = TimelinePrecision.quantize(source_duration) if source_duration else out_q

        return cls(
            start_time=start_q,
            duration=dur_q,
            end_time=end_q,
            in_point=in_q,
            out_point=out_q,
            source_duration=src_dur,
        )
