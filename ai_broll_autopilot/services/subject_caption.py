"""Subject-aware subtitle planning helpers for layered caption rendering.

Keeps subtitle layer intent in the canonical EditPlan while allowing the renderer
to split captions into normal and behind-subject ASS layers.
"""

from typing import Any, Dict, List


def _flag(value: Any) -> bool:
    return bool(value)


def _time_range(item: Dict[str, Any]) -> tuple[float, float]:
    start = item.get("startTime", item.get("start", item.get("start_time", 0.0)))
    end = item.get("endTime", item.get("end", item.get("end_time", start)))
    return float(start or 0.0), float(end or start or 0.0)


def _text(item: Dict[str, Any]) -> str:
    return " ".join(str(item.get("text", "")).strip().lower().split())


def _is_behind_subject(subtitle: Dict[str, Any]) -> bool:
    return _flag(subtitle.get("behind_subject", subtitle.get("behindSubject", False)))


def annotate_segments_for_subject_captions(
    transcript_segments: List[Dict[str, Any]],
    subtitles: List[Dict[str, Any]],
    force_behind_subject: bool = False,
) -> List[Dict[str, Any]]:
    """Attach canonical behind-subject intent to transcript segments.

    Matching prefers the same subtitle index, then falls back to the subtitle with
    the strongest time/text overlap. The original transcript structure is preserved.
    """
    if not transcript_segments:
        return []

    prepared: List[Dict[str, Any]] = []
    unused = set(range(len(subtitles)))

    for index, segment in enumerate(transcript_segments):
        item = dict(segment)
        seg_start, seg_end = _time_range(segment)
        seg_text = _text(segment)

        match_index = None
        if index < len(subtitles):
            candidate = subtitles[index]
            cand_start, cand_end = _time_range(candidate)
            if (
                not unused
                or max(seg_start, cand_start) <= min(seg_end, cand_end) + 0.25
                or (seg_text and seg_text == _text(candidate))
            ):
                match_index = index

        if match_index is None and subtitles:
            best_score = -1.0
            for candidate_index in unused:
                candidate = subtitles[candidate_index]
                cand_start, cand_end = _time_range(candidate)
                overlap = max(0.0, min(seg_end, cand_end) - max(seg_start, cand_start))
                duration = max(0.01, max(seg_end, cand_end) - min(seg_start, cand_start))
                score = overlap / duration
                if seg_text and seg_text == _text(candidate):
                    score += 1.0
                if score > best_score:
                    best_score = score
                    match_index = candidate_index

        subtitle = subtitles[match_index] if match_index is not None and match_index < len(subtitles) else {}
        if match_index is not None:
            unused.discard(match_index)

        item["behind_subject"] = force_behind_subject or _is_behind_subject(subtitle)
        prepared.append(item)

    return prepared


def has_behind_subject_segments(segments: List[Dict[str, Any]]) -> bool:
    """Return whether any prepared subtitle segment belongs below the subject."""
    return any(_flag(segment.get("behind_subject", segment.get("behindSubject", False))) for segment in segments)
