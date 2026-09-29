"""Editorial Moment Map Analyzer.

Analyzes raw speech transcript segments into sequential, semantically rich EditorialMoments
with narrative roles, emotional sentiment, information density, visual opportunity, and pacing requirements.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.services.editorial.types import (
    EditorialMoment,
    NarrativeRole,
    PacingCategory,
    SentimentCategory,
)

logger = logging.getLogger("autopilot.editorial.moment")


class MomentAnalyzer:
    """Deconstructs speech transcripts into structured editorial moments."""

    # Sentiment lexicons
    NEGATIVE_WORDS = {
        "loss", "lost", "fail", "failed", "failure", "decline", "crash", "crashed",
        "drop", "dropped", "disaster", "problem", "mistake", "debt", "stress",
        "damage", "broke", "ruined", "fired", "worst", "terrible", "horrible",
        "scam", "trap", "bankrupt", "blew", "pain", "hurt", "suffer", "died",
    }
    POSITIVE_WORDS = {
        "win", "won", "winning", "success", "successful", "gain", "gained", "grow",
        "growth", "profit", "profitable", "victory", "champion", "amazing",
        "brilliant", "celebrate", "best", "boom", "booming", "wealth", "fortune",
        "breakthrough", "conquered", "mastered", "surpassed", "record",
    }
    TENSION_WORDS = {
        "risk", "risky", "danger", "dangerous", "pressure", "panic", "fear",
        "critical", "deadline", "threat", "conflict", "fight", "tension", "intense",
        "suspended", "uncertain", "stakes", "gamble", "edge", "collapse",
    }
    REFLECTIVE_WORDS = {
        "realize", "realized", "wonder", "perspective", "silence", "journey",
        "meaning", "human", "soul", "quiet", "reflect", "ponder", "wisdom",
        "lesson", "deeply", "peace", "truth", "values", "understand",
    }
    FUNNY_WORDS = {
        "joke", "hilarious", "laugh", "laughing", "ridiculous", "absurd", "meme",
        "clown", "dumb", "wild", "funny", "comedic", "comedy", "lmao", "crazy",
    }
    TECHNICAL_WORDS = {
        "api", "code", "algorithm", "server", "database", "architecture",
        "framework", "specs", "parameters", "system", "neural", "gpu", "latency",
        "cpu", "software", "hardware", "token", "model", "pipeline", "function",
    }

    # Action detection verbs
    ACTION_PATTERNS = [
        (r"\b(buy|buying|bought|purchas\w*|invest\w*)\b", "buying / investing"),
        (r"\b(sell|selling|sold|liquidat\w*)\b", "selling / liquidating"),
        (r"\b(run|running|ran|sprint\w*)\b", "running / moving fast"),
        (r"\b(work|working|worked|build\w*|cod\w*|engineer\w*)\b", "working / building"),
        (r"\b(sign|signing|signed|clos\w*\s+deal)\b", "signing contract / closing deal"),
        (r"\b(shoot|shooting|shot|scor\w*)\b", "shooting / scoring"),
        (r"\b(look|looking|watch\w*|inspect\w*|examin\w*)\b", "inspecting / analyzing"),
        (r"\b(talk|talking|spoke|speak\w*|discuss\w*)\b", "speaking / negotiating"),
        (r"\b(driv\w*|dropp\w*|fly\w*|travel\w*)\b", "traveling / in transit"),
        (r"\b(fight\w*|argu\w*|conflict\w*)\b", "conflict / competing"),
    ]

    def analyze_transcript(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float,
    ) -> List[EditorialMoment]:
        """Convert a list of transcript segments into a cohesive editorial moment map."""
        if not transcript_segments:
            return []

        # 1. Group segments into granular editorial moments (3s to 8s target)
        grouped_chunks = self._group_segments(transcript_segments)
        total_chunks = len(grouped_chunks)

        moments: List[EditorialMoment] = []

        for idx, chunk in enumerate(grouped_chunks):
            st = chunk[0].get("start", 0.0)
            et = chunk[-1].get("end", 0.0)
            dur = max(0.5, et - st)
            text = " ".join(s.get("text", "").strip() for s in chunk).strip()
            all_words = []
            for s in chunk:
                all_words.extend(s.get("words", []))

            # Derive attributes
            sentiment = self._detect_sentiment(text)
            intensity = self._calculate_emotional_intensity(text, chunk, dur)
            emphasis = self._detect_speaker_emphasis(text)
            entities = self._extract_entities(text)
            action = self._detect_action(text)
            topic = self._extract_topic(text, entities)

            # Determine narrative role based on sequence and textual signals
            role = self._determine_narrative_role(idx, total_chunks, text, intensity, entities)

            # Calculate information density (words/second + entity density)
            words_count = len(text.split())
            wps = words_count / max(1.0, dur)
            density = min(1.0, max(0.1, (wps / 4.0) * 0.7 + (len(entities) / 4.0) * 0.3))

            # Visual opportunity: concrete physical things get higher visual opportunity
            vis_opp = self._calculate_visual_opportunity(text, entities, action, sentiment)

            # Pacing and recommended duration
            pacing_cat, rec_dur = self._calculate_pacing(role, sentiment, intensity, density)

            # Cognitive load for the viewer
            processing_load = min(1.0, max(0.2, density * 0.6 + intensity * 0.4))

            # Editorial energy curve level
            energy_level = self._compute_moment_energy(idx, total_chunks, role, intensity)

            moment = EditorialMoment(
                moment_id=f"moment_{idx+1:02d}",
                start_time=st,
                end_time=et,
                duration=dur,
                text=text,
                words=all_words,
                semantic_topic=topic,
                entities=entities,
                action=action,
                sentiment=sentiment,
                emotional_intensity=intensity,
                speaker_emphasis=emphasis,
                narrative_role=role,
                information_density=density,
                visual_opportunity=vis_opp,
                pacing_requirement=pacing_cat,
                recommended_duration=rec_dur,
                visual_processing_load=processing_load,
                energy_level=energy_level,
            )
            moments.append(moment)

        logger.info(f"MomentAnalyzer partitioned transcript into {len(moments)} editorial moments.")
        return moments

    def _group_segments(self, segments: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group raw Whisper segments into cohesive 3.0s - 7.5s moments."""
        groups: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []
        curr_dur = 0.0

        for seg in segments:
            dur = max(0.1, seg.get("end", 0.0) - seg.get("start", 0.0))
            text = seg.get("text", "").strip()

            if not current:
                current.append(seg)
                curr_dur = dur
                continue

            # Check if current group already has sufficient duration and ends with sentence punctuation
            has_terminal_punct = bool(re.search(r"[.?!]$", current[-1].get("text", "").strip()))
            if curr_dur >= 3.0 and has_terminal_punct:
                groups.append(current)
                current = [seg]
                curr_dur = dur
            elif curr_dur + dur > 7.5:
                # Force split to avoid overly long moments
                groups.append(current)
                current = [seg]
                curr_dur = dur
            else:
                current.append(seg)
                curr_dur += dur

        if current:
            groups.append(current)

        return groups

    def _detect_sentiment(self, text: str) -> SentimentCategory:
        """Classify emotional polarity and narrative mood."""
        text_lower = text.lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", text_lower))

        neg_matches = len(words.intersection(self.NEGATIVE_WORDS))
        pos_matches = len(words.intersection(self.POSITIVE_WORDS))
        ten_matches = len(words.intersection(self.TENSION_WORDS))
        ref_matches = len(words.intersection(self.REFLECTIVE_WORDS))
        fun_matches = len(words.intersection(self.FUNNY_WORDS))
        tech_matches = len(words.intersection(self.TECHNICAL_WORDS))

        scores = [
            (neg_matches, SentimentCategory.NEGATIVE),
            (pos_matches, SentimentCategory.POSITIVE),
            (ten_matches, SentimentCategory.TENSION),
            (ref_matches, SentimentCategory.REFLECTIVE),
            (fun_matches, SentimentCategory.FUNNY),
            (tech_matches, SentimentCategory.TECHNICAL),
        ]
        scores.sort(key=lambda x: x[0], reverse=True)

        if scores[0][0] > 0:
            return scores[0][1]
        return SentimentCategory.NEUTRAL

    def _calculate_emotional_intensity(
        self, text: str, chunk: List[Dict[str, Any]], duration: float
    ) -> float:
        """Score emotional arousal and delivery energy (0.0 to 1.0)."""
        score = 0.5
        text_lower = text.lower()

        # Exclamations
        if "!" in text:
            score += 0.20
        # High arousal words
        if any(w in text_lower for w in ["insane", "crazy", "unbelievable", "shocking", "wild", "worst", "best"]):
            score += 0.20
        # High speech velocity indicates intensity
        word_count = len(text.split())
        wps = word_count / max(1.0, duration)
        if wps >= 3.2:
            score += 0.15
        elif wps < 1.8:
            score -= 0.10

        return min(1.0, max(0.1, score))

    def _detect_speaker_emphasis(self, text: str) -> float:
        """Detect rhetorical or auditory emphasis in spoken words."""
        emphasis = 0.4
        words = text.split()
        for w in words:
            if len(w) > 1 and w.isupper() and w not in ["A", "I"]:
                emphasis += 0.25
                break
        if any(w.lower() in ["never", "always", "absolutely", "exactly", "literally", "crucial"] for w in words):
            emphasis += 0.20
        return min(1.0, emphasis)

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key named entities, figures, and concepts."""
        entities = []
        # Dollar amounts
        money = re.findall(r"\$\d+(?:\.\d+)?(?:\s*(?:million|billion|k|m))?", text, re.IGNORECASE)
        entities.extend(money)
        # Percentages
        pcts = re.findall(r"\b\d+%\b", text)
        entities.extend(pcts)
        # Capitalized proper nouns
        proper = re.findall(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b", text)
        for p in proper:
            if p.lower() not in ["the", "this", "that", "there", "they", "when", "what", "where"]:
                entities.append(p)
        return list(dict.fromkeys(entities))[:5]

    def _detect_action(self, text: str) -> str:
        """Detect physical or transactional action described in the moment."""
        for pattern, action_name in self.ACTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return action_name
        return "explaining concept"

    def _extract_topic(self, text: str, entities: List[str]) -> str:
        """Extract a 2-4 word semantic topic label."""
        if entities:
            return " / ".join(entities[:2])
        words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", text) if w.lower() not in ["have", "with", "from", "that", "this"]]
        if words:
            return " ".join(words[:3]).title()
        return "Topic Focus"

    def _determine_narrative_role(
        self,
        index: int,
        total: int,
        text: str,
        intensity: float,
        entities: List[str],
    ) -> NarrativeRole:
        """Determine the narrative function of this moment."""
        text_lower = text.lower()

        # Opening moment
        if index == 0:
            return NarrativeRole.HOOK

        # Closing moment
        if index == total - 1:
            if any(w in text_lower for w in ["subscribe", "follow", "comment", "link", "check out", "watch"]):
                return NarrativeRole.CTA
            return NarrativeRole.PAYOFF

        # Statistical claim
        if any(re.search(r"(\$\d+|\b\d+%\b|\b\d+\s*million\b)", e) for e in entities):
            return NarrativeRole.STATISTIC

        # Strong claim or revelation
        if any(w in text_lower for w in ["the truth is", "suddenly", "actually", "turned out", "realized"]):
            return NarrativeRole.REVEAL

        # Contrast
        if any(text_lower.startswith(w) or f" {w} " in text_lower for w in ["but", "however", "on the other hand", "unlike"]):
            return NarrativeRole.CONTRAST

        # Example or Story
        if any(w in text_lower for w in ["for example", "like when", "case in point", "one time", "imagine"]):
            return NarrativeRole.EXAMPLE
        if any(w in text_lower for w in ["i remember", "he walked", "years ago", "back in"]):
            return NarrativeRole.STORY

        # Emotional reaction
        if intensity >= 0.8 and any(w in text_lower for w in ["crazy", "insane", "oh my", "no way", "wild"]):
            return NarrativeRole.REACTION

        # Core claim vs explanation
        if any(w in text_lower for w in ["because", "which means", "the way it works", "how you", "in order to"]):
            return NarrativeRole.EXPLANATION
        if any(w in text_lower for w in ["is the biggest", "will never", "must always", "the key is"]):
            return NarrativeRole.CLAIM

        # Penultimate climax
        if index >= total - 2:
            return NarrativeRole.PAYOFF

        # Default middle moments
        return NarrativeRole.EXPLANATION if index % 2 == 1 else NarrativeRole.SETUP

    def _calculate_visual_opportunity(
        self, text: str, entities: List[str], action: str, sentiment: SentimentCategory
    ) -> float:
        """Score how well this moment can be enhanced with B-roll (0.0 to 1.0)."""
        score = 0.5
        # Concrete actions and named entities have high visual opportunity
        if action != "explaining concept":
            score += 0.25
        if entities:
            score += 0.20
        # Technical, financial, or intense emotional moments benefit from visual cutaways
        if sentiment in [SentimentCategory.NEGATIVE, SentimentCategory.POSITIVE, SentimentCategory.TECHNICAL]:
            score += 0.15
        return min(1.0, score)

    def _calculate_pacing(
        self,
        role: NarrativeRole,
        sentiment: SentimentCategory,
        intensity: float,
        density: float,
    ) -> Tuple[PacingCategory, float]:
        """Calculate adaptive pacing and recommended clip duration based on cognitive load."""
        if intensity >= 0.75 or role == NarrativeRole.HOOK:
            return PacingCategory.HIGH_ENERGY, 2.5
        if sentiment == SentimentCategory.REFLECTIVE or role == NarrativeRole.STORY:
            return PacingCategory.REFLECTIVE, 6.5
        if role in [NarrativeRole.EXPLANATION, NarrativeRole.EXAMPLE] and density >= 0.65:
            return PacingCategory.DEEP_EXPLANATION, 4.5
        return PacingCategory.NORMAL, 3.5

    def _compute_moment_energy(
        self, index: int, total: int, role: NarrativeRole, intensity: float
    ) -> float:
        """Compute the macro editorial energy curve level (0.0 to 1.0)."""
        if role == NarrativeRole.HOOK:
            return 0.90
        if role in [NarrativeRole.REVEAL, NarrativeRole.PAYOFF]:
            return 0.92
        if role in [NarrativeRole.STATISTIC, NarrativeRole.CLAIM]:
            return 0.82
        if role == NarrativeRole.CTA:
            return 0.75
        if role == NarrativeRole.SETUP:
            return 0.50

        # Sine-wave progression for rhythm and contrast
        base_rhythm = 0.55 + 0.25 * ((index % 3) / 2.0)
        return min(1.0, max(0.3, base_rhythm * 0.7 + intensity * 0.3))
