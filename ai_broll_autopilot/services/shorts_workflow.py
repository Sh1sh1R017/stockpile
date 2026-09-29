"""Helpers for turning long-form clip candidates into Stockpile child edits."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_broll_autopilot.services.clip_detector import ClipCandidate


def normalize_clip_candidate(raw: Dict[str, Any], index: int = 0) -> Optional[Dict[str, Any]]:
    """Normalize OpenShorts/clip-discovery output into a safe Stockpile candidate."""
    try:
        start = float(raw.get("start", raw.get("start_time")))
        end = float(raw.get("end", raw.get("end_time")))
    except (TypeError, ValueError):
        return None

    if end <= start or start < 0:
        return None

    title = str(
        raw.get("title")
        or raw.get("video_title_for_youtube_short")
        or f"Short {index + 1}"
    ).strip()

    return {
        "id": str(raw.get("id") or f"openshorts_{index + 1}"),
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(end - start, 3),
        "title": title[:160],
        "summary": str(raw.get("summary") or title).strip()[:500],
        "hook_text": str(raw.get("hook_text") or title).strip()[:180],
        "source": "openshorts",
        "provider": "openshorts",
    }


def normalize_clip_transcript(
    transcript_segments: List[Dict[str, Any]],
    clip_start: float,
    clip_end: float,
) -> List[Dict[str, Any]]:
    """Slice transcript to an absolute interval and normalize timestamps to clip time."""
    duration = max(0.0, clip_end - clip_start)
    result: List[Dict[str, Any]] = []

    for segment in transcript_segments or []:
        seg_start = float(segment.get("start", 0.0))
        seg_end = float(segment.get("end", seg_start))
        if seg_end <= clip_start or seg_start >= clip_end:
            continue

        out: Dict[str, Any] = {
            "start": round(max(0.0, seg_start - clip_start), 3),
            "end": round(min(duration, seg_end - clip_start), 3),
            "text": str(segment.get("text", "")).strip(),
        }

        words = []
        for word in segment.get("words", []) or []:
            w_start = float(word.get("start", seg_start))
            w_end = float(word.get("end", w_start))
            if w_end <= clip_start or w_start >= clip_end:
                continue
            text = str(word.get("word", word.get("text", ""))).strip()
            if not text:
                continue
            words.append(
                {
                    "word": text,
                    "start": round(max(0.0, w_start - clip_start), 3),
                    "end": round(min(duration, w_end - clip_start), 3),
                }
            )
        if words:
            out["words"] = words

        if out["end"] > out["start"]:
            result.append(out)

    return result


def build_clip_candidate(
    normalized: Dict[str, Any],
    source_duration: float,
) -> ClipCandidate:
    """Build the existing ClipCandidate type without introducing another schema."""
    start = max(0.0, min(float(normalized["start"]), float(source_duration)))
    end = max(start + 0.25, min(float(normalized["end"]), float(source_duration)))
    return ClipCandidate(
        id=str(normalized.get("id", "openshorts_clip")),
        start_time=start,
        end_time=end,
        duration=end - start,
        title=str(normalized.get("title") or "Short"),
        hook_text=str(normalized.get("hook_text") or normalized.get("title") or ""),
        summary=str(normalized.get("summary") or ""),
        viral_score=80.0,
        factor_scores={},
        rationale="OpenShorts long-form clip discovery candidate.",
        suggested_broll_topics=[],
        tags=["openshorts", "long-form"],
    )


def workflow_record(
    *,
    parent_job_id: str,
    source: str,
    start: float,
    end: float,
    title: str,
    batch_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    caption_style: Optional[str] = None,
    caption_motion: Optional[str] = None,
    subtitles_behind_subject: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return additive workflow metadata kept inside the canonical EditPlan."""
    return {
        "type": "short_edit",
        "source": source,
        "parent_job_id": parent_job_id,
        "batch_id": batch_id,
        "candidate_id": candidate_id,
        "source_interval": {
            "start": round(float(start), 3),
            "end": round(float(end), 3),
        },
        "title": title,
        "caption_style": caption_style,
        "caption_motion": caption_motion,
        "subtitles_behind_subject": subtitles_behind_subject,
        "status": "queued",
    }


__all__ = [
    "normalize_clip_candidate",
    "normalize_clip_transcript",
    "build_clip_candidate",
    "workflow_record",
]
