"""Niche Detection and Content Understanding Services.

Analyzes transcripts and metadata to automatically determine content niche,
visual themes, speaker entities, and high-impact moments.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.niches import niche_registry, NicheProfile
from ai_broll_autopilot.styles import style_registry

logger = logging.getLogger(__name__)


@dataclass
class NicheDetectionResult:
    """Result of automated niche classification."""
    niche_id: str
    niche_name: str
    confidence: float
    detected_keywords: List[str] = field(default_factory=list)
    suggested_style_id: str = "clean_podcast"
    secondary_niches: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "niche_id": self.niche_id,
            "niche_name": self.niche_name,
            "confidence": round(self.confidence, 3),
            "detected_keywords": self.detected_keywords,
            "suggested_style_id": self.suggested_style_id,
            "secondary_niches": self.secondary_niches,
            "explanation": self.explanation,
        }


@dataclass
class ContentAnalysisResult:
    """Structured understanding of long-form or clip content."""
    title: str
    summary: str
    core_topics: List[str] = field(default_factory=list)
    speakers: List[str] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    high_energy_moments: List[Dict[str, Any]] = field(default_factory=list)
    tone: str = "conversational"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "core_topics": self.core_topics,
            "speakers": self.speakers,
            "key_entities": self.key_entities,
            "high_energy_moments": self.high_energy_moments,
            "tone": self.tone,
        }


def _clean_json_str(text: str) -> str:
    """Strip markdown fencing from LLM json responses."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# Suggested default style mappings per niche
NICHE_TO_STYLE_MAP = {
    "sports_basketball": "sports_editorial",
    "sports": "sports_editorial",
    "business_startup": "business_editorial",
    "finance": "business_editorial",
    "tech_ai": "clean_podcast",
    "gaming": "gaming_fast",
    "comedy": "gaming_fast",
    "education": "clean_podcast",
    "fitness": "sports_editorial",
    "law": "business_editorial",
    "news": "news_editorial",
    "generic": "clean_podcast",
}


class NicheDetectionService:
    """Detects content niche using LLM analysis with robust heuristic fallback."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    async def detect_niche(
        self,
        transcript_text: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NicheDetectionResult:
        """Classify video content into a registered niche profile.

        Args:
            transcript_text: Full or sampled transcript text.
            title: Optional title of the video or episode.
            metadata: Optional extra metadata (tags, channel name, description).

        Returns:
            NicheDetectionResult with primary niche, confidence, and keyword evidence.
        """
        combined_text = f"Title: {title or ''}\n\nTranscript:\n{transcript_text[:5000]}"
        if metadata and "description" in metadata:
            combined_text += f"\nDescription: {metadata['description'][:1000]}"

        # Attempt LLM detection if client available
        if self.client:
            try:
                return await self._detect_with_llm(combined_text)
            except Exception as e:
                logger.warning(f"LLM niche detection failed: {e}. Falling back to heuristic classifier.")

        # Deterministic Heuristic Fallback
        return self._detect_heuristic(transcript_text, title=title, metadata=metadata)

    async def _detect_with_llm(self, text: str) -> NicheDetectionResult:
        """Use Gemini to perform nuanced niche classification."""
        available_niches = [
            {"id": p.id, "name": p.name, "parent": p.parent_niche, "description": p.description}
            for p in niche_registry.list_profiles()
        ]

        prompt = f"""You are an expert video content classifier.
Analyze the following video transcript/metadata and classify it into the best matching content niche from the available list:

Available Niches:
{json.dumps(available_niches, indent=2)}

Content to classify:
{text}

