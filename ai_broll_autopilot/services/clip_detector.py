"""Viral Clip Detection Service.

Discovers high-potential short-form video clips from long-form content
using a 9-factor viral scoring framework, with LLM and algorithmic implementations.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from google import genai

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ClipCandidate:
    """A detected viral clip candidate with multi-factor scoring and editorial metadata."""
    id: str
    start_time: float
    end_time: float
    duration: float
    title: str
    hook_text: str
    summary: str
    viral_score: float                  # 0 to 100 overall score
    factor_scores: Dict[str, float]     # Breakdown of the 9 scoring dimensions
    rationale: str
    suggested_broll_topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    recommended_aspect_ratio: str = "9:16"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": round(self.duration, 2),
            "title": self.title,
            "hook_text": self.hook_text,
            "summary": self.summary,
            "viral_score": round(self.viral_score, 1),
            "factor_scores": {k: round(v, 1) for k, v in self.factor_scores.items()},
            "rationale": self.rationale,
            "suggested_broll_topics": self.suggested_broll_topics,
            "tags": self.tags,
            "recommended_aspect_ratio": self.recommended_aspect_ratio,
        }


def _clean_json_str(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class ClipDetectionService:
    """Evaluates long-form transcripts to locate high-retention short clips."""

    # Scoring dimension weights summing to 1.0
    WEIGHTS = {
        "hook_strength": 0.20,
        "novelty": 0.12,
        "emotional_resonance": 0.13,
        "controversy": 0.10,
        "story_arc": 0.12,
        "standalone_coherence": 0.13,
        "humor": 0.08,
        "surprise": 0.07,
        "quotability": 0.05,
    }

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    async def detect_clips(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float,
        target_clip_count: int = 5,
        min_duration: float = 25.0,
        max_duration: float = 75.0,
        niche_id: Optional[str] = None,
    ) -> List[ClipCandidate]:
        """Detect and rank viral short clip opportunities.

        Args:
            transcript_segments: List of segment dicts with start, end, text.
            video_duration: Total video length in seconds.
            target_clip_count: Target number of top non-overlapping clips.
            min_duration: Minimum clip duration in seconds.
            max_duration: Maximum clip duration in seconds.
            niche_id: Content niche to tailor virality criteria.

        Returns:
            List of ranked ClipCandidate objects.
        """
        if not transcript_segments:
            return []

        # If LLM available, use prompt with 9-factor evaluation
        if self.client and len(transcript_segments) > 0:
            try:
                candidates = await self._detect_with_llm(
                    transcript_segments,
                    video_duration,
                    target_clip_count=target_clip_count,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    niche_id=niche_id,
                )
                if candidates:
                    return candidates
            except Exception as e:
                logger.warning(f"LLM clip detection failed: {e}. Falling back to algorithmic window scanner.")

        # Deterministic window scanner fallback
        return self._detect_algorithmic(
            transcript_segments,
            video_duration,
            target_clip_count=target_clip_count,
            min_duration=min_duration,
            max_duration=max_duration,
        )

    async def _detect_with_llm(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        target_clip_count: int = 5,
        min_duration: float = 25.0,
        max_duration: float = 75.0,
        niche_id: Optional[str] = None,
    ) -> List[ClipCandidate]:
        """Use Gemini to evaluate narrative arcs and viral retention factors."""
        formatted_segments = "\n".join([
            f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}"
            for s in segments
        ])

        prompt = f"""You are a master viral short-form video editor for TikTok, YouTube Shorts, and Instagram Reels.
Analyze this video transcript and identify the top {target_clip_count} most viral standalone short clips.

Clip constraints:
- Duration: between {min_duration}s and {max_duration}s
- Niche context: {niche_id or 'general'}
- Must have a strong curiosity-inducing or shocking hook in the first 3 seconds
- Must make complete sense on its own without needing the rest of the episode
- Must end on a punchline, conclusion, or cliffhanger

Evaluate every candidate across these 9 viral factors (each 0 to 100):
1. hook_strength: Curiosity gap, instant punchiness, question, or bold claim
2. novelty: Unique take, non-obvious insight, or rare story
3. emotional_resonance: Intensity, vulnerability, passion, or fire
4. controversy: Debate-sparking, counter-intuitive, or challenging conventional wisdom
5. story_arc: Has clear setup, progression, and climax/payoff
6. standalone_coherence: Understandable to a stranger without context
7. humor: Comedy, wit, funny reaction, or awkward moment
8. surprise: Unexpected plot twist, stat, or revelation
9. quotability: Memorable one-liner or punchline

Transcript:
{formatted_segments[:35000]}

