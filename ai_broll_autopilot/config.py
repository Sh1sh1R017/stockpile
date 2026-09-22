"""Configuration module for AI B-Roll Autopilot."""

import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Autopilot central configuration."""

    PROJECT_ROOT: Path = PROJECT_ROOT
    INPUT_DIR: Path = PROJECT_ROOT / os.getenv("LOCAL_INPUT_FOLDER", "input")
    OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("LOCAL_OUTPUT_FOLDER", "output")
    DB_PATH: Path = PROJECT_ROOT / "autopilot.db"

    # Sub-projects
    STOCKPILE_DIR: Path = PROJECT_ROOT / "src"
    COLLAGE_DIR: Path = PROJECT_ROOT / "gbro-collage-broll"
    ERDUO_DIR: Path = PROJECT_ROOT / "erduo-broll-loop-engineering"

    # AI & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    GEMINI_FALLBACK_MODELS: List[str] = [
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
    ]
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

    # B-Roll Target Ratio & Duration Constraints
    TARGET_BROLL_RATIO: float = float(os.getenv("TARGET_BROLL_RATIO", "0.60"))  # 60% of total video duration
    MAX_CLIP_DURATION_SECONDS: int = int(os.getenv("MAX_CLIP_DURATION_SECONDS", "4"))
    STOCKPILE_START_OFFSET_SECONDS: float = float(os.getenv("STOCKPILE_START_OFFSET_SECONDS", "6.0"))
    RAPID_FIRE_MONTAGE_ENABLED: bool = True
    TARGET_MICRO_CLIPS_PER_SHOT: int = 4  # 3 to 5 rapid cuts per cutaway
    MIN_MICRO_CLIP_DURATION: float = 0.4
    MAX_MICRO_CLIP_DURATION: float = 0.8
    REJECT_WATERMARKS: bool = True
    WATERMARK_SCAN_ENABLED: bool = True
    WATERMARK_SAMPLE_FRAMES: int = 3
    WATERMARK_GEMINI_ENABLED: bool = True
    WATERMARK_CV_FALLBACK: bool = True
    MAX_WATERMARK_CANDIDATE_RETRIES: int = 4

    # Video Settings
    TARGET_WIDTH: int = 1080
    TARGET_HEIGHT: int = 1920
    TARGET_FPS: int = 30
    VIDEO_CRF: int = 19

    # SDR2HDR & Upscaling Engine
    HDR_ENABLED: bool = False
    HDR_DEFAULT_SCALE: float = 1.0  # 1.0 (Native HDR10), 1.5 (2K QHD), 2.0 (4K UHD)
    HDR_DEFAULT_TONE: str = "vivid"  # "vivid" (punchy viral pop) or "reference" (BT.2408)
    HDR_DEFAULT_STYLE: str = "natural"  # "natural", "cinematic", "night"
    HDR_FAST_MODE: bool = True
    HDR_PROCESSING_SCALE: float = 0.6  # Optimal balance of speed and color fidelity
    HDR_MODEL_PATH: Path = PROJECT_ROOT / "models" / "enhancement_model_reuse_v1.pt"

    # Google Drive
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
    GOOGLE_DRIVE_INPUT_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_INPUT_FOLDER_ID", "")
    GOOGLE_DRIVE_OUTPUT_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")

    # Pexels Video API (Royalty-free & Watermark-free)
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")

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
