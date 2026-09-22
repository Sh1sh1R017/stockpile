"""YouTube search service using yt-dlp for finding B-roll videos."""

import logging
import yt_dlp
from typing import List, Dict, Optional

from models.video import VideoResult
from utils.retry import retry_api_call, NetworkError, TemporaryServiceError
from utils.config import load_config

logger = logging.getLogger(__name__)

# Configure yt-dlp logging to be silent
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)
logging.getLogger("yt_dlp.extractor").setLevel(logging.CRITICAL)
logging.getLogger("yt_dlp.downloader").setLevel(logging.CRITICAL)


def video_filter(info: Dict) -> Optional[str]:
    """Filter videos based on duration and other criteria.

    Args:
        info: Video information dictionary from yt-dlp

    Returns:
        String describing why video was filtered, or None if it passes
    """
    config = load_config()
    max_duration = config.get("max_video_duration_seconds", 3600)
    max_size = config.get("max_video_size_mb", 100) * 1024 * 1024

    # Check duration (relaxed to 3600s since yt-dlp only downloads a 3s slice)
    duration = info.get("duration")
    if duration is not None and duration > max_duration:
        return f"Duration {duration}s exceeds maximum {max_duration}s"

    size = info.get("filesize")
    if size is not None and size > max_size:
        return f"Size {size} exceeds maximum {max_size} bytes"

    # Filter out watermarked stock previews and stock agency channels
    title = (info.get("title") or "").lower()
    uploader = (info.get("uploader") or "").lower()
    channel = (info.get("channel") or "").lower()
    desc = (info.get("description") or "").lower()

    watermark_keywords = [
        "watermark", "watermarked", "with watermark", "preview only", "preview",
        "stock footage preview", "sample footage", "shutterstock", "getty images",
        "gettyimages", "getty", "pond5", "pond 5", "istock", "istockphoto",
        "storyblocks", "depositphotos", "123rf", "adobe stock", "adobestock",
        "clever stock", "cleverstock", "vectorstock", "canva", "freepik",
        "dreamstime", "filmpac", "filmsupply", "artgrid", "footage island",
        "envato", "videohive", "motion array", "motionarray", "motionelements",
        "dissolve footage", "dissolve stock", "stock footage", "stock video",
        "stock library", "royalty free footage", "royalty-free footage",
        "no copyright footage", "free stock video", "free stock footage",
        "copyright free footage", "copyright free video", "sarasota herald",
        "news ticker", "breaking news", "official music video", "vevo"
    ]
    for kw in watermark_keywords:
        if kw in title:
            return f"Video title contains watermark keyword: {kw}"
        if kw in uploader or kw in channel:
            return f"Video channel/uploader is stock footage agency: {kw}"

    # Also check description for overt stock agency watermark links
    stock_urls = ["shutterstock.com", "gettyimages.com", "pond5.com", "istockphoto.com", "storyblocks.com", "cleverstock"]
    for su in stock_urls:
        if su in desc:
            return f"Video description contains stock purchase link: {su}"

    return None


class YouTubeService:
    """Service for searching YouTube videos using yt-dlp."""

    def __init__(self, max_results: int = 20):
        """Initialize YouTube search service."""
        self.max_results = max_results

        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }

    @staticmethod
    def clean_search_phrase(phrase: str) -> str:
        """Simplify verbose search prompts into punchy, high-yield YouTube search queries while preserving topical subject matter."""
        import re
        p = phrase.lower()
        fillers = [
            "looking at screen in disbelief", "looking at screen", "in disbelief",
            "in the background", "high quality footage of", "high quality", "stock footage",
            "showing a", "close up of", "shot of", "a clip of", "clean clip", "no watermark",
            "looking into camera", "talking to camera", "photorealistic", "cinematic"
        ]
        for f in fillers:
            p = p.replace(f, " ")

        words = re.findall(r"\b[a-z0-9]+\b", p)
        # Drop generic stop words while keeping key nouns and verbs
        stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "of"}
        meaningful_words = [w for w in words if w not in stopwords]

        if not meaningful_words:
            return phrase.strip()

        # Limit to 3-5 punchy keywords for optimal YouTube algorithmic search
        return " ".join(meaningful_words[:5])

    @retry_api_call(max_retries=3, base_delay=2.0)
    def search_videos(self, search_phrase: str) -> List[VideoResult]:
        """Search YouTube for videos matching the search phrase with fallback queries."""
        if not search_phrase.strip():
            return []

        cleaned_phrase = self.clean_search_phrase(search_phrase)
        logger.info(f"Searching YouTube for: '{search_phrase}' (cleaned: '{cleaned_phrase}')")

        neg_filters = "-stock -preview -watermark -shutterstock -getty -pond5 -footage"
        candidate_queries = [
            f"{cleaned_phrase} {neg_filters}",
            f"{cleaned_phrase} b-roll {neg_filters}",
            cleaned_phrase,
        ]
        if search_phrase.lower() != cleaned_phrase:
            candidate_queries.append(f"{search_phrase.lower()} {neg_filters}")

        for query in candidate_queries:
            try:
                search_query = f"ytsearch{self.max_results}:{query}"

                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    search_results = ydl.extract_info(search_query, download=False)

                    if not search_results or "entries" not in search_results:
                        continue

                    video_results = []
                    filtered_count = 0
                    for entry in search_results["entries"]:
                        if entry is None:
                            continue

                        # Filter video before parsing
                        filter_result = video_filter(entry)
                        if filter_result:
                            filtered_count += 1
                            logger.debug(
                                f"Video {entry.get('id', 'unknown')} filtered: {filter_result}"
                            )
                            continue

                        video_result = self._parse_video_entry(entry)
                        if video_result:
                            video_results.append(video_result)

                    if filtered_count > 0:
                        logger.info(
                            f"Filtered out {filtered_count} videos that didn't meet criteria for '{query}'"
                        )

                    if video_results:
                        return video_results

            except Exception as e:
                logger.warning(f"YouTube search attempt failed for query '{query}': {e}")
                continue

        logger.warning(f"No usable YouTube results found across candidate queries for: '{search_phrase}'")
        return []

    def _parse_video_entry(self, entry: Dict) -> Optional[VideoResult]:
        """Parse a yt-dlp video entry into a VideoResult object."""
        try:
            video_id = entry.get("id")
            if not video_id:
                return None

            return VideoResult(
                video_id=video_id,
                title=entry.get("title", "Unknown Title"),
                url=f"https://www.youtube.com/watch?v={video_id}",
                duration=entry.get("duration", 0) or 0,
                description=entry.get("description", ""),
            )

        except Exception as e:
            logger.warning(f"Failed to parse video entry: {e}")
            return None
