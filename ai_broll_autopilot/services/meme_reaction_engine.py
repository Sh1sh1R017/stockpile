"""Semantic meme/reaction overlay engine for short-form edits.

The engine turns high-impact caption moments into short, contextual reaction
assets. GIPHY is optional; when unavailable, the edit still renders with its
caption/video/SFX treatment.
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
    "shock": ["shocked reaction meme", "what reaction meme", "surprised reaction"],
    "disbelief": ["disbelief reaction meme", "are you serious reaction", "no way reaction meme"],
    "laughing": ["laughing reaction meme", "dying laughing reaction", "lol reaction meme"],
    "confused": ["confused reaction meme", "confused guy reaction", "huh reaction meme"],
    "suspicious": ["suspicious reaction meme", "side eye reaction", "sus reaction meme"],
    "cringe": ["cringe reaction meme", "second hand embarrassment reaction"],
    "celebration": ["celebration reaction meme", "lets go reaction", "money reaction meme"],
    "chaos": ["unhinged reaction meme", "absolute chaos reaction", "what the fuck reaction meme"],
}

IMPACT_TYPES = {"hook", "number", "money", "negation", "action", "named_entity", "chaos", "extreme"}
CHAOTIC_TERMS = {
    "insane", "crazy", "wild", "ridiculous", "unhinged", "literally", "never",
    "nobody", "nothing", "wtf", "fuck", "shit", "broke", "million", "billion",
    "chaos", "absurd", "bonkers", "nuts",
}

MODE_THRESHOLDS = {"subtle": 0.72, "chaotic": 0.42, "unhinged": 0.58}


class MemeReactionEngine:
    """Build and optionally materialize timed GIPHY reaction overlays."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.api_key = os.getenv("GIPHY_API_KEY", "").strip()
        self.cache_dir = Path(cache_dir or os.getenv("STOCKPILE_REACTION_CACHE", "artifacts/reactions"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def classify(self, word: str, semantic_type: str = "normal", emotion: str = "neutral", context: str = "") -> Optional[str]:
        clean = re.sub(r"[^a-z0-9$% ]", "", str(word).lower()).strip()
        ctx = str(context).lower()
        semantic_type = semantic_type.lower()
        if semantic_type in {"money", "number"} or "$" in clean or "%" in clean:
            return "celebration" if any(x in ctx for x in ("made", "earned", "profit", "won", "revenue")) else "shock"
        if semantic_type == "negation" or clean in {"never", "nobody", "nothing", "stop", "impossible"}:
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
        """Create sparse reaction events with deterministic queries and cooldowns."""
        mode = (mode or "unhinged").lower()
        if mode == "off":
            return []
        threshold = MODE_THRESHOLDS.get(mode, MODE_THRESHOLDS["unhinged"])
        events: List[Dict[str, Any]] = []
        for idx, event in enumerate(caption_events):
            word = str(event.get("word", event.get("text", "")))
            semantic_type = str(event.get("semantic_type", event.get("semanticType", "normal")))
            score = float(event.get("importance", event.get("word_importance_score", 0.0)) or 0.0)
            if score < threshold and semantic_type not in {"hook", "money", "number", "negation", "chaos", "extreme"}:
                continue
            reaction = self.classify(word, semantic_type, str(event.get("emotion", "neutral")), str(event.get("sentence", event.get("context", ""))))
            if not reaction:
                continue
            start = max(0.0, float(event.get("start", event.get("start_time", 0.0))) - 0.06)
            end = float(event.get("end", event.get("end_time", start + 0.7))) + 0.18
            intensity = min(1.0, max(0.0, score))
            events.append({
                "id": f"reaction_{idx}_{hashlib.sha1((word + reaction).encode()).hexdigest()[:8]}",
                "word": word,
                "reaction_type": reaction,
                "impact_score": round(score, 3),
                "start_time": start,
                "duration": min(1.05 if mode != "unhinged" else 1.25, max(0.35, end - start)),
                "position": "center_right" if reaction == "chaos" else "reaction_corner",
                "scale": min(0.55, 0.30 + intensity * 0.20),
                "entrance": "slam" if reaction == "chaos" else "pop",
                "query": REACTION_QUERIES[reaction][idx % len(REACTION_QUERIES[reaction])],
            })

        # One meme is funny. Six memes in a second is a PowerPoint from hell.
        filtered: List[Dict[str, Any]] = []
        last_start = -999.0
        last_type = None
        for event in events:
            if event["start_time"] - last_start < (1.35 if mode == "subtle" else 1.10):
                continue
            if event["reaction_type"] == last_type and event["start_time"] - last_start < 2.25:
                continue
            filtered.append(event)
            last_start = event["start_time"]
            last_type = event["reaction_type"]
        return filtered

    def materialize(self, events: List[Dict[str, Any]], work_dir: str) -> List[Dict[str, Any]]:
        """Search GIPHY and download the most render-friendly MP4/GIF rendition."""
        if not self.api_key:
            logger.info("GIPHY_API_KEY not configured; reaction metadata remains available without overlays.")
            return events
        out_dir = Path(work_dir) / "reactions"
        out_dir.mkdir(parents=True, exist_ok=True)
        materialized = []
        for event in events:
            try:
                params = urllib.parse.urlencode({
                    "api_key": self.api_key,
                    "q": event["query"],
                    "limit": 12,
                    "rating": "pg-13",
                    "lang": "en",
                })
                with urllib.request.urlopen(f"https://api.giphy.com/v1/gifs/search?{params}", timeout=8) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                candidates = payload.get("data", [])
                picked = None
                for candidate in candidates:
                    images = candidate.get("images", {})
                    # Prefer a small MP4 to keep FFmpeg fast, then GIF/WebP.
                    picked = (
                        images.get("fixed_width_small", {})
                        or images.get("downsized_small", {})
                        or images.get("fixed_width", {})
                        or images.get("downsized", {})
                    )
                    if picked and (picked.get("mp4") or picked.get("url")):
                        break
                if not picked:
                    continue
                url = picked.get("mp4") or picked.get("url")
                if not url:
                    continue
                ext = ".mp4" if ".mp4" in url else ".gif"
                target = out_dir / f"{event['id']}{ext}"
                if not target.exists():
                    urllib.request.urlretrieve(url, target)
                item = dict(event)
                item["asset_path"] = str(target)
                item["source"] = "giphy"
                item["giphy_id"] = next((c.get("id") for c in candidates if c.get("id")), None)
                materialized.append(item)
            except Exception as exc:
                logger.warning("Reaction asset lookup failed for %s: %s", event.get("word"), exc)
        return materialized
