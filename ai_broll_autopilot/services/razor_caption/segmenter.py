"""Razor Segmenter — splits a word stream into editorially-meaningful CaptionEvents.

Segmentation is driven by:
  1. Pause detection (inter-word gap > threshold)
  2. Semantic unit boundaries (punctuation, clause breaks)
  3. Word-duration rhythm (unusually long or short words signal edges)
  4. Emphasis transitions (importance score jumps)
  5. Sentence structure (sentence boundary = hard break)

The output is a flat list of CaptionEvents — one per word — with
`segment_break_before` and `segment_break_reason` set appropriately.
Groups of words that belong together are identified by shared phrase_id.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional

from .caption_event import CaptionEvent, CaptionMode, EnergyLevel

logger = logging.getLogger(__name__)

# Thresholds (seconds)
_PAUSE_HARD = 0.40      # inter-word gap → definite break
_PAUSE_SOFT = 0.18      # inter-word gap → soft break (respect semantic context)
_WORD_LONG = 0.55       # single word duration → potential edge
_MAX_GROUP = 5          # default 5 words per segment (overridden by max_group_size)
_MIN_GROUP = 1          # minimum 1 word per segment (single-word punchlines allowed)

# Punctuation that signals a clause/sentence end
_HARD_PUNCT = re.compile(r'[.!?…]$')
_SOFT_PUNCT = re.compile(r'[,;:\-—]$')

# Words that typically start a new semantic unit
_CONNECTOR_WORDS = {
    "and", "but", "so", "because", "although", "however", "therefore",
    "then", "when", "while", "if", "unless", "until", "after", "before",
    "that", "which", "who", "what", "where", "how", "why",
}


def _clean_word(raw: str) -> str:
    return raw.strip()


class RazorSegmenter:
    """Segments a flat word list into razor-cut caption groups.

    Each word is returned as a CaptionEvent with segment metadata.
    Downstream stages enrich the events with importance/position/animation.
    """

    def __init__(
        self,
        pause_hard_threshold: float = _PAUSE_HARD,
        pause_soft_threshold: float = _PAUSE_SOFT,
        max_group_size: int = _MAX_GROUP,
        mode: CaptionMode = CaptionMode.RAPID_RAZOR,
    ):
        self.pause_hard = pause_hard_threshold
        self.pause_soft = pause_soft_threshold
        self.max_group = max_group_size
        self.mode = mode

    def segment(
        self,
        words: List[Dict[str, Any]],
        segments: Optional[List[Dict[str, Any]]] = None,
    ) -> List[CaptionEvent]:
        """Convert raw word dicts to CaptionEvents with razor segmentation.

        Args:
            words: List of word dicts with keys:
                   word, start, end, confidence (optional), speaker (optional),
                   semanticImportance (optional), emphasis (optional), emotion (optional)
            segments: Optional sentence-level segments to inherit sentence_id

        Returns:
            List of CaptionEvent objects (one per word), segmentation metadata set.
        """
        if not words:
            return []

        events: List[CaptionEvent] = []
        phrase_id = 0
        sentence_id = 0
        group_count = 0   # words accumulated in current segment group

        # Build a sentence_id map from segments if provided
        sentence_map: Dict[str, int] = {}
        if segments:
            for si, seg in enumerate(segments):
                for sw in seg.get("words", []):
                    key = f"{sw.get('word', '')}-{sw.get('start', 0)}"
                    sentence_map[key] = si

        prev_end = None

        for i, w in enumerate(words):
            raw = w.get("word", "").strip()
            if not raw:
                continue

            t_start = float(w.get("start", 0.0))
            t_end = float(w.get("end", t_start + 0.15))
            conf = float(w.get("confidence", 1.0))
            speaker = w.get("speaker", "default")
            emotion = w.get("emotion", "neutral")

            # Determine sentence_id from map or sequence
            word_key = f"{raw}-{t_start}"
            if word_key in sentence_map:
                sentence_id = sentence_map[word_key]

            # ── Decide break BEFORE this word ─────────────────────────────
            break_before = False
            break_reason = ""

            # Hard pause
            if prev_end is not None:
                gap = t_start - prev_end
                if gap >= self.pause_hard:
                    break_before = True
                    break_reason = "pause_hard"
                elif gap >= self.pause_soft:
                    # Soft pause — only break if at semantic boundary
                    prev_event = events[-1] if events else None
                    if prev_event and _SOFT_PUNCT.search(prev_event.word):
                        break_before = True
                        break_reason = "pause_soft+punct"

            # Sentence boundary from previous word's punctuation
            if events and _HARD_PUNCT.search(events[-1].word):
                break_before = True
                break_reason = "sentence_boundary"
                sentence_id += 1

            # Connector word starts a new semantic unit
            if raw.lower().rstrip(".,!?") in _CONNECTOR_WORDS and i > 0:
                if not break_before:
                    break_before = True
                    break_reason = "semantic_connector"

            # Group size cap
            if group_count >= self.max_group:
                break_before = True
                break_reason = "max_group_size"

            # Emphasis jump (will be re-scored later, but use raw hint)
            raw_sem = float(w.get("semanticImportance", w.get("semantic_importance", 0.5)))
            raw_emph = w.get("emphasis", False)
            if raw_emph and not break_before and i > 0:
                break_before = True
                break_reason = "emphasis_jump"

            # Unusually long single word (possible punchline)
            word_dur = t_end - t_start
            if word_dur >= _WORD_LONG and not break_before and i > 0:
                break_before = True
                break_reason = "long_word_punchline"

            if break_before:
                phrase_id += 1
                group_count = 0

            ev = CaptionEvent(
                word=_clean_word(raw),
                start_time=t_start,
                end_time=t_end,
                duration=round(t_end - t_start, 4),
                confidence=conf,
                speaker=speaker,
                sentence_id=sentence_id,
                phrase_id=phrase_id,
                semantic_importance=raw_sem,
                emotion=emotion,
                segment_break_before=break_before,
                segment_break_reason=break_reason,
                mode=self.mode,
            )
            events.append(ev)
            group_count += 1
            prev_end = t_end

        logger.debug(
            "RazorSegmenter: %d words → %d phrases across %d events",
            len(words),
            phrase_id + 1,
            len(events),
        )
        return events

    def flatten_from_segments(
        self,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Flatten sentence-level segments into a word list suitable for segment()."""
        words: List[Dict[str, Any]] = []
        for seg in segments:
            seg_words = seg.get("words", [])
            if seg_words:
                words.extend(seg_words)
            else:
                # Uniform distribution fallback
                text = seg.get("text", "").strip()
                tokens = text.split()
                if not tokens:
                    continue
                s = float(seg.get("start", 0.0))
                e = float(seg.get("end", s + len(tokens) * 0.25))
                dur_per = (e - s) / max(len(tokens), 1)
                for k, tok in enumerate(tokens):
                    words.append({
                        "word": tok,
                        "start": round(s + k * dur_per, 3),
                        "end": round(s + (k + 1) * dur_per, 3),
                        "confidence": float(seg.get("confidence", 1.0)),
                        "speaker": seg.get("speaker", "default"),
                    })
        return words
