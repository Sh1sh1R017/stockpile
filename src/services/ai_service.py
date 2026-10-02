"""AI service for phrase extraction and video evaluation using Google GenAI."""

import json
import logging
from typing import List
from google.genai import Client
from google.genai import types

from utils.retry import retry_api_call, APIRateLimitError, NetworkError
from models.video import VideoResult, ScoredVideo

logger = logging.getLogger(__name__)


def strip_markdown_code_blocks(text: str) -> str:
    """Strip markdown code blocks from AI response text.

    Args:
        text: Raw text that may contain markdown code blocks

    Returns:
        Cleaned text with markdown code blocks removed
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    if text.endswith("```"):
        text = text[:-3]  # Remove ```
    return text.strip()


class AIService:
    """Service for AI-powered phrase extraction and video evaluation using Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-001"):
        """Initialize Google GenAI client.

        Args:
            api_key: Google GenAI API key
            model_name: Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client = Client(api_key=api_key)
        self.fallback_models = [
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite",
        ]

        logger.info(f"Initialized AI service with model: {model_name}")

    def extract_search_phrases(self, transcript: str) -> List[str]:
        """Extract B-roll search phrases from transcript using Gemini with model fallback."""
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided for phrase extraction")
            return []

        # B-Roll Extractor prompt with streamer reaction prioritization
        prompt = f"""You are B-RollExtractor v7.

GOAL
Turn the transcript into punchy stock-footage and reaction search phrases an editor can paste into YouTube to find B-roll.

OUTPUT
Return one JSON string array and nothing else.

Example: ["streamer shocked reaction clip", "warehouse worker packing boxes", "streamer laughing meme", "person typing on smartphone", "streamer celebration reaction"]

RULES
• ≥10 phrases.
• 2–6 words each.
• For emotional reactions, surprise, humor, excitement, shock, anger, or celebration, PRIORITIZE streamer reaction clips (e.g., "streamer shocked reaction clip", "streamer laughing meme", "streamer screaming reaction", "streamer facepalm reaction", "streamer celebration clip").
• For physical subjects, objects, or actions, generate clean, tangible visual scenes (e.g., "person scrolling smartphone", "office desk close up").
• Target clean footage with no watermarks.
• No duplicates or vague ideas.
• No markdown, no extra keys, no surrounding text.

TRANSCRIPT ↓
<<<
{transcript}
>>>"""

        models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        response_text = None

        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.85,
                    ),
                )
                if response and response.text:
                    response_text = strip_markdown_code_blocks(response.text)
                    break
            except Exception as e:
                logger.warning(f"Phrase extraction model {model_name} failed: {e}. Trying fallback...")
                continue

        if not response_text:
            logger.warning("All AI models failed for phrase extraction; falling back to heuristic extraction")
            words = [w.strip() for w in transcript.split() if len(w.strip()) > 3]
            phrases = []
            if "reaction" not in transcript.lower():
                phrases.append("streamer shocked reaction clip")
            for i in range(0, min(len(words), 30), 4):
                chunk = " ".join(words[i:i+4])
                if chunk:
                    phrases.append(f"{chunk} clean clip")
            return phrases[:10]

        try:
            phrases = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            phrases = re.findall(r'"([^"]+)"', response_text)
            if not phrases:
                lines = response_text.strip().split("\n")
                phrases = [
                    line.strip(" -•*")
                    for line in lines
                    if line.strip() and len(line.strip()) < 50
                ]

        cleaned_phrases = []
        for phrase in phrases:
            if isinstance(phrase, str) and phrase.strip():
                clean_phrase = phrase.strip().lower()
                if len(clean_phrase) > 0 and clean_phrase not in cleaned_phrases:
                    cleaned_phrases.append(clean_phrase)

        return cleaned_phrases[:10]

    @retry_api_call(max_retries=3, base_delay=1.0)
    def evaluate_videos(
        self, search_phrase: str, video_results: List[VideoResult]
    ) -> List[ScoredVideo]:
        """Evaluate YouTube videos for B-roll suitability using Gemini.

        Args:
            search_phrase: The search phrase used to find videos
            video_results: List of video search results

        Returns:
            List of scored videos (score >= 6 only)
        """
        if not video_results:
            logger.info(f"No videos to evaluate for phrase: {search_phrase}")
            return []

        # Format video results for AI evaluation
        results_text = "\n".join(
            [
                f"ID: {video.video_id}\n"
                f"Title: {video.title}\n"
                f"Description: {video.description[:200] if video.description else 'N/A'}...\n"
                f"Duration: {video.duration}s\n"
                f"URL: {video.url}\n"
                "---"
                for video in video_results
            ]
        )

        evaluator_prompt = f"""You are B-Roll Evaluator with strict Broadcast Quality and Human Relatability standards.
Your goal is to select the cleanest, most emotionally resonant, human-relatable YouTube videos for a given search phrase and narrative context.

SEARCH PHRASE / SCENE:
"{search_phrase}"

YOUTUBE RESULTS:
---
{results_text}
---

