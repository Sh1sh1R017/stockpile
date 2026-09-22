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

# Merge segments if silence gap is less than 0.35s
merged = []
cur_st, cur_en = raw_segments[0]
for st, en in raw_segments[1:]:
    gap = st - cur_en
    if gap < 0.35:
        cur_en = en
    else:
        merged.append((round(cur_st, 2), round(cur_en, 2)))
        cur_st, cur_en = st, en
merged.append((round(cur_st, 2), round(cur_en, 2)))

print(f"Total merged SFX clips: {len(merged)}")

with open("scratch_transcription.json", encoding="utf-8") as f:
    whisper_data = json.load(f)

# Associate whisper text
sfx_list = []
for idx, (st, en) in enumerate(merged):
    # find whisper text
    texts = []
    for w in whisper_data["segments"]:
        if max(st - 0.2, w["start"]) < min(en + 0.2, w["end"]):
            texts.append(w["text"].strip())
    spoken = " ".join(texts) if texts else ""
    sfx_list.append({
        "index": idx + 1,
        "start": st,
        "end": en,
        "duration": round(en - st, 2),
        "whisper_text": spoken
    })

with open("sfx_87_candidates.json", "w", encoding="utf-8") as f:
    json.dump(sfx_list, f, indent=2)

print("Saved sfx_87_candidates.json")
for item in sfx_list[:25]:
    txt = f" (Text: '{item['whisper_text']}')" if item['whisper_text'] else ""
    print(f"[{item['index']:02d}] {item['start']:06.2f}s - {item['end']:06.2f}s ({item['duration']:04.2f}s){txt}")