Respond ONLY with valid JSON matching this schema:
{{
  "niche_id": "<one of the valid niche IDs from the list>",
  "confidence": <float between 0.0 and 1.0>,
  "detected_keywords": ["<key visual/topical terms found in text>"],
  "secondary_niches": [
    {{"niche_id": "<secondary id>", "confidence": <float>}}
  ],
  "explanation": "<one sentence explanation of why this niche was selected>"
}}"""

        models_to_try = [self.model_name] + [m for m in getattr(Config, "GEMINI_FALLBACK_MODELS", []) if m != self.model_name]
        response = None
        last_err = None
        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=1),
                            timeout=15000,
                        )
                    )
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

        niche_id = data.get("niche_id", "generic")
        profile = niche_registry.get_profile(niche_id)
        suggested_style = NICHE_TO_STYLE_MAP.get(profile.id, "clean_podcast")

        return NicheDetectionResult(
            niche_id=profile.id,
            niche_name=profile.name,
            confidence=float(data.get("confidence", 0.8)),
            detected_keywords=data.get("detected_keywords", []),
            suggested_style_id=suggested_style,
            secondary_niches=data.get("secondary_niches", []),
            explanation=data.get("explanation", f"Matched niche '{profile.name}' based on content analysis."),
        )

    def _detect_heuristic(
        self,
        transcript_text: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NicheDetectionResult:
        """Deterministic keyword-density & category matching classifier."""
        full_text = f"{title or ''} {transcript_text} "
        if metadata:
            full_text += f"{metadata.get('description', '')} {' '.join(metadata.get('tags', []))}"
        full_text_lower = full_text.lower()
        words_in_text = set(re.findall(r"\b[a-z]{3,}\b", full_text_lower))

        profiles = niche_registry.list_profiles()
        scores: Dict[str, Dict[str, Any]] = {}

        for profile in profiles:
            if profile.id == "generic":
                continue

            matched_keywords = []
            score = 0

            # Match visual keywords
            for kw in profile.visual_keywords:
                kw_lower = kw.lower()
                if " " in kw_lower:
                    count = full_text_lower.count(kw_lower)
                    if count > 0:
                        score += count * 3
                        matched_keywords.append(kw)
                elif kw_lower in words_in_text:
                    count = full_text_lower.count(kw_lower)
                    score += count * 2
                    matched_keywords.append(kw)

            # Match B-roll categories
            for cat in profile.broll_categories:
                clean_cat = cat.lower().replace("_", " ")
                if clean_cat in full_text_lower:
                    score += 2
                    if clean_cat not in matched_keywords:
                        matched_keywords.append(clean_cat)

            # Match profile name words
            for name_word in profile.name.lower().split():
                if len(name_word) > 3 and name_word in words_in_text:
                    score += 3

            scores[profile.id] = {
                "profile": profile,
                "score": score,
                "matched_keywords": matched_keywords,
            }

        sorted_scores = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

        if not sorted_scores or sorted_scores[0]["score"] == 0:
            generic_profile = niche_registry.get_profile("generic")
            return NicheDetectionResult(
                niche_id="generic",
                niche_name=generic_profile.name,
                confidence=0.5,
                detected_keywords=[],
                suggested_style_id="clean_podcast",
                secondary_niches=[],
                explanation="No specific domain keywords identified with high confidence; defaulted to generic.",
            )

        top = sorted_scores[0]
        top_profile: NicheProfile = top["profile"]
        top_score = top["score"]

        # Calculate confidence metric
        total_score = sum(s["score"] for s in sorted_scores)
        confidence = min(0.98, max(0.40, top_score / (total_score + 1e-5)))

        # Compile secondary niches
        secondary = []
        for s in sorted_scores[1:4]:
            if s["score"] > 0:
                secondary.append({
                    "niche_id": s["profile"].id,
                    "confidence": round(s["score"] / (total_score + 1e-5), 2),
                })

        suggested_style = NICHE_TO_STYLE_MAP.get(top_profile.id, "clean_podcast")

        return NicheDetectionResult(
            niche_id=top_profile.id,
            niche_name=top_profile.name,
            confidence=confidence,
            detected_keywords=top["matched_keywords"][:12],
            suggested_style_id=suggested_style,
            secondary_niches=secondary,
            explanation=f"Detected {len(top['matched_keywords'])} topical keywords matching {top_profile.name}.",
        )


class ContentUnderstandingService:
    """Analyzes transcript segments to extract narrative structure, key entities, and dynamics."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    async def analyze_content(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentAnalysisResult:
        """Perform comprehensive content analysis on speech segments."""
        full_text = " ".join([seg.get("text", "") for seg in transcript_segments])

        if self.client and len(transcript_segments) > 0:
            try:
                return await self._analyze_with_llm(transcript_segments, video_metadata)
            except Exception as e:
                logger.warning(f"LLM content understanding failed: {e}. Falling back to heuristic analysis.")

        return self._analyze_heuristic(transcript_segments, video_metadata)

    async def _analyze_with_llm(
        self,
        segments: List[Dict[str, Any]],
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentAnalysisResult:
        """LLM-assisted extraction of topics, speakers, and emotional peaks."""
        sample_segments = [
            f"[{s['start']:.1f}s - {s['end']:.1f}s] {s.get('speaker', '')}: {s['text']}"
            for s in segments[:100]
        ]
        segments_str = "\n".join(sample_segments)

        prompt = f"""You are an executive video editor.
Analyze the following transcript excerpt from a video/podcast:

{segments_str}

Extract the structural elements and return ONLY JSON matching:
{{
  "title": "<punchy, descriptive working title for this clip/episode>",
  "summary": "<2-3 sentence core summary of what is discussed>",
  "core_topics": ["<3-6 primary topics or concepts>"],
  "speakers": ["<names or roles of speaking parties>"],
  "key_entities": ["<names of people, teams, companies, tools, products mentioned>"],
  "high_energy_moments": [
    {{"start": <seconds>, "end": <seconds>, "reason": "<why this moment is intense, surprising, or high-value>"}}
  ],
  "tone": "<conversational | energetic | controversial | educational | humorous>"
}}"""

        models_to_try = [self.model_name] + [m for m in getattr(Config, "GEMINI_FALLBACK_MODELS", []) if m != self.model_name]
        response = None
        last_err = None
        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=1),
                            timeout=15000,
                        )
                    )
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

        return ContentAnalysisResult(
            title=data.get("title", video_metadata.get("title", "Untitled Episode") if video_metadata else "Untitled Episode"),
            summary=data.get("summary", ""),
            core_topics=data.get("core_topics", []),
            speakers=data.get("speakers", []),
            key_entities=data.get("key_entities", []),
            high_energy_moments=data.get("high_energy_moments", []),
            tone=data.get("tone", "conversational"),
        )

    def _analyze_heuristic(
        self,
        segments: List[Dict[str, Any]],
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentAnalysisResult:
        """Rule-based entity and moment extractor."""
        full_text = " ".join([seg.get("text", "") for seg in segments])
        title = (video_metadata or {}).get("title", "Speech Analysis")

        # Extract entities via Capitalized sequences
        words = full_text.split()
        entities = set()
        for i, w in enumerate(words):
            clean_w = re.sub(r"[^\w]", "", w)
            if clean_w and clean_w[0].isupper() and len(clean_w) > 2:
                # Check for 2-word proper noun
                if i + 1 < len(words):
                    next_w = re.sub(r"[^\w]", "", words[i + 1])
                    if next_w and next_w[0].isupper():
                        entities.add(f"{clean_w} {next_w}")
                        continue
                if clean_w.lower() not in {"the", "and", "but", "what", "this", "they", "then", "there", "when"}:
                    entities.add(clean_w)

        # High energy moments (exclamations, questions, fast speech rate)
        high_energy = []
        speakers = set()
        for seg in segments:
            text = seg.get("text", "")
            if seg.get("speaker"):
                speakers.add(seg["speaker"])
            dur = max(0.1, seg.get("end", 0) - seg.get("start", 0))
            words_count = len(text.split())
            wps = words_count / dur  # words per second

            if "!" in text or wps > 3.8:
                high_energy.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "reason": "Rapid speech or emphatic delivery" if wps > 3.8 else "Emphatic statement",
                })

        summary = full_text[:200] + "..." if len(full_text) > 200 else full_text

        return ContentAnalysisResult(
            title=title,
            summary=summary,
            core_topics=list(entities)[:5],
            speakers=list(speakers) or ["Host", "Guest"],
            key_entities=list(entities)[:10],
            high_energy_moments=high_energy[:8],
            tone="conversational",
        )


# Global instances
niche_detector = NicheDetectionService()
content_analyzer = ContentUnderstandingService()
