"""Background Music (BGM) Engine with speech ducking.

Manages curated royalty-free soundtrack catalog and generates FFmpeg audio filtergraphs
with automatic voice ducking under dialogue tracks.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class BGMEngine:
    """Manages background music tracks and audio ducking."""

    DEFAULT_TRACKS = [
        {
            "id": "chill_lofi",
            "name": "Chill Lo-Fi Beat",
            "filename": "chill_lofi_beat.mp3",
            "genre": "Lo-Fi / Relaxed",
            "default_volume": 0.16,
            "description": "Smooth, relaxed beats perfect for storytelling and education."
        },
        {
            "id": "upbeat_phonk",
            "name": "Upbeat Phonk & Energy",
            "filename": "upbeat_phonk_groove.mp3",
            "genre": "Phonk / Energy",
            "default_volume": 0.14,
            "description": "Driving rhythm and hype bass for fast-paced viral shorts."
        },
        {
            "id": "cinematic_motivation",
            "name": "Cinematic Motivation",
            "filename": "cinematic_motivation.mp3",
            "genre": "Inspirational / Corporate",
            "default_volume": 0.15,
            "description": "Inspiring pads and building emotion for business & advice clips."
        }
    ]

    def __init__(self, bgm_dir: Optional[Path] = None):
        self.bgm_dir = bgm_dir or (Config.PROJECT_ROOT / "media" / "bgm")
        self.bgm_dir.mkdir(parents=True, exist_ok=True)

    def list_tracks(self) -> List[Dict[str, Any]]:
        """Return catalog of available BGM tracks with preview URLs."""
        tracks = []
        for item in self.DEFAULT_TRACKS:
            p = self.bgm_dir / item["filename"]
            exists = p.exists()
            tracks.append({
                "id": item["id"],
                "name": item["name"],
                "filename": item["filename"],
                "genre": item["genre"],
                "default_volume": item["default_volume"],
                "description": item["description"],
                "available": exists,
                "preview_url": f"/api/bgm/{item['id']}/audio" if exists else None,
            })

        # Also discover any custom uploaded mp3/wav files in media/bgm
        for f in self.bgm_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".aac", ".m4a"):
                if not any(t["filename"] == f.name for t in self.DEFAULT_TRACKS):
                    clean_id = f.stem.lower().replace(" ", "_")
                    tracks.append({
                        "id": clean_id,
                        "name": f.stem.replace("_", " ").title(),
                        "filename": f.name,
                        "genre": "Custom",
                        "default_volume": 0.15,
                        "description": "Custom uploaded background track",
                        "available": True,
                        "preview_url": f"/api/bgm/{clean_id}/audio",
                    })

        return tracks

    def get_track_path(self, track_id_or_name: str) -> Optional[Path]:
        """Find the local path for a given BGM track ID or filename."""
        clean = track_id_or_name.strip().lower()
        for t in self.DEFAULT_TRACKS:
            if clean in (t["id"].lower(), t["filename"].lower(), t["name"].lower()):
                p = self.bgm_dir / t["filename"]
                if p.exists():
                    return p

        for f in self.bgm_dir.iterdir():
            if f.is_file() and clean in (f.stem.lower(), f.name.lower()):
                return f

        return None
