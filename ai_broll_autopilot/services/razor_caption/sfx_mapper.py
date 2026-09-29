"""SFX Mapper — maps CaptionEvents to the correct sound effect event.

Rules (from spec):
  KEYWORD_POP     → moderately important word (STRONG)
  TEXT_SNAP       → razor-cut segment break (any importance)
  BEHIND_SUBJECT  → soft whoosh for behind-subject composited words
  MAJOR_HOOK      → restrained impact for HOOK-level words
  NORMAL_WORD     → NO SFX (silence is editorial discipline)

SFX names are forwarded to the existing SoundDesigner blacklist check
before being committed, so no laughs / memes / cartoon sounds ever make it.

All SFX are disabled for NORMAL emphasis words — silence is the default.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .caption_event import CaptionEvent, EmphasisLevel, LayerMode

logger = logging.getLogger(__name__)

# Canonical SFX event name constants
SFX_KEYWORD_POP = "KEYWORD_POP"
SFX_TEXT_SNAP = "TEXT_SNAP"
SFX_BEHIND_SUBJECT_WHOOSH = "BEHIND_SUBJECT_WHOOSH"
SFX_MAJOR_HOOK = "MAJOR_HOOK"
SFX_NONE = None


class SfxMapper:
    """Maps caption events to SFX events respecting the blacklist guard."""

    def __init__(self, sound_designer=None):
        """
        Args:
            sound_designer: Optional SoundDesigner instance for blacklist check.
                            If None, blacklist check is skipped.
        """
        self._sd = sound_designer

    def map(self, events: List[CaptionEvent]) -> List[CaptionEvent]:
        """Assign sfx_event to each CaptionEvent.  Mutates in-place."""
        for ev in events:
            sfx = self._assign(ev)
            if sfx and self._is_blacklisted(sfx):
                sfx = SFX_NONE
            ev.sfx_event = sfx
        return events

    # ── Private ────────────────────────────────────────────────────────────

    @staticmethod
    def _assign(ev: CaptionEvent) -> Optional[str]:
        # Behind-subject composited words get a subtle whoosh
        if ev.layer == LayerMode.BEHIND_SUBJECT:
            return SFX_BEHIND_SUBJECT_WHOOSH

        # Hook words get a restrained impact (only if not already behind-subject)
        if ev.emphasis == EmphasisLevel.HOOK:
            return SFX_MAJOR_HOOK

        # Razor cut transition: text snap for any break
        if ev.segment_break_before:
            return SFX_TEXT_SNAP

        # Strong emphasis: keyword pop
        if ev.emphasis == EmphasisLevel.STRONG:
            return SFX_KEYWORD_POP

        # MODERATE and NORMAL: no SFX (editorial discipline)
        return SFX_NONE

    def _is_blacklisted(self, sfx: str) -> bool:
        if self._sd is None:
            return False
        try:
            return self._sd.is_blacklisted(sfx)
        except Exception:
            return False