Respond ONLY with valid JSON array of objects matching:
[
  {{
    "start_time": <float seconds>,
    "end_time": <float seconds>,
    "title": "<punchy viral title>",
    "hook_text": "<first spoken words that grab attention>",
    "summary": "<one sentence what happens>",
    "factor_scores": {{
      "hook_strength": <0-100>,
      "novelty": <0-100>,
      "emotional_resonance": <0-100>,
      "controversy": <0-100>,
      "story_arc": <0-100>,
      "standalone_coherence": <0-100>,
      "humor": <0-100>,
      "surprise": <0-100>,
      "quotability": <0-100>
    }},
    "rationale": "<why this clip will keep viewers watching>",
    "suggested_broll_topics": ["<b-roll idea 1>", "<b-roll idea 2>"],
    "tags": ["#topic1", "#topic2"]
  }}
]"""

        models_to_try = [self.model_name] + [m for m in getattr(Config, "GEMINI_FALLBACK_MODELS", []) if m != self.model_name]
        response = None
        last_err = None
        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=prompt,
                )
                if response and response.text:
                    break
            except Exception as me:
                last_err = me
                continue
        if not response or not response.text:
            raise last_err or RuntimeError("No response from Gemini")

        raw_json = _clean_json_str(response.text)
        data = json.loads(raw_json)

        candidates = []
        for i, item in enumerate(data):
            st = float(item["start_time"])
            et = float(item["end_time"])
            dur = et - st
            if dur < min_duration * 0.7 or dur > max_duration * 1.3:
                continue

            fs = item.get("factor_scores", {})
            # Calculate weighted viral score
            viral_score = sum(
                float(fs.get(k, 50.0)) * weight
                for k, weight in self.WEIGHTS.items()
            )

            candidates.append(ClipCandidate(
                id=f"clip_{i+1:02d}",
                start_time=st,
                end_time=et,
                duration=dur,
                title=item.get("title", f"Clip #{i+1}"),
                hook_text=item.get("hook_text", ""),
                summary=item.get("summary", ""),
                viral_score=viral_score,
                factor_scores=fs,
                rationale=item.get("rationale", ""),
                suggested_broll_topics=item.get("suggested_broll_topics", []),
                tags=item.get("tags", []),
                recommended_aspect_ratio="9:16",
            ))

        # Sort by viral score descending
        candidates.sort(key=lambda c: c.viral_score, reverse=True)
        return candidates[:target_clip_count]

    def _detect_algorithmic(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        target_clip_count: int = 5,
        min_duration: float = 25.0,
        max_duration: float = 75.0,
    ) -> List[ClipCandidate]:
        """Algorithmic multi-factor sliding window scanner with Non-Maximum Suppression."""
        if not segments:
            return []

        # If total video is already within short duration, return the entire clip
        if video_duration <= max_duration:
            hook_text = segments[0]["text"][:60] if segments else ""
            return [ClipCandidate(
                id="clip_01",
                start_time=0.0,
                end_time=video_duration,
                duration=video_duration,
                title="Full Video Master",
                hook_text=hook_text,
                summary="Complete video selected as primary short.",
                viral_score=85.0,
                factor_scores={k: 80.0 for k in self.WEIGHTS},
                rationale="Source video is already optimized for short-form duration.",
                suggested_broll_topics=["highlight", "reaction", "key_moment"],
                tags=["#viral", "#short"],
            )]

        raw_candidates = []
        n_segs = len(segments)

        # Slide through segments to find viable start/end intervals
        for i in range(n_segs):
            start_seg = segments[i]
            st = start_seg["start"]

            # Hook score for the first segment
            hook_text = start_seg["text"]
            hook_score = self._score_hook_heuristics(hook_text)

            current_text = []
            for j in range(i, n_segs):
                end_seg = segments[j]
                et = end_seg["end"]
                dur = et - st
                current_text.append(end_seg["text"])

                if dur < min_duration:
                    continue
                if dur > max_duration:
                    break

                # Check if end_seg ends cleanly (period, exclamation, question mark)
                last_char = end_seg["text"].strip()[-1:] if end_seg["text"].strip() else ""
                is_sentence_boundary = last_char in {".", "!", "?"}

                # Evaluate window candidate
                full_clip_text = " ".join(current_text)
                factor_scores = self._score_text_heuristics(full_clip_text, hook_score, is_sentence_boundary, dur)

                # Weighted viral score
                viral_score = sum(factor_scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)

                title = self._generate_heuristic_title(full_clip_text)

                raw_candidates.append({
                    "start_time": st,
                    "end_time": et,
                    "duration": dur,
                    "title": title,
                    "hook_text": hook_text[:80],
                    "summary": full_clip_text[:140] + "...",
                    "viral_score": viral_score,
                    "factor_scores": factor_scores,
                    "rationale": f"High hook score ({hook_score:.0f}/100) with solid narrative pacing.",
                })

        # Sort all windows by viral score
        raw_candidates.sort(key=lambda x: x["viral_score"], reverse=True)

        # Apply Non-Maximum Suppression (NMS) to eliminate heavy overlaps (>20s overlap)
        selected: List[ClipCandidate] = []
        for cand in raw_candidates:
            if len(selected) >= target_clip_count:
                break

            overlap = False
            for sel in selected:
                # Calculate intersection
                inter_st = max(cand["start_time"], sel.start_time)
                inter_et = min(cand["end_time"], sel.end_time)
                if inter_et > inter_st:
                    overlap_dur = inter_et - inter_st
                    # If overlapping more than 15s or 35% of either, reject
                    if overlap_dur > 15.0 or (overlap_dur / cand["duration"]) > 0.35:
                        overlap = True
                        break

            if not overlap:
                selected.append(ClipCandidate(
                    id=f"clip_{len(selected)+1:02d}",
                    start_time=cand["start_time"],
                    end_time=cand["end_time"],
                    duration=cand["duration"],
                    title=cand["title"],
                    hook_text=cand["hook_text"],
                    summary=cand["summary"],
                    viral_score=cand["viral_score"],
                    factor_scores=cand["factor_scores"],
                    rationale=cand["rationale"],
                    suggested_broll_topics=["context", "reaction", "action"],
                    tags=["#shorts", "#clip"],
                    recommended_aspect_ratio="9:16",
                ))

        return selected

    def _score_hook_heuristics(self, text: str) -> float:
        """Score hook strength (0 to 100) based on curiosity, questions, and punchiness."""
        score = 50.0
        text_lower = text.lower().strip()

        # Questions create curiosity gaps
        if "?" in text:
            score += 18.0

        # High curiosity openers
        curiosity_triggers = [
            "the reason why", "nobody knows", "secret", "never", "always",
            "what happened", "the truth about", "i realized", "most people think",
            "everyone said", "crazy", "insane", "million", "billion", "ranked",
            "biggest mistake", "number one", "first time", "you won't believe"
        ]
        for trigger in curiosity_triggers:
            if trigger in text_lower:
                score += 12.0
                break

        # Exclamations or intense words
        if "!" in text or any(w in text_lower for w in ["insane", "crazy", "wild", "worst", "best"]):
            score += 10.0

        # Numbers or rankings attract clicks
        if re.search(r"\b\d+\b", text):
            score += 8.0

        # Short punchy opener
        word_count = len(text.split())
        if 4 <= word_count <= 12:
            score += 6.0

        return min(98.0, max(25.0, score))

    def _score_text_heuristics(
        self,
        text: str,
        hook_score: float,
        is_sentence_boundary: bool,
        duration: float,
    ) -> Dict[str, float]:
        """Compute the 9 viral factor scores heuristically."""
        text_lower = text.lower()
        words = text.split()
        word_count = len(words)
        wps = word_count / max(1.0, duration)

        # Novelty / Information
        has_stats = bool(re.search(r"\b\d+%\b|\$\d+|\b\d+\b", text))
        novelty = 65.0 + (15.0 if has_stats else 0.0)

        # Emotion
        emotional_words = ["love", "hate", "scared", "dream", "killed", "won", "lost", "passion", "crying", "tears", "angry"]
        emo_matches = sum(1 for w in emotional_words if w in text_lower)
        emotional_resonance = min(95.0, 55.0 + emo_matches * 10.0)

        # Controversy
        debate_words = ["disagree", "wrong", "bullshit", "fake", "lie", "trash", "overrated", "underrated", "argument"]
        controversy = min(95.0, 50.0 + sum(12.0 for w in debate_words if w in text_lower))

        # Story arc & Standalone coherence
        story_arc = 60.0 + (20.0 if is_sentence_boundary else 0.0)
        coherence = 65.0 + (15.0 if is_sentence_boundary else -10.0)

        # Humor
        humor_words = ["laugh", "funny", "joke", "ridiculous", "hilarious", "lol", "crap"]
        humor = min(90.0, 45.0 + sum(15.0 for w in humor_words if w in text_lower))

        # Surprise
        surprise_words = ["suddenly", "actually", "plot twist", "shocking", "unexpected", "turned out"]
        surprise = min(90.0, 50.0 + sum(15.0 for w in surprise_words if w in text_lower))

        # Quotability
        quotability = min(95.0, 55.0 + (15.0 if "!" in text else 0.0))

        return {
            "hook_strength": hook_score,
            "novelty": min(95.0, novelty),
            "emotional_resonance": emotional_resonance,
            "controversy": controversy,
            "story_arc": min(95.0, story_arc),
            "standalone_coherence": min(95.0, coherence),
            "humor": humor,
            "surprise": surprise,
            "quotability": quotability,
        }

    def _generate_heuristic_title(self, text: str) -> str:
        """Create a punchy viral title from first clause or key phrase."""
        first_sentence = re.split(r"[.!?]", text)[0].strip()
        words = first_sentence.split()
        if len(words) <= 7:
            return first_sentence.title()
        return " ".join(words[:6]).title() + "..."


# Global instance
clip_detector = ClipDetectionService()
