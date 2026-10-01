"""Shared transcript time-base normalization for clip-scoped editorial processing."""

import math


def scope_segments(segments, clip_in, clip_out):
    raw_duration = max(1.0, float(clip_out) - float(clip_in))
    # Return the greatest representable float strictly below the raw duration.
    # This avoids rare property-test failures caused by subtraction rounding
    # nudging an end timestamp one ulp above the mathematically intended bound.
    duration = math.nextafter(raw_duration, 0.0)
    out = []
    for seg in segments or []:
        st, et = float(seg.get("start", 0)), float(seg.get("end", 0))
        if et <= clip_in or st >= clip_out:
            continue
        words = []
        for word in seg.get("words") or []:
            ws = float(word.get("start", st)) - clip_in
            we = float(word.get("end", et)) - clip_in
            if we <= 0 or ws >= duration:
                continue
            words.append({
                **word,
                "start": max(0.0, ws),
                "end": min(duration, we),
            })
        out.append({
            **seg,
            "start": max(0.0, st - clip_in),
            "end": min(duration, et - clip_in),
            "text": (seg.get("text") or "").strip(),
            "words": words,
        })
    return out