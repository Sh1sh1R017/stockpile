"""Configuration module for AI B-Roll Autopilot."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Autopilot central configuration."""
    PROJECT_ROOT: Path = PROJECT_ROOT
    INPUT_DIR: Path = PROJECT_ROOT / os.getenv("LOCAL_INPUT_FOLDER", "input")
    OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("LOCAL_OUTPUT_FOLDER", "output")
    DB_PATH: Path = PROJECT_ROOT / "autopilot.db"

    STOCKPILE_DIR: Path = PROJECT_ROOT / "src"
    COLLAGE_DIR: Path = PROJECT_ROOT / "gbro-collage-broll"
    ERDUO_DIR: Path = PROJECT_ROOT / "erduo-broll-loop-engineering"

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_BROLL_SUPER_MODEL: str = os.getenv("GEMINI_BROLL_SUPER_MODEL", "gemini-2.5-pro")
    GEMINI_BROLL_SUPER_FALLBACK_MODELS: List[str] = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    GEMINI_FALLBACK_MODELS: List[str] = ["gemini-3.6-flash", "gemini-3-flash-preview", "gemini-3.5-flash-lite"]
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

    TARGET_BROLL_RATIO: float = float(os.getenv("TARGET_BROLL_RATIO", "0.60"))
    # Short, punchy B-roll by default. Long holds are opt-in via the edit plan.
    MAX_CLIP_DURATION_SECONDS: float = float(os.getenv("MAX_CLIP_DURATION_SECONDS", "1.8"))
    BROLL_MIN_RENDER_DURATION: float = float(os.getenv("BROLL_MIN_RENDER_DURATION", "0.65"))
    BROLL_MAX_RENDER_DURATION: float = float(os.getenv("BROLL_MAX_RENDER_DURATION", "1.8"))
    BROLL_HERO_MAX_DURATION: float = float(os.getenv("BROLL_HERO_MAX_DURATION", "2.4"))
    BROLL_REPEAT_GAP_SECONDS: float = float(os.getenv("BROLL_REPEAT_GAP_SECONDS", "5.0"))
    STOCKPILE_START_OFFSET_SECONDS: float = float(os.getenv("STOCKPILE_START_OFFSET_SECONDS", "6.0"))
    BROLL_SPEED_MULTIPLIER: float = float(os.getenv("BROLL_SPEED_MULTIPLIER", "1.25"))
    STREAMER_SPEED_MULTIPLIER: float = float(os.getenv("STREAMER_SPEED_MULTIPLIER", "1.30"))
    RAPID_FIRE_MONTAGE_ENABLED: bool = True
    TARGET_MICRO_CLIPS_PER_SHOT: int = 4
    MIN_MICRO_CLIP_DURATION: float = 0.4
    MAX_MICRO_CLIP_DURATION: float = 0.8
    REJECT_WATERMARKS: bool = True
    WATERMARK_SCAN_ENABLED: bool = True
    WATERMARK_SAMPLE_FRAMES: int = 3
    WATERMARK_GEMINI_ENABLED: bool = True
    WATERMARK_CV_FALLBACK: bool = True
    MAX_WATERMARK_CANDIDATE_RETRIES: int = 4

    TARGET_WIDTH: int = 1080
    TARGET_HEIGHT: int = 1920
    TARGET_FPS: int = 30
    VIDEO_CRF: int = 19
    FONT_PATH: str = os.getenv("STOCKPILE_FONT_PATH", "")

    FAST_RENDER_ENABLED: bool = os.getenv("STOCKPILE_FAST_RENDER", "1").strip().lower() not in {"0", "false", "off"}
    FAST_RENDER_WIDTH: int = int(os.getenv("STOCKPILE_FAST_RENDER_WIDTH", "720"))
    FAST_RENDER_HEIGHT: int = int(os.getenv("STOCKPILE_FAST_RENDER_HEIGHT", "1280"))

    NVENC_MODE: str = os.getenv("STOCKPILE_NVENC", "auto").strip().lower()
    NVENC_PRESET: str = os.getenv("STOCKPILE_NVENC_PRESET", "p4")
    NVENC_CQ: int = int(os.getenv("STOCKPILE_NVENC_CQ", str(VIDEO_CRF)))
    FAST_RENDER_VALIDATION: bool = os.getenv("STOCKPILE_FAST_VALIDATION", "1").strip().lower() not in {"0", "false", "off"}

    EDITOR_ENGINE: str = os.getenv("EDITOR_ENGINE", "openreel")
    HDR_ENABLED: bool = False
    HDR_DEFAULT_SCALE: float = 1.0
    HDR_DEFAULT_TONE: str = "vivid"
    HDR_DEFAULT_STYLE: str = "natural"
    HDR_FAST_MODE: bool = True
    HDR_PROCESSING_SCALE: float = 0.6
    HDR_MODEL_PATH: Path = PROJECT_ROOT / "models" / "enhancement_model_reuse_v1.pt"

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
    GOOGLE_DRIVE_INPUT_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "")
    GOOGLE_DRIVE_OUTPUT_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
    OPENSHORTS_API_URL: str = os.getenv("OPENSHORTS_API_URL", "")
    OPENSHORTS_API_KEY: str = os.getenv("OPENSHORTS_API_KEY", "")
    MOTION_ANYTHING_DIR: Path = Path(os.getenv("MOTION_ANYTHING_DIR", str(PROJECT_ROOT / "motion-anything")))

    @classmethod
    def ensure_directories(cls):
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> List[str]:
        errors = []
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not configured in .env")
        return errors
