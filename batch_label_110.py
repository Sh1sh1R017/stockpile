import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

audio_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

with open("all_110_segments.json") as f:
    segments = json.load(f)

# Upload the full audio file
print("Uploading audio to Gemini...")
uploaded_audio = client.files.upload(file=audio_path)
print("Uploaded successfully:", uploaded_audio.name)

def label_batch(batch_segs, batch_name):
    seg_prompt = "\n".join([
        f"Segment {s['index']}: start={s['start']}s, end={s['end']}s, dur={s['duration']}s"
        for s in batch_segs
    ])
    
    prompt = f"""
You are an expert audio archivist and video editor.
You have the audio file of '100+ Meme Sound Effects (2026)'.
Below are {len(batch_segs)} exact silence-detected audio segments from this audio track:

{seg_prompt}

TASK:
Listen to the audio track at each segment's timestamp interval.
Identify the exact sound effect, meme line, cartoon sound, or foley playing in that segment.
Provide a clean, accurate label and filename for EACH of the {len(batch_segs)} segments.

Rules:
- DO NOT SKIP any segments. Return an entry for EVERY segment in this batch ({batch_segs[0]['index']} to {batch_segs[-1]['index']}).
- Filename format: `XXX_descriptive_name.mp3` (e.g. `001_bonk.mp3`, `008_bruh.mp3`, `065_vine_boom.mp3`).
- If a segment is part of a longer meme line (e.g. part of "Ayo the pizza here" or "Laughing wheeze"), label the specific part clearly (e.g. "Ayo the pizza here (Part 1 - Shout)", "Look at this dude (Wheeze)").

Return ONLY a valid JSON array of objects:
[
  {{
    "index": {batch_segs[0]['index']},
    "start": {batch_segs[0]['start']},
    "end": {batch_segs[0]['end']},
    "duration": {batch_segs[0]['duration']},
    "title": "Bonk Impact",
    "filename": "{batch_segs[0]['index']:03d}_bonk_impact.mp3",
    "category": "Cartoon SFX",
    "description": "Wood bonk impact"
  }},
  ...
]
"""
    print(f"Querying Gemini for {batch_name} ({len(batch_segs)} segments)...")
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[uploaded_audio, prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(resp.text)

# Batch 1: 1 to 55
batch1_segs = segments[:55]
results_b1 = label_batch(batch1_segs, "Batch 1 (segs 1 to 55)")
print(f"Batch 1 returned {len(results_b1)} labelled items")

# Batch 2: 56 to 110
batch2_segs = segments[55:]
results_b2 = label_batch(batch2_segs, "Batch 2 (segs 56 to 110)")
print(f"Batch 2 returned {len(results_b2)} labelled items")

all_labelled = results_b1 + results_b2
print(f"Total labelled sound effects: {len(all_labelled)}")

with open("final_110_sfx_catalog.json", "w", encoding="utf-8") as f:
    json.dump(all_labelled, f, indent=2)

print("Saved final_110_sfx_catalog.json!")
