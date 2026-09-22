"""Video Sound Effect Analyzer inspired by sieve-community/video-sound-effect.

Extracts representative keyframes from B-roll videos, analyzes visual actions and
narrative context with Multimodal Vision AI (Gemini), and selects the best matching
sound effect from the curated SFX library.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

SFX_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "split_sfx"
CATALOG_PATH = SFX_DIR / "sfx_catalog.json"


class VideoSFXAnalyzer:
    """Analyzes video visual frames and assigns contextual sound effects."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> List[Dict[str, Any]]:
        """Load curated 93-sound effect library catalog."""
        if not CATALOG_PATH.exists():
            logger.warning(f"SFX catalog not found at {CATALOG_PATH}")
            return []
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading SFX catalog: {e}")
            return []

    async def analyze_and_assign_sfx(self, shots: List[Dict[str, Any]], work_dir: Path) -> List[Dict[str, Any]]:
        """Analyze each shot's video footage and recommend contextual SFX."""
        if not self.catalog or not self.client:
            logger.warning("VideoSFXAnalyzer: Missing SFX catalog or Gemini client. Skipping SFX assignment.")
            return shots

        logger.info(f"VideoSFXAnalyzer analyzing {len(shots)} B-roll shots for sound effect matching...")

        for idx, shot in enumerate(shots, start=1):
            try:
                asset_path = shot.get("asset_path")
                frame_path = None
                if asset_path and os.path.exists(asset_path):
                    duration = float(shot.get("duration", 3.0))
                    mid_time = round(duration / 2.0, 2)
                    candidate_frame = work_dir / f"sfx_frame_shot_{idx}.jpg"
                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(mid_time),
                        "-i", str(asset_path),
                        "-vframes", "1",
                        "-q:v", "2",
                        str(candidate_frame)
                    ]
                    subprocess.run(cmd, capture_output=True)
                    if candidate_frame.exists():
                        frame_path = candidate_frame

                # 2. Vision analysis & sound selection (sieve-community/video-sound-effect style)
                matched_sfx = self._query_vision_for_sfx(
                    frame_path=frame_path,
                    dialogue=shot.get("dialogue_quote", ""),
                    visual_query=shot.get("search_prompt", shot.get("visual_query", "")),
                    category=shot.get("emotional_core", "")
                )

                if matched_sfx:
                    shot["contextual_sfx"] = matched_sfx
                    logger.info(f"Shot [{shot.get('shot_id', f'shot_{idx}')}] assigned SFX: {matched_sfx.get('name')} ({matched_sfx.get('file')})")
            except Exception as e:
                logger.error(f"Failed to analyze SFX for shot {idx}: {e}")

        return shots

    def _query_vision_for_sfx(self, frame_path: Optional[Path], dialogue: str, visual_query: str, category: str) -> Optional[Dict[str, Any]]:
        """Query Gemini Vision with the video frame to select the best sound from the catalog."""
        # Create a compact index of available sound effects
        catalog_summary = "\n".join([
            f"- ID {s['id']}: {s['name']} ({s['file']}) | Category: {s['cat']} | Desc: {s['desc']}"
            for s in self.catalog
        ])

        prompt = f"""
You are an expert sound designer for viral short-form videos.
Analyze this video keyframe from a B-roll cutaway shot.

Shot Context:
- Visual Search Topic: {visual_query}
- Spoken Dialogue: "{dialogue}"
- Scene Theme: {category}

TASK:
Choose the SINGLE BEST sound effect from the following library to place during this visual cutaway.
You can choose a realistic ambient Foley sound (e.g., keyboard typing, pencil writing, cash register, camera shutter, bell ding), a subtle impact, or a fitting reaction stinger that enhances the scene without distracting from the speech.
If the scene is purely talking and no sound effect is needed, you may select None.

Library of Available Sound Effects:
{catalog_summary}

Respond ONLY with a JSON object:
{{
  "selected_id": 10,
  "file": "10_cash_register_kaching.mp3",
  "name": "Cash Register Ka-Ching",
  "reason": "Businessman checking financial metrics / clipboard",
  "volume": 0.40,
  "start_offset": 0.3
}}
Or if no sound effect fits:
{{
  "selected_id": null
}}
"""

        try:
            contents = []
            if frame_path and os.path.exists(frame_path):
                uploaded_frame = self.client.files.upload(file=str(frame_path))
                contents.append(uploaded_frame)
            contents.append(prompt)

            resp = self.client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            data = json.loads(resp.text)
            sel_id = data.get("selected_id")
            if sel_id is not None:
                # Find in catalog
                for item in self.catalog:
                    if item["id"] == sel_id:
                        sfx_file = item["file"]
                        sfx_path = Path(item["path"]) if "path" in item else (SFX_DIR / sfx_file)
                        if sfx_path.exists():
                            return {
                                "id": item["id"],
                                "name": item["name"],
                                "file": sfx_file,
                                "path": str(sfx_path),
                                "category": item["cat"],
                                "volume": data.get("volume", 0.40),
                                "start_offset": data.get("start_offset", 0.2),
                                "reason": data.get("reason", "")
                            }
        except Exception as e:
            logger.warning(f"Gemini Vision SFX selection error: {e}")

        return None