CRITICAL SCORING CRITERIA:
1. EMOTIONAL RESONANCE & HUMAN RELATABILITY (50% of score):
   - Rate 9-10 (HIGHEST PRIORITY): Real human drama that viewers instantly connect with emotionally:
     • e.g. Packing a cardboard box with personal belongings, walking out of an office after being fired.
     • e.g. Frustrated employee in computer rage, banging keyboard/desk, head in hands at chaotic desk.
     • e.g. An empty desolate office cubicle, lonely rolling chair, dark office after layoffs.
   - Rate 6-8: Relevant physical work or workplace action (e.g. typing furiously on keyboard, business meeting).
   - Rate 1-5 (REJECT): Flat, lifeless, generic, or unrelatable clips (e.g. random building exteriors, industrial robot assembly lines, music videos, cartoon factory machines, podcast talking heads).

2. NO WATERMARKS OR OVERLAYS:
   - Strictly reject (score < 6) any videos with stock watermarks (Shutterstock, Getty, Pond5, Clever Stock), title cards, lyrics, subtitles, channel bugs, or news tickers.

3. QUALITY & PACING:
   - Must be punchy cinematic live-action video, not a PowerPoint slideshow or advice talk show.

OUTPUT:
Return a JSON array of objects with video_id and score (6 to 10), ordered by score (highest first).
Format: [{{"video_id": "abc123", "score": 10}}, {{"video_id": "def456", "score": 8}}]
Return only the JSON array, nothing else."""

        models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        scored_results = None

        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=evaluator_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Low temperature for consistent evaluation
                    ),
                )
                if not response or not response.text:
                    continue

                text = strip_markdown_code_blocks(response.text)
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        scored_results = parsed
                        break
                except json.JSONDecodeError:
                    import re
                    matches = re.findall(
                        r'"video_id":\s*"([^"]+)".*?"score":\s*(\d+)', response.text
                    )
                    parsed = [
                        {"video_id": vid_id, "score": int(score)}
                        for vid_id, score in matches
                        if int(score) >= 6
                    ]
                    if parsed:
                        scored_results = parsed
                        break
            except Exception as e:
                logger.warning(f"Video evaluation model {model_cand} failed: {e}. Trying fallback...")
                continue

        # If all AI models fail, use clean heuristic evaluation
        if not scored_results:
            logger.info(f"AI evaluation unavailable for '{search_phrase}'; using heuristic scoring")
            return self._heuristic_evaluate_videos(search_phrase, video_results)

        # Create ScoredVideo objects
        scored_videos = []
        video_lookup = {v.video_id: v for v in video_results}

        for item in scored_results:
            if (
                not isinstance(item, dict)
                or "video_id" not in item
                or "score" not in item
            ):
                continue

            video_id = item["video_id"]
            score = item["score"]

            # Validate score
            if not isinstance(score, (int, float)) or score < 6 or score > 10:
                continue

            # Find corresponding video result
            if video_id not in video_lookup:
                continue

            scored_video = ScoredVideo(
                video_id=video_id,
                score=int(score),
                video_result=video_lookup[video_id],
            )
            scored_videos.append(scored_video)

        if not scored_videos:
            return self._heuristic_evaluate_videos(search_phrase, video_results)

        # Sort by score (highest first)
        scored_videos.sort(key=lambda x: x.score, reverse=True)
        logger.info(
            f"Evaluated videos for '{search_phrase}': {len(scored_videos)} videos scored >= 6"
        )
        return scored_videos

    def _heuristic_evaluate_videos(
        self, search_phrase: str, video_results: List[VideoResult]
    ) -> List[ScoredVideo]:
        """Deterministic heuristic scoring when Gemini models are unavailable or rate-limited."""
        clean_phrase = search_phrase.lower()
        reaction_keywords = [
            "streamer", "reaction", "react", "twitch", "clip", "meme",
            "speed", "kai", "xqc", "screaming", "crying", "laugh", "shock", "rage"
        ]
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
            "news ticker", "breaking news", "official music video", "vevo",
            "closed captions", "subtitles"
        ]

        scored_videos = []
        topic_words = [w for w in clean_phrase.split() if len(w) > 2]

        for video in video_results:
            title_low = video.title.lower()
            desc_low = (video.description or "").lower()

            # Strictly reject watermarked stock previews
            if any(wm in title_low or wm in desc_low for wm in watermark_keywords):
                continue

            # Reject random gaming streams unless user query specifically asks for gaming
            if "game" not in clean_phrase and "gaming" not in clean_phrase:
                if any(gw in title_low for gw in ["gameplay", "walkthrough", "playthrough", "lets play", "horror game", "roblox", "fortnite", "minecraft"]):
                    continue

            # Calculate topical relevance match count
            match_count = sum(1 for tw in topic_words if tw in title_low or tw in desc_low)

            if match_count >= 2:
                score = 9  # High topical relevance
            elif match_count == 1:
                score = 8
            elif "clip" in title_low or "b-roll" in title_low:
                score = 7
            else:
                score = 6

            scored_videos.append(
                ScoredVideo(video_id=video.video_id, score=score, video_result=video)
            )

        scored_videos.sort(key=lambda x: x.score, reverse=True)
        # If all scored videos were filtered, check if any candidate is completely watermark-free
        if not scored_videos and video_results:
            for vr in video_results:
                t = vr.title.lower()
                d = (vr.description or "").lower()
                if not any(wm in t or wm in d for wm in watermark_keywords):
                    scored_videos.append(ScoredVideo(video_id=vr.video_id, score=6, video_result=vr))
                    break
        return scored_videos
