import json
import re

# Load detected silence segments
with open("detected_segments.txt") as f:
    lines = [line.strip() for line in f if line.strip()]

silence_segs = []
for line in lines:
    m = re.match(r'\[(\d+)\]\s*([\d\.]+)s\s*-\s*([\d\.]+)s\s*\(dur:\s*([\d\.]+)s\)', line)
    if m:
        silence_segs.append((float(m.group(2)), float(m.group(3))))

with open("all_raw_sfx.json", encoding="utf-8") as f:
    raw_sfx = json.load(f)

print(f"Total silence segments: {len(silence_segs)}")
print(f"Total raw sfx from Gemini: {len(raw_sfx)}")

# For each Gemini sfx, find overlapping silence segments
aligned_clips = []
used_silence_indices = set()

for sfx_idx, sfx in enumerate(raw_sfx):
    st = sfx["global_start"]
    en = sfx["global_end"]
    title = sfx.get("title", f"SFX_{sfx_idx+1}")
    cat = sfx.get("category", "SFX")
    desc = sfx.get("description", "")
    
    # Find matching silence segment(s) that overlap with [st - 0.5, en + 0.5]
    matching_segs = []
    for i, (seg_st, seg_en) in enumerate(silence_segs):
        # check overlap
        if max(st - 0.4, seg_st) < min(en + 0.4, seg_en):
            matching_segs.append((i, seg_st, seg_en))
    
    if matching_segs:
        cut_st = min(s[1] for s in matching_segs)
        cut_en = max(s[2] for s in matching_segs)
        for s in matching_segs:
            used_silence_indices.add(s[0])
    else:
        # fallback to gemini timestamps
        cut_st = st
        cut_en = en
    
    # Add a tiny 0.03s margin for audio attack/decay
    cut_st = max(0.0, cut_st - 0.02)
    cut_en = min(233.76, cut_en + 0.05)
    
    aligned_clips.append({
        "raw_index": sfx_idx + 1,
        "title": title,
        "category": cat,
        "description": desc,
        "start": round(cut_st, 2),
        "end": round(cut_en, 2),
        "duration": round(cut_en - cut_st, 2)
    })

print(f"Aligned clips: {len(aligned_clips)}")
print(f"Used {len(used_silence_indices)} of {len(silence_segs)} silence segments")

# Check which silence segments were NOT matched (might be missed sounds!)
unmatched = [i for i in range(len(silence_segs)) if i not in used_silence_indices]
print(f"Unmatched silence segments: {len(unmatched)}")
for i in unmatched:
    print(f"  Unmatched seg [{i+1}]: {silence_segs[i][0]}s - {silence_segs[i][1]}s (dur: {silence_segs[i][1]-silence_segs[i][0]:.2f}s)")
