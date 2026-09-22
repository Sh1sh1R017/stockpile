import json
import re

with open("detected_segments.txt") as f:
    lines = [line.strip() for line in f if line.strip()]

raw_segments = []
for line in lines:
    m = re.match(r'\[(\d+)\]\s*([\d\.]+)s\s*-\s*([\d\.]+)s\s*\(dur:\s*([\d\.]+)s\)', line)
    if m:
        st = float(m.group(2))
        en = float(m.group(3))
        raw_segments.append((st, en))

# Merge segments if silence gap is less than threshold
def merge_segments(threshold=0.35):
    merged = []
    if not raw_segments:
        return merged
    cur_st, cur_en = raw_segments[0]
    for st, en in raw_segments[1:]:
        gap = st - cur_en
        if gap < threshold:
            cur_en = en
        else:
            merged.append((cur_st, cur_en))
            cur_st, cur_en = st, en
    merged.append((cur_st, cur_en))
    return merged

for thresh in [0.25, 0.30, 0.35, 0.40, 0.45]:
    m = merge_segments(thresh)
    print(f"Threshold {thresh:.2f}s -> {len(m)} sound effects")

merged_035 = merge_segments(0.35)
print("\n--- First 30 merged segments with 0.35s threshold ---")
for i, (st, en) in enumerate(merged_035[:30]):
    print(f"[{i+1:02d}] {st:06.2f}s - {en:06.2f}s (dur: {en-st:05.2f}s)")
