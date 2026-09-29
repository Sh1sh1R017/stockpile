"""Word Importance Scorer for the Rapid Razor Caption Engine.

Computes a composite importance score (0.0–1.0) for each CaptionEvent and
assigns the correct EmphasisLevel.

Score components:
  1. semantic_importance    — from transcript ASR metadata
  2. emotional_importance   — from emotion tag
  3. novelty                — first occurrence of a significant word
  4. numeric_value          — word contains a number/percentage/dollar
  5. named_entity           — capitalized proper noun / brand
  6. action_word            — action verb / imperative / CTA
  7. hook_relevance         — proximity to first word & classic hook vocabulary
  8. speaker_emphasis       — raw emphasis flag from ASR prosody
  9. word_rarity            — common function words score low

Emphasis assignment (never emphasize everything):
  HOOK    → top ~5%  of importance distribution
  STRONG  → next ~10%
  MODERATE → next ~20%
  NORMAL  → bottom ~65%

Behind-subject compositing is only granted to HOOK-level words where
the word is a major noun, number, or punchline.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from .caption_event import CaptionEvent, EmphasisLevel, LayerMode

# ---------------------------------------------------------------------------
# Word-category lookup sets
# ---------------------------------------------------------------------------

_FUNCTION_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought", "used",
    "to", "of", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "from", "up", "down", "out", "off", "over", "under", "then", "once",
    "and", "but", "or", "nor", "so", "yet", "both", "either", "neither",
    "not", "no", "only", "same", "than", "too", "very", "also", "just",
    "i", "me", "my", "myself", "we", "our", "ours", "you", "your", "he",
    "him", "his", "she", "her", "it", "its", "they", "them", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom",
}

_ACTION_WORDS: Set[str] = {
    "build", "built", "create", "created", "make", "made", "start", "started",
    "launch", "launched", "grow", "grew", "scale", "scaled", "sell", "sold",
    "buy", "bought", "invest", "invested", "earn", "earned", "win", "won",
    "lose", "lost", "quit", "quit", "leave", "left", "join", "joined",
    "fire", "fired", "hire", "hired", "learn", "learned", "teach", "taught",
    "stop", "stopped", "change", "changed", "think", "thought", "know", "knew",
    "realize", "realized", "discover", "discovered", "found", "find",
    "watch", "watched", "listen", "listened", "read", "said", "say", "tell",
    "told", "show", "showed", "prove", "proved", "fail", "failed",
    "succeed", "succeeded", "transform", "transformed", "hack", "hacked",
    "click", "subscribe", "follow", "like", "share", "comment", "go", "went",
}

_HOOK_VOCAB: Set[str] = {
    "never", "always", "everyone", "nobody", "impossible", "secret",
    "truth", "lie", "wrong", "right", "real", "fake", "shocking", "crazy",
    "insane", "unbelievable", "mind-blowing", "millions", "billion", "zero",
    "mistake", "hack", "trick", "strategy", "system", "method", "formula",
    "proven", "fastest", "easiest", "hardest", "only", "last", "first",
    "best", "worst", "biggest", "smallest", "richest", "poorest",
}

_EMOTION_WEIGHT: dict = {
    "neutral": 0.0,
    "joy": 0.3,
    "surprise": 0.4,
    "anger": 0.35,
    "fear": 0.3,
    "sadness": 0.2,
    "disgust": 0.25,
    "anticipation": 0.3,
    "trust": 0.15,
}

_NUM_PATTERN = re.compile(r'\d')
_CURRENCY_PATTERN = re.compile(r'[\$£€¥]\d|^\d+[kKmMbB]$|\d+%')
_PROPER_NOUN_PATTERN = re.compile(r'^[A-Z][a-z]+$')  # Capitalized word


class ImportanceScorer:
    """Scores each CaptionEvent and assigns EmphasisLevel in a single pass.

    Call score() to enrich a list of events in-place.
    """

    def __init__(
        self,
        hook_threshold: float = 0.78,
        strong_threshold: float = 0.62,
        moderate_threshold: float = 0.44,
        enable_behind_subject: bool = True,
    ):
        self.hook_threshold = hook_threshold
        self.strong_threshold = strong_threshold
        self.moderate_threshold = moderate_threshold
        self.enable_behind_subject = enable_behind_subject
        self._seen_words: Set[str] = set()   # for novelty tracking

    def score(self, events: List[CaptionEvent]) -> List[CaptionEvent]:
        """Score and assign emphasis to all events.  Mutates in-place."""
        self._seen_words.clear()

        # First pass: compute raw scores
        for ev in events:
            ev.word_importance_score = self._compute_raw(ev)

        # Second pass: normalize and assign EmphasisLevel
        scores = [ev.word_importance_score for ev in events]
        if not scores:
            return events

        mn, mx = min(scores), max(scores)
        score_range = mx - mn if mx > mn else 1.0

        # Track how many HOOKs and STRONGs we've assigned (budget guard)
        total = len(events)
        hook_budget = max(1, int(total * 0.05))    # ≤5%
        strong_budget = max(1, int(total * 0.10))  # ≤10%
        moderate_budget = max(1, int(total * 0.20)) # ≤20%
        hook_count = 0
        strong_count = 0
        moderate_count = 0

        # Sort events by score desc to assign budgeted emphasis
        indexed = sorted(enumerate(events), key=lambda x: -x[1].word_importance_score)

        for rank, (i, ev) in enumerate(indexed):
            norm = (ev.word_importance_score - mn) / score_range  # 0.0→1.0

            if norm >= self.hook_threshold and hook_count < hook_budget:
                ev.emphasis = EmphasisLevel.HOOK
                hook_count += 1
                # Behind-subject compositing: only hook words that are also
                # nouns/numbers/punchlines
                if self.enable_behind_subject and (
                    ev.named_entity or ev.numeric_value or ev.action_word
                ):
                    ev.layer = LayerMode.BEHIND_SUBJECT
                # Typography for HOOK
                ev.font_weight = "Black"
                ev.font_size_scale = 1.25
                ev.accent_color = "#FFE600"
                ev.fill_color = "#FFE600"
                ev.emphasis_scale = 1.2
                ev.sfx_event = "MAJOR_HOOK"

            elif norm >= self.strong_threshold and strong_count < strong_budget:
                ev.emphasis = EmphasisLevel.STRONG
                strong_count += 1
                ev.font_weight = "ExtraBold"
                ev.font_size_scale = 1.12
                ev.fill_color = "#FFE600"
                ev.emphasis_scale = 1.1
                ev.sfx_event = "KEYWORD_POP"

            elif norm >= self.moderate_threshold and moderate_count < moderate_budget:
                ev.emphasis = EmphasisLevel.MODERATE
                moderate_count += 1
                ev.font_weight = "Bold"
                ev.font_size_scale = 1.05
                ev.emphasis_scale = 1.04

            else:
                ev.emphasis = EmphasisLevel.NORMAL
                ev.font_weight = "Bold"
                ev.font_size_scale = 1.0
                ev.emphasis_scale = 1.0

        return events

    # ── Private helpers ────────────────────────────────────────────────────

    def _compute_raw(self, ev: CaptionEvent) -> float:
        w = ev.word.lower().rstrip(".,!?:;\"'")
        score = 0.0

        # 1. Semantic importance (from ASR / transcript metadata)
        score += ev.semantic_importance * 0.25

        # 2. Emotional importance
        score += _EMOTION_WEIGHT.get(ev.emotion, 0.0) * 0.12
        ev.emotional_importance = _EMOTION_WEIGHT.get(ev.emotion, 0.0)

        # 3. Novelty (first occurrence of a non-function word)
        if w not in _FUNCTION_WORDS and w not in self._seen_words:
            score += 0.10
            ev.novelty = 0.10
        self._seen_words.add(w)

        # 4. Numeric / monetary value
        if _NUM_PATTERN.search(ev.word) or _CURRENCY_PATTERN.search(ev.word):
            score += 0.18
            ev.numeric_value = True

        # 5. Named entity (capitalized word that's not start-of-sentence)
        if _PROPER_NOUN_PATTERN.match(ev.word) and ev.word.lower() not in _FUNCTION_WORDS:
            score += 0.14
            ev.named_entity = True

        # 6. Action word
        if w in _ACTION_WORDS:
            score += 0.12
            ev.action_word = True

        # 7. Hook vocabulary
        if w in _HOOK_VOCAB:
            score += 0.20
            ev.hook_relevance = 0.20

        # 8. Speaker emphasis (from ASR prosody flag)
        if ev.speaker_emphasis > 0:
            score += ev.speaker_emphasis * 0.15

        # 9. Penalize function words
        if w in _FUNCTION_WORDS:
            score -= 0.20

        # 10. Word duration proxy (longer spoken word = more weight)
        if ev.duration > 0.35:
            score += min((ev.duration - 0.35) * 0.25, 0.10)

        return max(0.0, min(score, 1.0))
