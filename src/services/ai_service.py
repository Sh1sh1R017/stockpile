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
    """Strip markdown code blocks from AI response text."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class AIService:
    """Service for AI-powered phrase extraction and video evaluation using Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-001"):
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
        """Extract concrete B-roll search phrases from transcript."""
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided for phrase extraction")
            return []

        prompt = f"""You are B-RollExtractor v8.

GOAL
Turn the transcript into concrete, searchable footage queries that depict EXACTLY what is being discussed.

RULES
• Return at least 10 phrases, 2–6 words each.
• Prefer observable subjects + actions + objects + settings.
• For abstract ideas, choose a literal real-world metaphor only when it clearly represents the spoken idea.
• NEVER generate generic filler like "random business footage", "technology background", "person thinking", "successful businessman".
• NEVER introduce sports, gaming, news broadcasts, TV anchors, charts, terminal/code screens, logos, or branded footage unless the transcript explicitly calls for that thing.
• For emotional reactions, use a physical reaction only when the speaker is actually expressing that emotion.
• Target clean footage with no baked-in captions, headlines, lower-thirds, channel bugs, logos, watermarks, or promotional text.
• No duplicates or vague ideas.
• Output JSON array only.

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
                    config=types.GenerateContentConfig(temperature=0.55),
                )
                if response and response.text:
                    response_text = strip_markdown_code_blocks(response.text)
                    break
            except Exception as e:
                logger.warning(f"Phrase extraction model {model_name} failed: {e}. Trying fallback...")

        if not response_text:
            logger.warning("All AI models failed for phrase extraction; falling back to heuristic extraction")
            words = [w.strip() for w in transcript.split() if len(w.strip()) > 3]
            return [" ".join(words[i:i+4]) + " clean clip" for i in range(0, min(len(words), 30), 4)][:10]

        try:
            phrases = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            phrases = re.findall(r'"([^"]+)"', response_text)
            if not phrases:
                phrases = [line.strip(" -•*") for line in response_text.split("\n") if line.strip() and len(line.strip()) < 50]

        cleaned_phrases = []
        for phrase in phrases:
            if isinstance(phrase, str) and phrase.strip():
                clean_phrase = phrase.strip().lower()
                if clean_phrase not in cleaned_phrases:
                    cleaned_phrases.append(clean_phrase)
        return cleaned_phrases[:10]

    @retry_api_call(max_retries=3, base_delay=1.0)
    def evaluate_videos(self, search_phrase: str, video_results: List[VideoResult]) -> List[ScoredVideo]:
        """Evaluate candidates for literal visual relevance and clean broadcast footage."""
        if not video_results:
            logger.info(f"No videos to evaluate for phrase: {search_phrase}")
            return []

        results_text = "\n".join(
            f"ID: {video.video_id}\nTitle: {video.title}\nDescription: {(video.description or 'N/A')[:300]}...\nDuration: {video.duration}s\nURL: {video.url}\n---"
            for video in video_results
        )

        evaluator_prompt = f"""You are a STRICT B-roll editor selecting footage for a short-form video.

SCENE / NARRATIVE CONTEXT:
"{search_phrase}"

CANDIDATE VIDEOS:
---
{results_text}
---

PRIMARY RULE — LITERAL VISUAL RELEVANCE
The selected clip must visibly depict the subject, action, object, place, or clearly supported metaphor described by the scene. Do NOT reward a clip merely because it feels emotional or vaguely related.

REJECT candidates when they are:
• unrelated generic footage
• news broadcasts, TV segments, podcast/talking-head clips, or commentary unless explicitly requested
• computer terminal/code, financial charts, dashboards, slides, articles, headlines, or screens full of text unless the scene explicitly discusses that exact thing
• footage whose dominant visual information is text rather than the requested physical subject/action
• logos, branded overlays, channel bugs, captions, subtitles, lower-thirds, title cards, watermarks, or promotional text
• music videos, gameplay, sports, memes, or reaction clips unless explicitly requested by the scene
• visually ambiguous footage where the claimed relevance cannot be established from the title/description

SCORING
10 = exact visual match + clean footage
8-9 = very strong literal match + clean
6-7 = usable but less exact
<6 = reject

The search phrase is evidence, not permission to invent a connection. Prefer an obvious literal match over a clever metaphor.

OUTPUT ONLY:
[{{"video_id":"abc123","score":10}},{{"video_id":"def456","score":8}}]
"""

        models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        scored_results = None
        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=evaluator_prompt,
                    config=types.GenerateContentConfig(temperature=0.05),
                )
                if not response or not response.text:
                    continue
                text = strip_markdown_code_blocks(response.text)
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        scored_results = parsed
                        break
                except json.JSONDecodeError:
                    import re
                    matches = re.findall(r'"video_id":\s*"([^"]+)".*?"score":\s*(\d+)', response.text)
                    parsed = [{"video_id": vid_id, "score": int(score)} for vid_id, score in matches]
                    if parsed:
                        scored_results = parsed
                        break
            except Exception as e:
                logger.warning(f"Video evaluation model {model_cand} failed: {e}. Trying fallback...")

        if not scored_results:
            logger.info(f"AI evaluation unavailable for '{search_phrase}'; using heuristic scoring")
            return self._heuristic_evaluate_videos(search_phrase, video_results)

        scored_videos = []
        video_lookup = {v.video_id: v for v in video_results}
        for item in scored_results:
            if not isinstance(item, dict) or "video_id" not in item or "score" not in item:
                continue
            video_id = item["video_id"]
            score = item["score"]
            if not isinstance(score, (int, float)) or score < 6 or score > 10 or video_id not in video_lookup:
                continue
            scored_videos.append(ScoredVideo(video_id=video_id, score=int(score), video_result=video_lookup[video_id]))

        return sorted(scored_videos, key=lambda x: x.score, reverse=True) or self._heuristic_evaluate_videos(search_phrase, video_results)

    def _heuristic_evaluate_videos(self, search_phrase: str, video_results: List[VideoResult]) -> List[ScoredVideo]:
        """Deterministic conservative fallback that rejects obvious irrelevant/text-heavy sources."""
        clean_phrase = search_phrase.lower()
        watermark_keywords = [
            "watermark", "watermarked", "preview", "shutterstock", "getty", "pond5", "istock",
            "storyblocks", "depositphotos", "adobe stock", "canva", "freepik", "dreamstime",
            "stock footage", "stock video", "royalty free footage", "news ticker", "breaking news",
            "official music video", "vevo", "closed captions", "subtitles", "lower third"
        ]
        generic_rejects = [
            "podcast", "talk show", "news", "fox business", "cnn", "msnbc", "terminal", "command line",
            "coding tutorial", "programming tutorial", "dashboard", "powerpoint", "slideshow", "gameplay",
            "walkthrough", "playthrough", "basketball", "football", "soccer", "stock market chart"
        ]
        topic_words = [w for w in clean_phrase.split() if len(w) > 2]
        scored_videos = []
        for video in video_results:
            title_low = video.title.lower()
            desc_low = (video.description or "").lower()
            if any(k in title_low or k in desc_low for k in watermark_keywords):
                continue
            if any(k in title_low or k in desc_low for k in generic_rejects):
                if not any(k in clean_phrase for k in generic_rejects):
                    continue
            match_count = sum(1 for tw in topic_words if tw in title_low or tw in desc_low)
            if match_count >= 2:
                score = 9
            elif match_count == 1:
                score = 7
            else:
                continue
            scored_videos.append(ScoredVideo(video_id=video.video_id, score=score, video_result=video))
        return sorted(scored_videos, key=lambda x: x.score, reverse=True)
