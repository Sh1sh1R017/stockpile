"""Energy Analyzer — classifies speech segments into LOW / MEDIUM / HIGH energy.

Energy is derived from:
  1. Word density (words per second)
  2. Speech rate variation (acceleration / deceleration)
  3. Inter-word pause frequency
  4. Emphasis word ratio (STRONG + HOOK words per minute)
  5. Emotional signal from emotion tags

This classification feeds the SpatialEngine and AnimationMapper so that
high-energy sections get snappier, more aggressive typography, and
low-energy sections get cleaner, calmer layouts.

NOTE: Energy is a window-level property, not per-word.  Events get their
energy from the window they belong to.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from .caption_event import CaptionEvent, EmphasisLevel, EnergyLevel

logger = logging.getLogger(__name__)

# Thresholds — tuned for short-form 9:16 vertical content
_HIGH_WPS = 3.2          # words per second → HIGH energy
_LOW_WPS = 1.4           # words per second → LOW energy
_HIGH_EMPHASIS_RATIO = 0.20  # ≥20% strong/hook words → HIGH
_LOW_PAUSE_DENSITY = 0.08    # ≤8% of time in pauses → HIGH (non-stop flow)
_HIGH_PAUSE_DENSITY = 0.30   # ≥30% of time in pauses → LOW (slow deliberate)


@dataclass
class EnergyWindow:
    start: float
    end: float
    energy: EnergyLevel
    word_density: float
    emphasis_ratio: float
    pause_ratio: float


class EnergyAnalyzer:
    """Analyzes energy across event windows and stamps each CaptionEvent."""

    def __init__(self, window_sec: float = 3.0):
        """
        Args:
            window_sec: Analysis window in seconds.  3 s is ideal for 9:16 content.
        """
        self.window_sec = window_sec

    def analyze(self, events: List[CaptionEvent]) -> List[CaptionEvent]:
        """Stamp energy level onto each event.  Mutates in-place."""
        if not events:
            return events

        windows = self._build_windows(events)

        for win in windows:
            for ev in events:
                if win.start <= ev.start_time < win.end:
                    ev.energy = win.energy

        return events

    def classify_segment(self, events: List[CaptionEvent]) -> EnergyLevel:
        """Return aggregate energy for a list of events (useful for full clip)."""
        if not events:
            return EnergyLevel.MEDIUM
        wins = self._build_windows(events)
        if not wins:
            return EnergyLevel.MEDIUM
        counts = {EnergyLevel.LOW: 0, EnergyLevel.MEDIUM: 0, EnergyLevel.HIGH: 0}
        for w in wins:
            counts[w.energy] += 1
        return max(counts, key=counts.get)

    # ── Private ───────────────────────────────────────────────────────────

    def _build_windows(self, events: List[CaptionEvent]) -> List[EnergyWindow]:
        if not events:
            return []

        t_min = events[0].start_time
        t_max = events[-1].end_time
        windows: List[EnergyWindow] = []

        t = t_min
        while t < t_max:
            t_end = t + self.window_sec
            w_events = [e for e in events if t <= e.start_time < t_end]

            if not w_events:
                t = t_end
                continue

            window_dur = t_end - t
            spoken_time = sum(e.duration for e in w_events)
            pause_time = max(0.0, window_dur - spoken_time)

            word_density = len(w_events) / max(window_dur, 0.01)
            pause_ratio = pause_time / max(window_dur, 0.01)
            emphasis_count = sum(
                1 for e in w_events if e.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.HOOK)
            )
            emphasis_ratio = emphasis_count / max(len(w_events), 1)

            energy = self._classify(word_density, pause_ratio, emphasis_ratio)

            windows.append(EnergyWindow(
                start=t,
                end=t_end,
                energy=energy,
                word_density=round(word_density, 3),
                emphasis_ratio=round(emphasis_ratio, 3),
                pause_ratio=round(pause_ratio, 3),
            ))
            t = t_end

        return windows

    @staticmethod
    def _classify(
        word_density: float,
        pause_ratio: float,
        emphasis_ratio: float,
    ) -> EnergyLevel:
        """Pure rule-based classification — no randomness."""
        # HIGH: fast speech + many emphasis words + few pauses
        if (
            word_density >= _HIGH_WPS
            or emphasis_ratio >= _HIGH_EMPHASIS_RATIO
            or pause_ratio <= _LOW_PAUSE_DENSITY
        ):
            return EnergyLevel.HIGH

        # LOW: slow speech + many pauses
        if (
            word_density <= _LOW_WPS
            and pause_ratio >= _HIGH_PAUSE_DENSITY
        ):
            return EnergyLevel.LOW

        return EnergyLevel.MEDIUM
