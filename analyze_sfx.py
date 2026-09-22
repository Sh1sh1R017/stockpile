import whisper
import json

audio_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"
model = whisper.load_model("base")
result = model.transcribe(audio_path, word_timestamps=True)

with open("scratch_transcription.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)

print("Transcription saved, segments:", len(result["segments"]))
for seg in result["segments"]:
    print(f"{seg['start']:.2f}s - {seg['end']:.2f}s: {seg['text']}")
