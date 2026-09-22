"""AutoTransition Engine inspired by yaojie-shen/AutoTransition.

Recommends optimal video transition effects (smooth dissolve, whip slide, zoom punch,
flash reveal, dip-to-black) based on visual energy, dialogue pacing, and shot boundaries,
paired with audio transition stingers (whooshes, clicks, bass risers).
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

SFX_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "split_sfx"


class TransitionEngine:
    """Intelligently recommends video transition types and transition audio stingers."""

    TRANSITION_TYPES = [
        "dissolve",       # Smooth crossfade alpha blend
        "slide_left",     # Whip slide transition from right to left
        "slide_right",    # Whip slide transition from left to right
        "zoom_punch",     # Scale up punch-in transition
        "flash_white",    # Quick white camera flash transition
        "dip_black",      # Cinematic dip to black
        "cut"             # Standard clean straight cut
    ]

    # Pre-mapped high quality transition stingers from our 93 SFX library
    TRANSITION_STINGERS = {
        "slide_left": {"file": "59_cartoon_slip_whoosh.mp3", "volume": 0.45},
        "slide_right": {"file": "59_cartoon_slip_whoosh.mp3", "volume": 0.45},
        "zoom_punch": {"file": "55_subtle_bass_drop.mp3", "volume": 0.40},
        "flash_white": {"file": "04_camera_shutter.mp3", "volume": 0.45},
        "cut": {"file": "19_snap_click.mp3", "volume": 0.35},
        "dissolve": None  # Dissolves are typically silent or very subtle
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def plan_transitions(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate shot boundaries and recommend transitions for each B-roll cutaway."""
        if not shots:
            return shots

        logger.info(f"TransitionEngine planning dynamic transitions for {len(shots)} shots...")

        # If Gemini client is available, get AI recommendations based on dialogue and theme
        if self.client:
            try:
                shots = self._ai_recommend_transitions(shots)
                return shots
            except Exception as e:
                logger.warning(f"AI transition recommendation failed, falling back to rule-based: {e}")

        # Fallback: Rule-based transition mapping
        return self._rule_based_transitions(shots)

    def _resolve_stinger(self, t_type: str) -> Optional[Dict[str, Any]]:
        """Resolve stinger audio file from local split_sfx or unified catalog."""
        stinger = self.TRANSITION_STINGERS.get(t_type)
        if not stinger:
            return None
        fn = stinger["file"]
        local_p = SFX_DIR / fn
        if local_p.exists():
            return {"file": fn, "path": str(local_p), "volume": stinger["volume"]}
        cat_p = SFX_DIR / "sfx_catalog.json"
        if cat_p.exists():
            try:
                with open(cat_p, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        if item.get("file") == fn or Path(item.get("path", "")).name == fn:
                            p = Path(item["path"])
                            if p.exists():
                                return {"file": p.name, "path": str(p), "volume": stinger["volume"]}
            except Exception:
                pass
        return None

    def _ai_recommend_transitions(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ask Gemini to recommend transitions for each shot based on narrative rhythm."""
        shots_summary = []
        for idx, s in enumerate(shots, start=1):
            shots_summary.append({
                "shot_id": s.get("shot_id", f"broll_{idx}"),
                "start": s.get("start_time"),
                "end": s.get("end_time"),
                "dialogue": s.get("dialogue_quote", ""),
                "emotion": s.get("emotional_core", ""),
                "visual": s.get("search_prompt", "")
            })

        prompt = f"""
You are an expert video editor applying professional transitions between A-roll and B-roll.
Review these sequential B-roll cutaway shots:
{json.dumps(shots_summary, indent=2)}

Available transition types:
- 'dissolve': Soft, elegant crossfade (best for calm, thoughtful, mentorship, or emotional lines)
- 'slide_left': Energetic whip slide left (best for forward momentum, action, high energy)
- 'slide_right': Whip slide right (best for contrasting ideas, checklist items)
- 'zoom_punch': Dramatic punch-in zoom (best for key punchlines, victory, bold statements)
- 'flash_white': Quick camera flash stinger (best for sudden realizations, new topics)
- 'cut': Instant hard cut (best when simplicity is needed)

Assign an entry transition ('transition_in') and duration ('duration_in' in seconds, default 0.3s)
and exit transition ('transition_out', default 'dissolve' or 'slide_left') for each shot.

Return ONLY a JSON list:
[
  {{
    "shot_id": "broll_1",
    "transition_in": "slide_left",
    "duration_in": 0.25,
    "transition_out": "dissolve"
  }}
]
"""

        resp = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        recommendations = json.loads(resp.text)
        rec_map = {r["shot_id"]: r for r in recommendations if "shot_id" in r}

        for idx, shot in enumerate(shots, start=1):
            sid = shot.get("shot_id", f"broll_{idx}")
            rec = rec_map.get(sid, {})
            t_in = rec.get("transition_in", "dissolve")
            if t_in not in self.TRANSITION_TYPES:
                t_in = "dissolve"
            t_out = rec.get("transition_out", "dissolve")
            if t_out not in self.TRANSITION_TYPES:
                t_out = "dissolve"

            trans_info = {
                "type_in": t_in,
                "duration_in": rec.get("duration_in", 0.3),
                "type_out": t_out,
                "duration_out": rec.get("duration_out", 0.3),
            }

            # Attach audio stinger if mapped
            stinger_info = self._resolve_stinger(t_in)
            if stinger_info:
                trans_info["stinger_sfx"] = stinger_info

            shot["transition"] = trans_info
            logger.info(f"Shot [{sid}] transition: IN={t_in} ({trans_info.get('duration_in')}s), OUT={t_out}")

        return shots

    def _rule_based_transitions(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deterministic rhythm-based transition assignment."""
        patterns = ["slide_left", "dissolve", "zoom_punch", "slide_right", "dissolve"]
        for idx, shot in enumerate(shots):
            t_in = patterns[idx % len(patterns)]
            stinger = self.TRANSITION_STINGERS.get(t_in)
            trans_info = {
                "type_in": t_in,
                "duration_in": 0.3,
                "type_out": "dissolve",
                "duration_out": 0.3
            }
            stinger_info = self._resolve_stinger(t_in)
            if stinger_info:
                trans_info["stinger_sfx"] = stinger_info
            shot["transition"] = trans_info
        return shots
