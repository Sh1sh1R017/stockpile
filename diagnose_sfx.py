import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

frame_path = Path("output/workspace/test_sfx_transitions/sfx_frame_shot_4.jpg")
print("Frame exists:", frame_path.exists())

with open("output/split_sfx/sfx_catalog.json") as f:
    catalog = json.load(f)

# Compact summary of sounds
catalog_summary = "\n".join([
    f"- ID {s['id']}: {s['name']} ({s['file']}) | Category: {s['cat']} | Desc: {s['desc']}"
    for s in catalog
])

prompt = f"""
You are an expert sound designer for viral short-form videos.
Analyze this video keyframe from a B-roll cutaway shot.

Shot Context:
- Visual Search Topic: businessman checking clipboard
- Spoken Dialogue: "If you come to my office, that's my thing that I have on my clipboard right here in front of me."
- Scene Theme: Discipline / Office

TASK:
Select the most fitting sound effect from the following library to place during this visual cutaway.
(e.g., pen writing, paper snap, mouse click, camera shutter, cash register, subtle chime, etc.)

Library of Available Sound Effects:
{catalog_summary}

Respond ONLY with a JSON object:
{{
  "selected_id": 3,
  "file": "03_pencil_writing.mp3",
  "name": "Pencil Writing",
  "reason": "Businessman checking clipboard and writing notes",
  "volume": 0.40,
  "start_offset": 0.3
}}
"""

uploaded_frame = client.files.upload(file=str(frame_path))
resp = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=[uploaded_frame, prompt],
    config=types.GenerateContentConfig(response_mime_type="application/json")
)
print("Response:", resp.text)
