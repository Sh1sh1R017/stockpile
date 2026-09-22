import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

audio_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

with open("detected_segments.txt") as f:
    detected_text = f.read()

# Also read whisper transcription
with open("scratch_transcription.json", encoding="utf-8") as f:
    whisper_data = json.load(f)

whisper_summary = "\n".join([f"{s['start']:.2f}s - {s['end']:.2f}s: {s['text']}" for s in whisper_data["segments"]])

# We already uploaded the file earlier or can reuse/upload
print("Uploading audio file...")
audio_file = client.files.upload(file=audio_path)

prompt = f"""
You are an expert sound designer, meme historian, and audio engineer.
You are given an audio file which is a classic compilation of famous meme sound effects and SFX used by video editors (like YouTuber SFX packs).

Here is the Whisper transcription of spoken parts in the compilation:
{whisper_summary}

Here are the silence-detected audio segments (start - end):
{detected_text}

TASK:
1. Go through the audio carefully from 0:00 to 3:53.76.
2. For each distinct sound effect or meme audio:
   - Determine its exact start time and end time (align with the silence boundaries).
   - If two adjacent silence-detected slices are actually ONE single continuous meme/SFX (e.g., "FBI open up" + door kick/gunshots, or "Ayo the pizza here" + falling down stairs + "my ears burn", or a sentence with a brief breath pause), group them into ONE single SFX file.
   - If they are distinct sound effects (e.g. "Bonk", then "What", then "Pencil writing", then "Camera click", then "Mouse click", then "Nope", then "Scream", then "Spring Boing", then "Yay Children Cheering", etc.), keep them as separate individual SFX files!
3. Give each sound effect:
   - A clean, standard, recognizable name/label (e.g., "001_bonk.mp3", "002_what_meme.mp3", "003_pencil_writing.mp3", "004_camera_shutter.mp3", "005_mouse_click.mp3", "006_nope_engineer.mp3", "007_loud_screaming.mp3", "008_cartoon_spring_boing.mp3", "009_yay_children_cheer.mp3", "010_cash_register_kaching.mp3", "011_bruh.mp3", "012_are_you_serious_my_brother.mp3", "013_angelic_choir_halo.mp3", "014_slap_punch_impact.mp3", "015_ay_yo_what_the_fuck.mp3", "016_baba_booey.mp3", "017_baby_crying.mp3", etc.)
   - Category (e.g. "Meme Voice", "Foley / Real Life", "Cartoon SFX", "Impact", "Gaming / Alert", "Reaction")
   - Spoken words / Sound description (e.g. "Wood bonk impact", "Man saying 'What?' with echo", etc.)

Return ONLY a valid JSON list of objects:
[
  {{
    "id": 1,
    "start_time": 0.45,
    "end_time": 0.85,
    "filename": "001_bonk_impact.mp3",
    "name": "Bonk Impact",
    "category": "Cartoon SFX",
    "description": "Classic cartoon hollow wood bonk sound effect"
  }},
  ...
]
"""

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=[audio_file, prompt],
    config=types.GenerateContentConfig(
        response_mime_type="application/json"
    )
)

with open("master_sfx_split_plan.json", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Saved master_sfx_split_plan.json")
