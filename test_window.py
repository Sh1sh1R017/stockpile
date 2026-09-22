import os
import subprocess
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

input_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

# Cut window 0 to 30
subprocess.run(['ffmpeg', '-y', '-ss', '0', '-t', '30', '-i', input_path, 'window_0_30.mp3'], check=True)

audio_file = client.files.upload(file="window_0_30.mp3")

prompt = """
Listen to this 30-second audio clip which contains multiple consecutive meme sound effects and SFX.
List EVERY SINGLE sound effect in order. Do NOT skip any sound effects.
Include:
- start_time (seconds within this 30s window)
- end_time (seconds within this 30s window)
- title (popular meme or SFX name)
- category (Voice, Impact, Cartoon, Foley, etc.)
- description

Output as JSON array:
[
  {
    "start_time": 0.45,
    "end_time": 0.85,
    "title": "Bonk",
    "category": "Impact",
    "description": "Cartoon wooden bonk"
  }
]
"""

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=[audio_file, prompt],
    config=types.GenerateContentConfig(response_mime_type="application/json")
)

print(response.text)
