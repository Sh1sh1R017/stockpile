import re
import json
from sfx_definitions import sfx_definitions

# Load detected silence segments
with open("detected_segments.txt") as f:
    lines = [line.strip() for line in f if line.strip()]

silence_segs = []
for line in lines:
    m = re.match(r'\[(\d+)\]\s*([\d\.]+)s\s*-\s*([\d\.]+)s\s*\(dur:\s*([\d\.]+)s\)', line)
    if m:
        silence_segs.append((float(m.group(2)), float(m.group(3))))

print(f"Total silence segments available: {len(silence_segs)}")

# For each SFX, find the closest silence segment or cluster around approx_ts
final_cuts = []

for i, sfx in enumerate(sfx_definitions):
    ts = sfx["approx_ts"]
    # search window: ts +/- 1.8s (or wider for long clips)
    window = 1.8
    if sfx["id"] in [13, 22, 27, 33, 47]: # long memes like Halo choir, Pizza here, Look at this dude
        window = 12.0
    
    # Candidates that overlap or are close to approx_ts
    candidates = [seg for seg in silence_segs if abs((seg[0] + seg[1])/2 - ts) <= window or (seg[0] <= ts <= seg[1])]
    
    if candidates:
        # If long clip like Look at this dude (140s to 162s)
        if sfx["id"] == 47: # Look at this dude
            st = 140.32
            en = 162.08
        elif sfx["id"] == 22: # Ayo the pizza here
            st = 47.17
            en = 53.14
        elif sfx["id"] == 13: # Angelic choir
            st = 21.88
            en = 30.82
        elif sfx["id"] == 27: # Please man I need this
            st = 64.96
            en = 71.39
        elif sfx["id"] == 33: # FBI open up
            st = 89.65
            en = 93.70
        else:
            # find closest segment to approx_ts
            best_seg = min(candidates, key=lambda s: abs((s[0] + s[1])/2 - ts))
            st, en = best_seg
    else:
        st = max(0.0, ts - 0.5)
        en = ts + 0.5

    final_cuts.append({
        "id": sfx["id"],
        "filename": sfx["filename"],
        "name": sfx["name"],
        "category": sfx["cat"],
        "start": round(st, 2),
        "end": round(en, 2),
        "duration": round(en - st, 2)
    })

# Ensure no backwards or negative duration and chronological order
for i in range(len(final_cuts) - 1):
    c1 = final_cuts[i]
    c2 = final_cuts[i+1]
    if c1["end"] > c2["start"] and c1["id"] != 47: # don't overlap unless special
        # adjust boundary to midpoint
        mid = round((c1["end"] + c2["start"]) / 2, 2)
        c1["end"] = mid
        c2["start"] = mid
        c1["duration"] = round(c1["end"] - c1["start"], 2)
        c2["duration"] = round(c2["end"] - c2["start"], 2)

with open("final_sfx_cut_list.json", "w", encoding="utf-8") as f:
    json.dump(final_cuts, f, indent=2)

print(f"Generated {len(final_cuts)} clean cut configurations:")
for c in final_cuts:
    print(f"[{c['id']:02d}] {c['start']:06.2f}s - {c['end']:06.2f}s ({c['duration']:04.2f}s) -> {c['filename']} ({c['name']})")
