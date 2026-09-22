import os
import subprocess
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

input_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

windows = [
    (0, 30),
    (30, 60),
    (60, 90),
    (90, 120),
    (120, 150),
    (150, 180),
    (180, 210),
    (210, 234)
]

all_effects = []

prompt_template = """
Listen to this {dur}s audio clip which contains multiple consecutive famous meme sound effects and SFX.
List EVERY SINGLE sound effect in order. Do NOT skip any sound effects (including farts, impacts, clicks, booms, voices, music riffs, etc.).
Include:
- start_time (seconds as a float relative to the start of this clip)
- end_time (seconds as a float relative to the start of this clip)
- title (exact popular meme / SFX title, e.g. "Bruh", "Vine Boom", "Metal Pipe", "Airhorn", "Sad Trombone", etc.)
- category (Voice, Impact, Cartoon, Foley, Gaming, etc.)
- description

Output ONLY a JSON array of objects.
"""

for idx, (w_start, w_end) in enumerate(windows):
    dur = w_end - w_start
    w_file = f"chunk_{w_start}_{w_end}.mp3"
    print(f"\nProcessing window {idx+1}/{len(windows)}: {w_start}s to {w_end}s...")
    subprocess.run(['ffmpeg', '-y', '-ss', str(w_start), '-t', str(dur), '-i', input_path, w_file], capture_output=True, check=True)
    
    upload = client.files.upload(file=w_file)
    p = prompt_template.format(dur=dur)
    
    resp = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[upload, p],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    try:
        items = json.loads(resp.text)
        print(f"Window {w_start}-{w_end}s found {len(items)} sound effects:")
        for item in items:
            g_start = round(w_start + float(item["start_time"]), 2)
            g_end = round(w_start + float(item["end_time"]), 2)
            item["global_start"] = g_start
            item["global_end"] = g_end
            print(f"  - [{g_start:06.2f}s - {g_end:06.2f}s] {item.get('title')}")
            all_effects.append(item)
    except Exception as e:
        print(f"Error parsing json for window {w_start}-{w_end}: {e}")
        print("Raw text:", resp.text[:200])

with open("all_raw_sfx.json", "w", encoding="utf-8") as f:
    json.dump(all_effects, f, indent=2)

print(f"\nTotal collected sound effects: {len(all_effects)}")
