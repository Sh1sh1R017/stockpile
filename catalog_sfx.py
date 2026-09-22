import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

audio_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

print("Uploading audio to Gemini API...")
audio_file = client.files.upload(file=audio_path)
print(f"Uploaded: {audio_file.name}, state: {audio_file.state}")

prompt = """
You are a master audio engineer and meme sound effects expert.
This audio file is a popular SFX soundboard / meme compilation for video editors.
Please listen carefully from 00:00.00 to the end (around 03:53.76).
List EVERY single distinct sound effect / meme audio in chronological order.
For each sound effect, provide:
1. index (1, 2, 3...)
2. start_time (seconds or mm:ss)
3. end_time (seconds or mm:ss)
4. label / title (standard meme/SFX name, e.g. "Bruh", "Vine Boom", "Metal Pipe Falling", "Wilhelm Scream", "Windows XP Error", "Sad Violin", "Airhorn", etc.)
5. description / category (e.g. "Voice meme", "Cartoon SFX", "Impact", "Transition")

Output as a valid JSON list of objects:
[
  {
    "index": 1,
    "start_time": "00:00.45",
    "end_time": "00:00.80",
    "title": "Bonk / Whack",
    "filename": "001_bonk.mp3",
    "category": "Impact"
  },
  ...
]
"""

for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.1-flash-lite"]:
    try:
        print(f"Trying model: {model}...")
        response = client.models.generate_content(
            model=model,
            contents=[audio_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        print("Success!")
        with open("gemini_sfx_catalog.json", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Catalog saved to gemini_sfx_catalog.json")
        break
    except Exception as e:
        print(f"Failed with {model}: {e}")
