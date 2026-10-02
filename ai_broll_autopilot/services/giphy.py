"""Giphy Stock and Reaction GIF / B-roll Service.

Provides animated GIF / MP4 clips using the official Giphy REST API.
Converts GIF/MP4 responses into standardized 1080x1920 vertical video B-roll.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class GiphyService:
    """Acquires reaction, meme, and thematic B-roll clips from the Giphy API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(Config, "GIPHY_API_KEY", "") or os.getenv("GIPHY_API_KEY", "S158gtyK087a7AuLRiiAVuEsFZCE8Btj")

    def is_available(self) -> bool:
        """Check if Giphy API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def search_and_download(
        self,
        query: str,
        output_path: Path,
        duration: float = 2.5,
        used_ids: Optional[Set[str]] = None,
    ) -> Optional[Tuple[str, str]]:
        """Search Giphy for an animated clip matching query and format into vertical MP4.

        Returns (asset_path, giphy_id) or None.
        """
        if not self.is_available():
            logger.debug("Giphy API key not configured. Skipping Giphy search.")
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_and_download_sync,
            query,
            output_path,
            duration,
            used_ids or set(),
        )

    def _search_and_download_sync(
        self,
        query: str,
        output_path: Path,
        duration: float,
        used_ids: Set[str],
    ) -> Optional[Tuple[str, str]]:
        try:
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()
            clean_q = re.sub(r"\s+", " ", clean_q)

            stopwords = {
                "a", "an", "the", "in", "on", "at", "of", "with", "and", "or", "for",
                "to", "my", "his", "her", "that", "this", "is", "are", "was", "were",
                "very", "also", "into", "onto", "from", "by", "as", "about", "be"
            }
            words = [w for w in clean_q.split() if w.lower() not in stopwords]
            search_candidates = [clean_q]
            if words:
                search_candidates.append(" ".join(words[:3]))
                if len(words) >= 2:
                    search_candidates.append(" ".join(words[:2]))

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            chosen_item = None
            chosen_url = None
            giphy_id = None

            for cand in search_candidates:
                if not cand.strip():
                    continue
                encoded = urllib.parse.quote(cand.strip())
                url = f"https://api.giphy.com/v1/gifs/search?api_key={self.api_key}&q={encoded}&limit=15&rating=pg-13"
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode("utf-8"))
                        items = data.get("data", [])
                        for item in items:
                            gid = item.get("id")
                            if gid and gid in used_ids:
                                continue
                            imgs = item.get("images", {})
                            mp4_url = (
                                imgs.get("original", {}).get("mp4")
                                or imgs.get("downsized_large", {}).get("mp4")
                                or imgs.get("downsized_medium", {}).get("mp4")
                                or imgs.get("downsized_small", {}).get("mp4")
                                or imgs.get("fixed_height", {}).get("mp4")
                            )
                            if mp4_url:
                                chosen_item = item
                                chosen_url = mp4_url
                                giphy_id = gid
                                break
                            # Fallback to webp or gif if no direct mp4
                            gif_url = imgs.get("original", {}).get("url")
                            if gif_url:
                                chosen_item = item
                                chosen_url = gif_url
                                giphy_id = gid
                                break
                    if chosen_url:
                        break
                except Exception as ex:
                    logger.debug("Giphy candidate query '%s' failed: %s", cand, ex)

            if not chosen_url or not giphy_id:
                logger.info("No unique Giphy clips found for query: '%s'", query)
                return None

            output_path.parent.mkdir(parents=True, exist_ok=True)
            temp_dl = output_path.parent / f"temp_giphy_{giphy_id}.bin"

            req = urllib.request.Request(chosen_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r, open(temp_dl, "wb") as f:
                f.write(r.read())

            target_w = Config.TARGET_WIDTH
            target_h = Config.TARGET_HEIGHT

            # Convert downloaded Giphy file to standard 1080x1920 MP4
            # DO NOT loop the clip. Fit or fill to 1080x1920 portrait.
            scale_filter = (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},setsar=1"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_dl),
                "-t", f"{duration:.3f}",
                "-vf", scale_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                "-an",
                "-movflags", "+faststart",
                str(output_path),
            ]

            res = subprocess.run(cmd, capture_output=True, text=True)
            temp_dl.unlink(missing_ok=True)

            if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                logger.info("Successfully acquired Giphy B-roll clip '%s' -> %s", query, output_path.name)
                return str(output_path.resolve()), giphy_id

            logger.warning("FFmpeg formatting failed for Giphy clip: %s", res.stderr)
            return None

        except Exception as e:
            logger.error("Error fetching Giphy video for '%s': %s", query, e)
            return None


giphy_service = GiphyService()
