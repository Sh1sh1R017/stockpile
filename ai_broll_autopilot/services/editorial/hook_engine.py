"""Hook Detection and Retention Scoring Engine.

Generates multiple hook candidates from contiguous transcript segments across the entire source,
scores each using multi-dimensional viral/retention criteria and penalties, evaluates retention
purpose, and tightens phrasing while preserving grammatical integrity.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.services.editorial.types import (
    HookCandidate,
    HookScoreBreakdown,
)

logger = logging.getLogger("autopilot.editorial.hook")


class HookEngine:
    """Intelligent Hook Detection, Scoring, and Retention Optimization Engine."""

    # Opening greetings and small-talk patterns
    GREETINGS_PATTERN = re.compile(
        r"^(hey\s+(guys|everyone|y'all|there)?|hello\s+(everybody)?|hi\s+(guys)?|what'?s\s+up|welcome\s+back|good\s+(morning|afternoon|evening))\b",
        re.IGNORECASE,
    )
    # Channel and speaker introductions
    INTROS_PATTERN = re.compile(
        r"\b(my\s+name\s+is|i'?m\s+(joined\s+by|here\s+with)|welcome\s+to\s+the\s+show|in\s+this\s+episode|in\s+this\s+podcast)\b",
        re.IGNORECASE,
    )
    # Generic announcement setups
    ANNOUNCEMENT_PATTERN = re.compile(
        r"\b(today\s+we('?re|\s+are)\s+(going\s+to|talking\s+about)|in\s+this\s+video\s+we|i\s+want\s+to\s+talk\s+about)\b",
        re.IGNORECASE,
    )
    # Preamble filler phrases
    PREAMBLE_FILLER_PATTERN = re.compile(
        r"^(so\s+basically|you\s+know\s+what|the\s+thing\s+is|like\s+i\s+said|honestly\s+speaking|look|listen|well|so)\s*,?\s*",
        re.IGNORECASE,
    )

    # High-curiosity gap triggers
    CURIOSITY_TRIGGERS = [
        "the reason why", "nobody knows", "secret", "never", "always",
        "what happened", "the truth about", "i realized", "most people think",
        "everyone said", "crazy", "insane", "million", "billion", "ranked",
        "biggest mistake", "number one", "first time", "you won't believe",
        "here is why", "the problem with", "the dark side", "nobody talks about",
        "is a lie", "is dead", "waste of money", "changed everything",
    ]

    # Emotional intensity tokens
    INTENSITY_WORDS = [
        "insane", "crazy", "wild", "worst", "best", "terrible", "incredible",
        "destroyed", "blew up", "shocking", "brutal", "horrifying", "miracle",
        "disaster", "genius", "ruined", "collapsed", "exploded", "unreal",
    ]

    # Counter-intuitive strong claim triggers
    STRONG_CLAIM_TRIGGERS = [
        "is completely dead", "never buy", "always do", "biggest scam",
        "costs 10x more", "biggest lie", "waste of time", "impossible to",
        "will fail", "is a trap", "you are wrong", "everyone gets wrong",
    ]

    # Pattern interruption tokens
    SURPRISE_TRIGGERS = [
        "but actually", "turned out", "i was wrong", "suddenly", "then boom",
        "out of nowhere", "plot twist", "completely different", "except for",
    ]

    def __init__(self, min_duration: float = 2.5, max_duration: float = 12.0):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def generate_candidates(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float = 60.0,
        target_clip_interval: Optional[Tuple[float, float]] = None,
        **kwargs,
    ) -> List[HookCandidate]:
        """Generate and rank hook candidates across the full transcript."""
        if not transcript_segments:
            return []

        full_text = " ".join(s.get("text", "") for s in transcript_segments)
        candidates: List[HookCandidate] = []
        seen_texts = set()

        # Determine segment search range
        min_time = target_clip_interval[0] if target_clip_interval else 0.0
        max_time = target_clip_interval[1] if target_clip_interval else video_duration

        valid_segments = [
            s for s in transcript_segments
            if s.get("end", 0.0) >= min_time and s.get("start", 0.0) <= max_time
        ]

        if not valid_segments:
            valid_segments = transcript_segments

        # Window sliding: evaluate 1, 2, 3, and 4 contiguous segments
        n_segs = len(valid_segments)
        candidate_idx = 1

        for window_size in [1, 2, 3, 4]:
            for i in range(0, n_segs - window_size + 1):
                window = valid_segments[i : i + window_size]
                st = window[0].get("start", 0.0)
                et = window[-1].get("end", 0.0)
                dur = et - st

                if dur < self.min_duration or dur > self.max_duration:
                    continue

                raw_text = " ".join(s.get("text", "").strip() for s in window).strip()
                if not raw_text or len(raw_text.split()) < 3:
                    continue

                norm_key = re.sub(r"[^\w\s]", "", raw_text.lower())[:80]
                if norm_key in seen_texts:
                    continue
                seen_texts.add(norm_key)

                candidate = self.evaluate_candidate(
                    candidate_id=f"hook_{candidate_idx:02d}",
                    raw_text=raw_text,
                    start_time=st,
                    end_time=et,
                    duration=dur,
                    full_transcript=full_text,
                )
                candidates.append(candidate)
                candidate_idx += 1

        # Also always include the natural opening if not captured
        has_natural_start = any(c.start_time <= 1.0 for c in candidates)
        if not has_natural_start and valid_segments:
            first_two = valid_segments[: min(2, len(valid_segments))]
            st = first_two[0].get("start", 0.0)
            et = first_two[-1].get("end", 0.0)
            raw_text = " ".join(s.get("text", "").strip() for s in first_two).strip()
            if raw_text:
                candidate = self.evaluate_candidate(
                    candidate_id=f"hook_opening_natural",
                    raw_text=raw_text,
                    start_time=st,
                    end_time=et,
                    duration=et - st,
                    full_transcript=full_text,
                )
                candidates.append(candidate)

        # Sort candidates descending by final_score
        candidates.sort(key=lambda c: c.scores.final_score, reverse=True)

        # Mark top candidate as the primary opening
        if candidates:
            candidates[0].is_opening = True

        logger.info(
            f"HookEngine evaluated {len(candidates)} candidates. "
            f"Top hook ({candidates[0].scores.final_score:.1f} pts): '{candidates[0].tightened_text[:60]}...'"
        )
        return candidates

    def select_winning_hook(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float = 60.0,
        target_clip_interval: Optional[Tuple[float, float]] = None,
    ) -> Optional[HookCandidate]:
        """Select the highest-ranked hook candidate to open the video."""
        cands = self.generate_candidates(transcript_segments, video_duration, target_clip_interval)
        return cands[0] if cands else None

    def tighten_preamble(self, raw_text: str) -> Tuple[str, str]:
        """Trim filler preamble and return (tightened_text, cut_preamble)."""
        tightened = self.tighten_hook(raw_text)
        cut = ""
        m = self.PREAMBLE_FILLER_PATTERN.match(raw_text.strip())
        if m:
            cut = raw_text.strip()[: m.end()].strip()
        return tightened, cut

    def score_text(self, text: str) -> HookScoreBreakdown:
        """Evaluate raw text and return its score breakdown."""
        cand = self.evaluate_candidate(
            candidate_id="temp_eval",
            raw_text=text,
            start_time=0.0,
            end_time=3.0,
            duration=3.0,
            full_transcript=text,
        )
        return cand.scores

    def evaluate_candidate(
        self,
        candidate_id: str,
        raw_text: str,
        start_time: float,
        end_time: float,
        duration: float,
        full_transcript: str,
    ) -> HookCandidate:
        """Evaluate a contiguous speech candidate across all viral dimensions and penalties."""
        tightened_text = self.tighten_hook(raw_text)
        text_lower = tightened_text.lower()
        words = tightened_text.split()
        word_count = len(words)

        # -------------------------------------------------------------
        # 1. CURIOSITY / INFORMATION GAP (0 - 100)
        # -------------------------------------------------------------
        curiosity_score = 45.0
        if "?" in tightened_text:
            curiosity_score += 22.0
        for trigger in self.CURIOSITY_TRIGGERS:
            if trigger in text_lower:
                curiosity_score += 18.0
                break
        if any(w in text_lower for w in ["why", "how", "what if", "secret", "nobody"]):
            curiosity_score += 10.0
        curiosity_score = min(100.0, curiosity_score)

        # -------------------------------------------------------------
        # 2. EMOTIONAL INTENSITY (0 - 100)
        # -------------------------------------------------------------
        intensity_score = 40.0
        if "!" in tightened_text:
            intensity_score += 15.0
        intense_hits = [w for w in self.INTENSITY_WORDS if w in text_lower]
        intensity_score += min(35.0, len(intense_hits) * 15.0)
        # Fast delivery rate indicates high arousal/energy
        wps = word_count / max(1.0, duration)
        if wps >= 3.2:
            intensity_score += 12.0
        elif wps < 2.0:
            intensity_score -= 8.0
        intensity_score = min(100.0, max(15.0, intensity_score))

        # -------------------------------------------------------------
        # 3. SPECIFICITY (0 - 100)
        # -------------------------------------------------------------
        specificity_score = 40.0
        # Check for dollar figures or large numbers ($10M, 500,000, 20%)
        if re.search(r"(\$\d+|\b\d+%\b|\b\d+,\d+\b|\b\d+\s*(million|billion|k)\b)", text_lower):
            specificity_score += 35.0
        elif re.search(r"\b\d+\b", text_lower):
            specificity_score += 15.0
        # Check for capitalized proper entities (people, companies, cities)
        capitalized = [w for w in words[1:] if w[0].isupper() and len(w) > 2]
        if len(capitalized) >= 2:
            specificity_score += 15.0
        specificity_score = min(100.0, specificity_score)

        # -------------------------------------------------------------
        # 4. STANDALONE CONTEXT (0 - 100)
        # -------------------------------------------------------------
        standalone_score = 75.0
        # Dangling leading pronouns indicate missing antecedent
        leading_dangling = re.match(
            r"^(and\s+then\s+he|so\s+she|they\s+did|it\s+was\s+just|and\s+that|but\s+he)\b",
            raw_text.lower(),
        )
        if leading_dangling:
            standalone_score -= 30.0
        # Trailing sentence fragments
        if raw_text.rstrip().endswith(("and", "but", "so", "because", "like")):
            standalone_score -= 25.0
        standalone_score = max(20.0, standalone_score)

        # -------------------------------------------------------------
        # 5. STRONG CLAIM (0 - 100)
        # -------------------------------------------------------------
        strong_claim_score = 40.0
        for claim in self.STRONG_CLAIM_TRIGGERS:
            if claim in text_lower:
                strong_claim_score += 35.0
                break
        if any(w in text_lower for w in ["never", "always", "every", "nobody", "impossible", "lie", "dead"]):
            strong_claim_score += 15.0
        # Weak hedging penalty
        if any(w in text_lower for w in ["maybe", "perhaps", "i guess", "sort of", "kind of", "somewhat"]):
            strong_claim_score -= 20.0
        strong_claim_score = min(100.0, max(15.0, strong_claim_score))

        # -------------------------------------------------------------
        # 6. SURPRISE / PATTERN INTERRUPTION (0 - 100)
        # -------------------------------------------------------------
        surprise_score = 40.0
        for st in self.SURPRISE_TRIGGERS:
            if st in text_lower:
                surprise_score += 30.0
                break
        if any(w in text_lower for w in ["actually", "wrong", "mistake", "shocked", "truth"]):
            surprise_score += 15.0
        surprise_score = min(100.0, surprise_score)

        # -------------------------------------------------------------
        # 7. NARRATIVE IMPORTANCE (0 - 100)
        # -------------------------------------------------------------
        narrative_score = 55.0
        # Key themes repeated in full transcript get higher narrative weight
        key_words = [w.lower() for w in words if len(w) > 4 and w.lower() not in ["there", "where", "which", "about"]]
        if key_words:
            transcript_lower = full_transcript.lower()
            freq = sum(transcript_lower.count(kw) for kw in key_words[:3])
            if freq >= 5:
                narrative_score += 20.0
        narrative_score = min(100.0, narrative_score)

        # -------------------------------------------------------------
        # 8. CLARITY & PUNCHINESS (0 - 100)
        # -------------------------------------------------------------
        clarity_score = 60.0
        # Ideal short-form hook word count is 6 - 16 words
        if 6 <= word_count <= 16:
            clarity_score += 20.0
        elif word_count < 5:
            clarity_score -= 15.0
        elif word_count > 25:
            clarity_score -= 15.0
        clarity_score = min(100.0, max(20.0, clarity_score))

        # -------------------------------------------------------------
        # PENALTIES (Subtracted from raw score)
        # -------------------------------------------------------------
        penalties = 0.0
        reasons_penalized = []

        if self.GREETINGS_PATTERN.search(raw_text):
            penalties += 35.0
            reasons_penalized.append("Contains greeting")

        if self.INTROS_PATTERN.search(raw_text):
            penalties += 30.0
            reasons_penalized.append("Contains generic introduction")

        if self.ANNOUNCEMENT_PATTERN.search(raw_text):
            penalties += 25.0
            reasons_penalized.append("Contains meta-announcement ('today we are')")

        if re.search(r"\b(um|uh|er|like\s+you\s+know)\b", raw_text.lower()):
            penalties += 15.0
            reasons_penalized.append("Contains conversational filler")

        if raw_text.rstrip().endswith(("and", "but", "so", "or", "because", "like")):
            penalties += 25.0
            reasons_penalized.append("Incomplete sentence ending")

        if duration > 8.0 and not re.search(r"(\?|\$|\!|\bnever\b|\bwhy\b)", text_lower[:30]):
            penalties += 15.0
            reasons_penalized.append("Long context before hook payoff")

        # -------------------------------------------------------------
        # COMPOSITE FINAL SCORE (0 - 100)
        # -------------------------------------------------------------
        raw_weighted = (
            curiosity_score * 0.22
            + strong_claim_score * 0.18
            + intensity_score * 0.16
            + specificity_score * 0.14
            + standalone_score * 0.12
            + surprise_score * 0.08
            + clarity_score * 0.05
            + narrative_score * 0.05
        )
        final_score = max(5.0, min(99.0, raw_weighted - penalties))

        # -------------------------------------------------------------
        # RETENTION PURPOSE CLASSIFICATION
        # -------------------------------------------------------------
        retention_purpose, retention_reason = self._classify_retention_purpose(
            tightened_text, curiosity_score, intensity_score, strong_claim_score, specificity_score
        )

        explanation = (
            f"Score {final_score:.1f}/100. Retention purpose: {retention_purpose}. "
            f"Curiosity: {curiosity_score:.0f}, Claim: {strong_claim_score:.0f}, Specificity: {specificity_score:.0f}."
        )
        if reasons_penalized:
            explanation += f" Penalties applied: {', '.join(reasons_penalized)}."

        scores = HookScoreBreakdown(
            curiosity_gap=curiosity_score,
            emotional_intensity=intensity_score,
            specificity=specificity_score,
            standalone_context=standalone_score,
            strong_claim=strong_claim_score,
            surprise_interrupt=surprise_score,
            narrative_importance=narrative_score,
            clarity=clarity_score,
            penalties=penalties,
            final_score=final_score,
            explanation=explanation,
        )

        return HookCandidate(
            candidate_id=candidate_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            raw_text=raw_text,
            tightened_text=tightened_text,
            retention_purpose=retention_purpose,
            retention_reason=retention_reason,
            scores=scores,
            is_opening=False,
        )

    def tighten_hook(self, text: str) -> str:
        """Tighten opening preamble while strictly preserving grammatical integrity and syntax.

        Removes conversational throat-clearing ('So basically', 'You know what') without
        producing awkward sentence fragments.
        """
        trimmed = text.strip()
        # Remove preamble phrases if present
        m = self.PREAMBLE_FILLER_PATTERN.match(trimmed)
        if m:
            candidate_trim = trimmed[m.end():].strip()
            # Verify remaining text is a complete grammatical clause (>= 4 words)
            if len(candidate_trim.split()) >= 4:
                trimmed = candidate_trim

        # Ensure first letter is capitalized
        if trimmed and trimmed[0].islower():
            trimmed = trimmed[0].upper() + trimmed[1:]

        # Clean multiple spaces and ensure proper punctuation
        trimmed = re.sub(r"\s+", " ", trimmed).strip()
        return trimmed

    def _classify_retention_purpose(
        self,
        text: str,
        curiosity: float,
        intensity: float,
        claim: float,
        specificity: float,
    ) -> Tuple[str, str]:
        """Determine the specific human retention psychological mechanism for this hook."""
        text_lower = text.lower()

        if "?" in text or curiosity >= 75.0:
            return (
                "CURIOSITY_GAP",
                "Opens an unanswered question that compels viewers to stay for the resolution.",
            )
        if re.search(r"(\$\d+|\b\d+%\b|\b\d+\s*million\b)", text_lower) or specificity >= 75.0:
            return (
                "CONCRETE_STATISTIC",
                "Anchors the viewer with a startling, high-stakes quantitative fact.",
            )
        if claim >= 75.0:
            return (
                "STRONG_CLAIM",
                "Makes a counter-intuitive or bold thesis statement that demands proof.",
            )
        if intensity >= 70.0:
            return (
                "EMOTIONAL_INTENSITY",
                "Immediately hooks attention through high-stakes visceral emotion.",
            )
        if any(w in text_lower for w in ["actually", "wrong", "mistake", "lie"]):
            return (
                "SURPRISE_INTERRUPT",
                "Interrupts viewer assumptions with an unexpected revelation.",
            )
        return (
            "NARRATIVE_STORY",
            "Launches directly into an intriguing real-world situation.",
        )
