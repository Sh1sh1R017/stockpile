"""Executable editorial plan invariants used by tests and runtime QA."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from ai_broll_autopilot.config import Config


TIME_KEYS = (
    "start_time",
    "end_time",
    "timestamp",
    "start",
    "end",
)


def _items(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, dict))
    return ()


def collect_plan_invariant_violations(
    plan: Dict[str, Any],
    *,
    target_duration: float | None = None,
    min_broll_duration: float | None = None,
    max_broll_duration: float | None = None,
    hook_guard_seconds: float = 1.2,
) -> List[str]:
    """Return human-readable violations without mutating the plan."""
    duration = float(
        target_duration
        if target_duration is not None
        else plan.get("target_duration", plan.get("total_duration", 0.0))
    )
    min_broll = float(
        min_broll_duration
        if min_broll_duration is not None
        else getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65)
    )
    max_broll = float(
        max_broll_duration
        if max_broll_duration is not None
        else getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8)
    )

    violations: List[str] = []

    def check_time(owner: str, value: Any) -> None:
        try:
            t = float(value)
        except (TypeError, ValueError):
            violations.append(f"{owner}: non-numeric time {value!r}")
            return
        if t < -1e-6 or t > duration + 1e-6:
            violations.append(f"{owner}: time {t:.3f}s outside [0,{duration:.3f}]")

    for collection_name in ("shots", "broll_shots", "text_overlays", "graphics", "subtitles", "zooms", "camera_moves"):
        for index, item in enumerate(_items(plan.get(collection_name, []))):
            for key in TIME_KEYS:
                if key in item:
                    check_time(f"{collection_name}[{index}].{key}", item[key])

    audio = plan.get("audio_cues", plan.get("sfx_cues", []))
    audio_items = []
    if isinstance(audio, dict):
        for value in audio.values():
            audio_items.extend(list(_items(value)))
    elif isinstance(audio, list):
        audio_items = list(_items(audio))
    for index, item in enumerate(audio_items):
        for key in ("start_time", "timestamp"):
            if key in item:
                check_time(f"audio_cues[{index}].{key}", item[key])

    shots = [
        shot for shot in _items(plan.get("shots", plan.get("broll_shots", [])))
        if shot.get("asset_path")
        and shot.get("status", "matched") not in {"rejected", "retained_a_roll"}
    ]
    shots.sort(key=lambda shot: float(shot.get("start_time", 0.0)))

    previous_end = None
    for index, shot in enumerate(shots):
        start = float(shot.get("start_time", 0.0))
        end = float(shot.get("end_time", start))
        duration_value = float(shot.get("duration", end - start))

        if end <= start:
            violations.append(f"shots[{index}]: end must be greater than start")
        if abs(duration_value - (end - start)) > 0.051:
            violations.append(f"shots[{index}]: duration disagrees with interval")
        if duration_value < min_broll - 1e-6 or duration_value > max_broll + 1e-6:
            violations.append(
                f"shots[{index}]: B-roll duration {duration_value:.3f}s outside "
                f"[{min_broll:.3f},{max_broll:.3f}]"
            )
        if start < hook_guard_seconds - 1e-6:
            violations.append(
                f"shots[{index}]: B-roll starts at {start:.3f}s before {hook_guard_seconds:.3f}s hook guard"
            )
        approved_start = shot.get("approved_start_time")
        approved_end = shot.get("approved_end_time")
        if approved_start is not None and start > float(approved_start) + 1e-6 and not shot.get("adjustment_log"):
            violations.append(
                f"shots[{index}]: interval changed without an adjustment log"
            )
        if approved_end is not None and end > float(approved_end) + 1e-6:
            violations.append(
                f"shots[{index}]: downstream stage lengthened an approved interval"
            )

        if shot.get("watermarked"):
            violations.append(f"shots[{index}]: accepted asset is watermarked")

        width, height = shot.get("width"), shot.get("height")
        if width is not None and height is not None and min(int(width), int(height)) < 720:
            violations.append(f"shots[{index}]: accepted asset is below 720px")

        raw_asset_duration = shot.get("source_duration", shot.get("asset_duration"))
        if raw_asset_duration is not None:
            speed = max(0.1, float(shot.get("speed") or 1.0))
            effective = float(raw_asset_duration) / speed
            if effective + 0.05 < duration_value:
                violations.append(f"shots[{index}]: asset is shorter than approved interval")

        if previous_end is not None and start < previous_end - 1e-6:
            violations.append(f"shots[{index}]: B-roll overlaps a previous accepted B-roll interval")
        previous_end = end

    # Word timestamps must stay inside their parent transcript segment when
    # transcript data is available in the plan/test fixture.
    segments = plan.get("transcript_segments", [])
    for si, segment in enumerate(_items(segments)):
        try:
            segment_start = float(segment.get("start", 0.0))
            segment_end = float(segment.get("end", segment_start))
        except (TypeError, ValueError):
            violations.append(f"transcript_segments[{si}]: invalid segment timing")
            continue
        for wi, word in enumerate(_items(segment.get("words", []))):
            try:
                ws = float(word.get("start", segment_start))
                we = float(word.get("end", ws))
            except (TypeError, ValueError):
                violations.append(f"transcript_segments[{si}].words[{wi}]: invalid timing")
                continue
            if ws < segment_start - 1e-6 or we > segment_end + 1e-6 or we < ws:
                violations.append(f"transcript_segments[{si}].words[{wi}]: word outside segment")

    return violations


def assert_plan_invariants(plan: Dict[str, Any], **kwargs: Any) -> None:
    """Raise AssertionError with all detected violations."""
    violations = collect_plan_invariant_violations(plan, **kwargs)
    assert not violations, "Plan invariant violations:\n" + "\n".join(violations)
