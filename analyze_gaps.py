import json
import re

with open("detected_segments.txt") as f:
    lines = [line.strip() for line in f if line.strip()]

segments = []
for line in lines:
    m = re.match(r'\[(\d+)\]\s*([\d\.]+)s\s*-\s*([\d\.]+)s\s*\(dur:\s*([\d\.]+)s\)', line)
    if m:
        idx = int(m.group(1))
        st = float(m.group(2))
        en = float(m.group(3))
        dur = float(m.group(4))
        segments.append({"id": idx, "start": st, "end": en, "duration": dur})

# Calculate gap to next segment
for i in range(len(segments) - 1):
    segments[i]["gap_to_next"] = round(segments[i+1]["start"] - segments[i]["end"], 3)
segments[-1]["gap_to_next"] = 0.0

print(f"Total raw segments: {len(segments)}")

# Let's inspect gaps
small_gaps = [s for s in segments if s["gap_to_next"] < 0.35]
large_gaps = [s for s in segments if s["gap_to_next"] >= 0.35]
print(f"Segments with gap < 0.35s: {len(small_gaps)}")
print(f"Segments with gap >= 0.35s: {len(large_gaps)}")
