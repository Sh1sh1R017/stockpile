"""Semantic meme/reaction overlay engine for short-form edits.

The engine turns high-impact caption words into short, contextual reaction overlays.
GIPHY is optional: without a GIPHY API key the engine simply returns no assets, so
rendering remains fully backwards compatible.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


REACTION_QUERIES = {
    "shock": ["shocked reaction", "what reaction", "surprised reaction"],
    "disbelief": ["disbelief reaction", "are you serious reaction", "no way reaction"],
    "laughing": ["laughing reaction", "dying laughing reaction", "lol reaction"],
    "confused": ["confused reaction", "confused guy reaction", "huh reaction"],
    "suspicious": ["suspicious reaction", "side eye reaction", "sus reaction"],
    "cringe": ["cringe reaction", "second hand embarrassment reaction"],
    "celebration": ["celebration reaction", "lets go reaction", "money reaction"],
    "chaos": ["unhinged reaction", "chaos reaction", "what the fuck reaction"],
}

IMPACT_TYPES = {"hook", "number", "money", "negation", "action", "named_entity"}
CHAOTIC_TERMS = {
    "insane", "crazy", "wild", "ridiculous", "unhinged", "literally", "never",
    "nobody", "nothing", "wtf", "fuck", "shit", "broke", "million", "billion",
}


class MemeReactionEngine:
    """Build and optionally materialize timed GIPHY reaction overlays."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.api_key = os.getenv("GIPHY_API_KEY", "").strip()
        self.cache_dir = Path(cache_dir or os.getenv("STOCKPILE_REACTION_CACHE", "artifacts/reactions"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def classify(self, word: str, semantic_type: str = "normal", emotion: str = "neutral", context: str = "") -> Optional[str]:
        """Choose a reaction family from the word and nearby sentence context."""
        clean = re.sub(r"[^a-z0-9$% ]", "", str(word).lower()).strip()
        ctx = str(context).lower()
        if semantic_type in {"money", "number"} or "$" in clean or "%" in clean:
            return "celebration" if any(x in ctx for x in ("made", "earned", "profit", "won", "revenue")) else "shock"
        if semantic_type == "negation" or clean in {"never", "nobody", "nothing", "stop"}:
            return "disbelief"
        if any(t in clean or t in ctx for t in CHAOTIC_TERMS):
            return "chaos"
        if emotion in {"surprise", "fear", "shock"}:
            return "shock"
        if emotion in {"joy", "amusement", "laughing"}:
            return "laughing"
        if "sus" in ctx or "suspicious" in ctx:
            return "suspicious"
        if semantic_type in IMPACT_TYPES:
            return "disbelief"
        return None

    def build_events(self, caption_events: List[Dict[str, Any]], mode: str = "unhinged") -> List[Dict[str, Any]]:
        """Return reaction event metadata; only high-impact words become reactions."""
        if mode == "off":
            return []
        events: List[Dict[str, Any]] = []
        for idx, event in enumerate(caption_events):
            word = str(event.get("word", event.get("text", "")))
            semantic_type = str(event.get("semantic_type", "normal"))
            score = float(event.get("importance", event.get("word_importance_score", 0.0)) or 0.0)
            # Chaotic mode intentionally has a lower threshold, but still requires
            # semantic evidence so the video doesn't become random GIF soup.
            threshold = 0.42 if mode == "chaotic" else 0.58 if mode == "unhinged" else 0.72
            if score < threshold and semantic_type not in {"hook", "money", "number", "negation"}:
                continue
            reaction = self.classify(word, semantic_type, str(event.get("emotion", "neutral")), str(event.get("sentence", "")))
            if not reaction:
                continue
            start = max(0.0, float(event.get("start", event.get("start_time", 0.0))) - 0.06)
            end = float(event.get("end", event.get("end_time", start + 0.7))) + 0.18
            events.append({
                "id": f"reaction_{idx}_{hashlib.sha1(word.encode()).hexdigest()[:8]}",
                "word": word,
                "reaction_type": reaction,
                "start_time": start,
                "duration": min(1.25, max(0.35, end - start)),
                "position": "reaction_corner" if reaction != "chaos" else "center_right",
                "scale": 0.34 if reaction != "chaos" else 0.48,
                "query": REACTION_QUERIES[reaction][idx % len(REACTION_QUERIES[reaction])],
            })
        # Avoid a wall of memes: keep at most one reaction every 1.1 seconds.
        filtered: List[Dict[str, Any]] = []
        for event in events:
            if filtered and event["start_time"] - filtered[-1]["start_time"] < 1.1:
                continue
            filtered.append(event)
        return filtered

    def materialize(self, events: List[Dict[str, Any]], work_dir: str) -> List[Dict[str, Any]]:
        """Search GIPHY and download MP4/WebP-compatible reaction assets when configured."""
        if not self.api_key:
            logger.info("GIPHY_API_KEY not configured; reaction metadata will remain available without overlays.")
            return events
        out_dir = Path(work_dir) / "reactions"
        out_dir.mkdir(parents=True, exist_ok=True)
        materialized = []
        for event in events:
            try:
                params = urllib.parse.urlencode({"api_key": self.api_key, "q": event["query"], "limit": 8, "rating": "pg-13", "lang": "en"})
                with urllib.request.urlopen(f"https://api.giphy.com/v1/gifs/search?{params}", timeout=8) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                candidates = payload.get("data", [])
                if not candidates:
                    continue
                # Prefer MP4, then downsized MP4, then GIF source.
                picked = None
                for candidate in candidates:
                    images = candidate.get("images", {})
                    picked = images.get("fixed_width", {}) or images.get("downsized", {})
                    if picked:
                        break
                url = (picked or {}).get("mp4") or (picked or {}).get("url")
                if not url:
                    continue
                ext = ".mp4" if ".mp4" in url else ".gif"
                target = out_dir / f"{event['id']}{ext}"
                if not target.exists():
                    urllib.request.urlretrieve(url, target)
                item = dict(event)
                item["asset_path"] = str(target)
                item["source"] = "giphy"
                item["giphy_id"] = candidates[0].get("id")
                materialized.append(item)
            except Exception as exc:
                logger.warning("Reaction asset lookup failed for %s: %s", event.get("word"), exc)
        return materialized
