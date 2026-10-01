"""Shared transcript time-base normalization for clip-scoped editorial processing."""

def scope_segments(segments, clip_in, clip_out):
    duration = max(1.0, float(clip_out) - float(clip_in))
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
                "start": round(max(0.0, ws), 3),
                "end": round(min(duration, we), 3),
            })
        out.append({
            **seg,
            "start": max(0.0, round(st - clip_in, 3)),
            "end": min(duration, round(et - clip_in, 3)),
            "text": (seg.get("text") or "").strip(),
            "words": words,
        })
    return out
