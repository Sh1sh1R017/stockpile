"""Pexels Royalty-Free Stock Video Service.

Provides watermark-free 1080x1920 portrait and landscape B-roll footage
using the official Pexels REST API.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.parse
import json

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class PexelsService:
    """Acquires watermark-free stock videos from Pexels API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")

    def is_available(self) -> bool:
        """Check if Pexels API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def search_and_download(
        self,
        query: str,
        output_path: Path,
        duration: float = 3.0,
        orientation: str = "portrait"
    ) -> Optional[str]:
        """Search Pexels for relevant video, download the highest quality vertical stream, and format."""
        if not self.is_available():
            logger.debug("Pexels API key not configured. Skipping Pexels search.")
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_and_download_sync,
            query,
            output_path,
            duration,
            orientation
        )

    def _search_and_download_sync(
        self,
        query: str,
        output_path: Path,
        duration: float,
        orientation: str
    ) -> Optional[str]:
        try:
            import re

            # Normalize and clean query
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()
            # Clean extra spaces
            clean_q = re.sub(r"\s+", " ", clean_q)

            stopwords = {
                "a", "an", "the", "in", "on", "at", "of", "with", "and", "or", "for",
                "to", "my", "his", "her", "that", "this", "is", "are", "was", "were",
                "very", "also", "into", "onto", "from", "by", "as", "about", "be"
            }
            words = [w for w in clean_q.split() if w.lower() not in stopwords]
            simplified_q = " ".join(words[:4]) if words else clean_q

            search_candidates = [clean_q]
            if simplified_q and simplified_q.lower() != clean_q.lower():
                search_candidates.append(simplified_q)
            if len(words) >= 2:
                search_candidates.append(" ".join(words[:2]))

            headers = {
                "Authorization": self.api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            videos = []
            matched_query = clean_q

            # 1. Try search candidates with requested orientation
            for cand in search_candidates:
                if not cand.strip():
                    continue
                encoded = urllib.parse.quote(cand.strip())
                url = f"https://api.pexels.com/videos/search?query={encoded}&orientation={orientation}&per_page=5&size=medium"
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=12) as response:
                        data = json.loads(response.read().decode("utf-8"))
                        videos = data.get("videos", [])
                        if videos:
                            matched_query = cand
                            break
                except Exception as cand_err:
                    logger.debug(f"Pexels query '{cand}' attempt error: {cand_err}")

            # 2. Relaxed orientation fallback if portrait search returned empty
            if not videos:
                for cand in search_candidates:
                    if not cand.strip():
                        continue
                    encoded = urllib.parse.quote(cand.strip())
                    url_relaxed = f"https://api.pexels.com/videos/search?query={encoded}&per_page=3"
                    req_relaxed = urllib.request.Request(url_relaxed, headers=headers)
                    try:
                        with urllib.request.urlopen(req_relaxed, timeout=12) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            videos = data.get("videos", [])
                            if videos:
                                matched_query = cand
                                break
                    except Exception:
                        pass

            if not videos:
                logger.info(f"Pexels found 0 videos across candidates for query: '{query}'")
                return None

            # Pick the best video file
            best_video = videos[0]
            video_files = best_video.get("video_files", [])

            # Smart stream selection: prioritize HD 1080x1920 or 720p, avoid slow 4K downloads
            chosen_file = None
            mp4_files = [vf for vf in video_files if vf.get("file_type") == "video/mp4" and vf.get("link")]

            if mp4_files:
                def stream_priority(vf):
                    w = vf.get("width", 0)
                    h = vf.get("height", 0)
                    # Severe penalty for 4K / UHD (>1440w or >2560h) to avoid massive 60MB downloads
                    is_4k = 1 if (w > 1440 or h > 2560) else 0
                    dist = abs(w - Config.TARGET_WIDTH)
                    return (is_4k, dist)

                mp4_files.sort(key=stream_priority)
                chosen_file = mp4_files[0]

            if not chosen_file and video_files:
                chosen_file = video_files[0]

            if not chosen_file or not chosen_file.get("link"):
                logger.warning(f"No valid MP4 link found in Pexels result for '{query}'")
                return None

            download_link = chosen_file["link"]
            temp_raw = output_path.parent / f"raw_{output_path.name}"

            # Download video stream
            logger.info(f"Downloading Pexels B-roll ({chosen_file.get('width')}x{chosen_file.get('height')}): '{query}'")
            dl_req = urllib.request.Request(download_link, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(dl_req, timeout=30) as dl_resp, open(temp_raw, "wb") as f:
                while True:
                    chunk = dl_resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)

            # Process with FFmpeg: scale to target vertical 9:16 and trim with fast multithreaded preset
            import subprocess
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(temp_raw),
                "-t", str(duration),
                "-vf", f"scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
                       f"pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={Config.TARGET_FPS}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-threads", "0",
                "-crf", str(Config.VIDEO_CRF),
                "-pix_fmt", "yuv420p",
                "-an",
                "-v", "warning",
                str(output_path)
            ]
            subprocess.run(cmd, check=True)

            try:
                temp_raw.unlink(missing_ok=True)
            except Exception:
                pass

            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Pexels footage successfully formatted: {output_path.name}")
                return str(output_path.resolve())

            return None

        except Exception as e:
            logger.error(f"Error fetching Pexels video for '{query}': {e}")
            return None

    async def search_candidates(
        self,
        query: str,
        per_page: int = 6,
        orientation: str = "portrait"
    ) -> List[Dict[str, Any]]:
        """Search Pexels API and return candidate video metadata with previews."""
        if not self.is_available():
            return []

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_candidates_sync,
            query,
            per_page,
            orientation
        )

    def _search_candidates_sync(
        self,
        query: str,
        per_page: int = 6,
        orientation: str = "portrait"
    ) -> List[Dict[str, Any]]:
        try:
            import re
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()
            if not clean_q:
                return []

            headers = {
                "Authorization": self.api_key,
                "User-Agent": "Mozilla/5.0"
            }
            encoded = urllib.parse.quote(clean_q)
            url = f"https://api.pexels.com/videos/search?query={encoded}&orientation={orientation}&per_page={per_page}&size=medium"
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                videos = data.get("videos", [])

            results = []
            for v in videos:
                vid_id = v.get("id")
                image = v.get("image")
                duration = v.get("duration", 0)
                video_files = v.get("video_files", [])

                # Find best vertical MP4
                mp4s = [vf for vf in video_files if vf.get("file_type") == "video/mp4" and vf.get("link")]
                chosen_link = None
                if mp4s:
                    mp4s.sort(key=lambda vf: (1 if (vf.get("width", 0) > 1440 or vf.get("height", 0) > 2560) else 0, abs(vf.get("width", 0) - Config.TARGET_WIDTH)))
                    chosen_link = mp4s[0].get("link")

                results.append({
                    "id": vid_id,
                    "thumbnail": image,
                    "duration": duration,
                    "width": v.get("width"),
                    "height": v.get("height"),
                    "url": v.get("url"),
                    "download_url": chosen_link,
                })

            return results
        except Exception as e:
            logger.error(f"Error searching Pexels candidates for '{query}': {e}")
            return []

    async def download_candidate(
        self,
        download_url: str,
        output_path: Path,
        duration: float = 3.0
    ) -> Optional[str]:
        """Download and format a specific chosen Pexels video stream."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._download_candidate_sync,
            download_url,
            output_path,
            duration
        )

    def _download_candidate_sync(
        self,
        download_url: str,
        output_path: Path,
        duration: float
    ) -> Optional[str]:
        try:
            import subprocess
            temp_raw = output_path.parent / f"raw_{output_path.name}"
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(download_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_raw, "wb") as out_f:
                out_f.write(resp.read())

            target_dur = max(2.5, min(10.0, duration))
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(temp_raw),
                "-t", f"{target_dur:.2f}",
                "-vf", f"scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={Config.TARGET_FPS}",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-threads", "0",
                "-crf", str(Config.VIDEO_CRF),
                "-pix_fmt", "yuv420p",
                "-an",
                "-v", "warning",
                str(output_path)
            ]
            subprocess.run(cmd, check=True)
            temp_raw.unlink(missing_ok=True)
            if output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path.resolve())
            return None
        except Exception as e:
            logger.error(f"Failed to download specific Pexels candidate: {e}")
            return None


pexels_service = PexelsService()
