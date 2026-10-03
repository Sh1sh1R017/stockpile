# Google Colab Backend Runner for AI B-Roll Autopilot Studio
# Runs on free T4 / A100 GPU with Cloudflare Tunnel (or ngrok)

import os
import subprocess
import sys

print("🚀 Step 1: Checking GPU...")
!nvidia-smi

print("\n📦 Step 2: Cloning stockpile repository...")
!git clone -b sorry-i-fucked-up https://github.com/Sh1sh1R017/stockpile.git /content/stockpile
%cd /content/stockpile

print("\n📦 Step 3: Installing system dependencies (ffmpeg)...")
!apt-get update -qq && apt-get install -y ffmpeg -qq

print("\n📦 Step 4: Installing python dependencies...")
!pip install -q -r requirements.txt
!pip install -q pycloudflared uvicorn[standard] python-multipart

# Prompt for API Keys (Optional if you already set them in .env)
import getpass
gemini_key = os.environ.get("GEMINI_API_KEY") or input("Enter GEMINI_API_KEY (leave blank if not needed): ").strip()
pexels_key = os.environ.get("PEXELS_API_KEY") or input("Enter PEXELS_API_KEY (leave blank if not needed): ").strip()
giphy_key = os.environ.get("GIPHY_API_KEY") or input("Enter GIPHY_API_KEY (leave blank if not needed): ").strip()

with open("/content/stockpile/.env", "w") as f:
    if gemini_key:
        f.write(f"GEMINI_API_KEY={gemini_key}\n")
    if pexels_key:
        f.write(f"PEXELS_API_KEY={pexels_key}\n")
    if giphy_key:
        f.write(f"GIPHY_API_KEY={giphy_key}\n")
    f.write("LOCAL_INPUT_FOLDER=input\nLOCAL_OUTPUT_FOLDER=output\nWHISPER_MODEL=small\n")

print("\n🌐 Step 5: Launching FastAPI Backend on GPU...")
import threading
import time

def run_backend():
    os.system("python -m ai_broll_autopilot.cli serve --host 0.0.0.0 --port 8000")

t = threading.Thread(target=run_backend, daemon=True)
t.start()
time.sleep(3)

print("\n🚇 Step 6: Exposing via Cloudflare Tunnel...")
# Using pycloudflared to give you a public https:// URL instantly
from pycloudflared import try_cloudflare
tunnel = try_cloudflare(port=8000)
print("\n" + "="*70)
print(f"🎉 YOUR COLLAB GPU BACKEND IS LIVE AT:")
print(f"👉 {tunnel.tunnel.url}")
print("="*70)
print("\n📋 Next step:")
print("1. Copy the URL above.")
print("2. In your local web studio, paste it in 'web/.env.local' or run:")
print(f"   BACKEND_API_URL={tunnel.tunnel.url} npm run dev")
print("="*70 + "\n")

# Keep cell alive
while True:
    time.sleep(60)
