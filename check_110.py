import re
import json

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
        segments.append({
            "index": idx,
            "start": st,
            "end": en,
            "duration": dur
        })

print(f"Total detected segments: {len(segments)}")

# Filter out any tiny noise clicks < 0.08s
real_segments = [s for s in segments if s["duration"] >= 0.08]
print(f"Segments >= 0.08s: {len(real_segments)}")

with open("all_110_segments.json", "w") as f:
    json.dump(real_segments, f, indent=2)
