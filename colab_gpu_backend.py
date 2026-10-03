# Google Colab Backend Runner — AI B-Roll Autopilot Studio
# Run this script cell-by-cell in a Colab notebook, or paste the whole thing
# into a single cell. Requires T4/A100 GPU runtime.

import os, sys, subprocess, threading, time, urllib.request

REPO_URL   = "https://github.com/Sh1sh1R017/stockpile.git"
BRANCH     = "sorry-i-fucked-up"
CLONE_DIR  = "/content/stockpile"
PORT       = 8000

# ── 1. GPU check ─────────────────────────────────────────────────────────────
print("🔍 Step 1: Checking GPU...")
os.system("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo '⚠️  No GPU — switch to T4 GPU runtime!'")

# ── 2. Clone / update repo ────────────────────────────────────────────────────
print(f"\n📦 Step 2: Setting up repo ({BRANCH})...")
if os.path.isdir(os.path.join(CLONE_DIR, ".git")):
    print("   Repo already exists — pulling latest changes...")
    os.system(f"git -C {CLONE_DIR} fetch -q origin {BRANCH}")
    os.system(f"git -C {CLONE_DIR} reset -q --hard origin/{BRANCH}")
else:
    os.system(f"rm -rf {CLONE_DIR}")
    os.system(f"git clone -q -b {BRANCH} {REPO_URL} {CLONE_DIR}")
os.chdir(CLONE_DIR)
print(f"   ✅ Working in {os.getcwd()}")

# ── 3. System deps ────────────────────────────────────────────────────────────
print("\n🔧 Step 3: Installing ffmpeg...")
os.system("apt-get update -qq && apt-get install -y -qq ffmpeg")

# ── 4. Python deps ────────────────────────────────────────────────────────────
print("\n📦 Step 4: Installing Python packages (this takes ~2 min on first run)...")
os.system(f"{sys.executable} -m pip install -q -r requirements.txt")
os.system(f"{sys.executable} -m pip install -q pycloudflared uvicorn[standard] python-multipart nest-asyncio")
print("   ✅ Packages installed.")

# ── 5. API Keys ───────────────────────────────────────────────────────────────
print("\n🔑 Step 5: Configuring API keys...")

def _get_secret(name):
    """Try Colab Secrets first, then environment variable."""
    try:
        from google.colab import userdata
        val = userdata.get(name)
        if val:
            return val.strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()

# Whisper settings — change these if needed
WHISPER_MODEL        = os.environ.get("WHISPER_MODEL", "medium")        # small / medium / large-v3
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "float32") # float32 = safe on T4; float16 = faster on A100

gemini_key = _get_secret("GEMINI_API_KEY")
pexels_key = _get_secret("PEXELS_API_KEY")
giphy_key  = _get_secret("GIPHY_API_KEY")

# Fall back to interactive prompt ONLY if not found in Secrets / env
if not gemini_key:
    gemini_key = input("   Enter GEMINI_API_KEY (or leave blank): ").strip()
if not pexels_key:
    pexels_key = input("   Enter PEXELS_API_KEY (optional, blank to skip): ").strip()
if not giphy_key:
    giphy_key  = input("   Enter GIPHY_API_KEY  (optional, blank to skip): ").strip()

env_lines = [
    f"LOCAL_INPUT_FOLDER=input",
    f"LOCAL_OUTPUT_FOLDER=output",
    f"WHISPER_MODEL={WHISPER_MODEL}",
    f"WHISPER_COMPUTE_TYPE={WHISPER_COMPUTE_TYPE}",
]
if gemini_key: env_lines.append(f"GEMINI_API_KEY={gemini_key}")
if pexels_key: env_lines.append(f"PEXELS_API_KEY={pexels_key}")
if giphy_key:  env_lines.append(f"GIPHY_API_KEY={giphy_key}")

with open(f"{CLONE_DIR}/.env", "w") as f:
    f.write("\n".join(env_lines) + "\n")

print(f"   GEMINI  : {'✅ set' if gemini_key else '❌ missing'}")
print(f"   PEXELS  : {'✅ set' if pexels_key else '⚠️  not set'}")
print(f"   GIPHY   : {'✅ set' if giphy_key  else '⚠️  not set'}")
print(f"   Whisper : {WHISPER_MODEL} ({WHISPER_COMPUTE_TYPE})")

# ── 6. Start FastAPI ──────────────────────────────────────────────────────────
print(f"\n🚀 Step 6: Starting FastAPI backend on port {PORT}...")

log_file = open("/tmp/backend.log", "w")
server_proc = subprocess.Popen(
    [sys.executable, "-m", "ai_broll_autopilot.cli", "serve",
     "--host", "0.0.0.0", "--port", str(PORT)],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    cwd=CLONE_DIR,
)

# Wait until /health responds (up to 60s)
print("   Waiting for backend", end="", flush=True)
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2)
        print(" ✅", flush=True)
        break
    except urllib.error.HTTPError:
        # Any HTTP response means the server is up (even 4xx)
        print(" ✅", flush=True)
        break
    except Exception:
        print(".", end="", flush=True)
        time.sleep(2)
else:
    print("\n❌ Backend didn't start — last 30 lines of log:")
    with open("/tmp/backend.log") as lf:
        lines = lf.readlines()
        print("".join(lines[-30:]))
    raise RuntimeError("Backend failed to start. Check /tmp/backend.log")

# ── 7. Cloudflare Tunnel ──────────────────────────────────────────────────────
print("\n🌐 Step 7: Opening Cloudflare tunnel...")
from pycloudflared import try_cloudflare
tunnel = try_cloudflare(port=PORT)
# tunnel.tunnel is the public HTTPS URL string
PUBLIC_URL = tunnel.tunnel

print("\n" + "═" * 65)
print("🚀  AI B-ROLL AUTOPILOT — GPU BACKEND LIVE!")
print("═" * 65)
print(f"  🔗 Public URL  : {PUBLIC_URL}")
print(f"  🤖 Whisper     : {WHISPER_MODEL} ({WHISPER_COMPUTE_TYPE})")
print("═" * 65)
print("")
print("📋 TO CONNECT YOUR WEB STUDIO:")
print("  Option A — PowerShell before npm run dev:")
print(f'    $env:BACKEND_API_URL="{PUBLIC_URL}"; npm run dev')
print("")
print("  Option B — write to web/.env.local:")
print(f"    BACKEND_API_URL={PUBLIC_URL}")
print("")
print("⚠️  URL changes every restart.")
print("═" * 65)

# Keep alive with heartbeat
print("\n🟢 Backend running. Ctrl+C or ■ Stop to shut down.\n")
heartbeat = 0
while True:
    time.sleep(60)
    heartbeat += 1
    print(f"  💓 [{heartbeat}m] Alive — {PUBLIC_URL}", flush=True)
