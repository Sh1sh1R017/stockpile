import subprocess
import os
import re

input_path = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"

# Let's get silences with fine threshold
cmd = ['ffmpeg', '-i', input_path, '-af', 'silencedetect=noise=-32dB:d=0.18', '-f', 'null', '-']
res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

silences = []
cur_start = None
for line in res.stderr.splitlines():
    m_s = re.search(r'silence_start:\s*([\d\.]+)', line)
    if m_s:
        cur_start = float(m_s.group(1))
    m_e = re.search(r'silence_end:\s*([\d\.]+)', line)
    if m_e and cur_start is not None:
        silences.append((cur_start, float(m_e.group(1))))
        cur_start = None

# Audio segments
audio_segments = []
t = 0.0
for s_start, s_end in silences:
    if s_start > t + 0.08:
        audio_segments.append((t, s_start))
    t = s_end

# Add last segment up to total duration 233.76
if t < 233.76 - 0.08:
    audio_segments.append((t, 233.76))

print(f"Total audio segments detected: {len(audio_segments)}")
with open("detected_segments.txt", "w") as f:
    for i, (st, en) in enumerate(audio_segments):
        f.write(f"[{i+1:03d}] {st:06.2f}s - {en:06.2f}s (dur: {en-st:05.2f}s)\n")

print("Saved detected_segments.txt")
