"""Caption State Machine — drives each CaptionEvent through its lifecycle.

States:
  IDLE → ENTERING → VISIBLE → EMPHASIZED → EXITING → COMPLETE

Transitions are triggered by the playback clock.  The state machine also
resolves animation selection based on:
  - EmphasisLevel (determines enter animation aggressiveness)
  - EnergyLevel (HIGH → snappier transitions, LOW → gentler)
  - Segment break (razor cut → SNAP/DIRECTIONAL instead of FADE)
  - Position change (word moved to new region → SLIDE/DIRECTIONAL)

All animation durations are clamped to 80–250 ms per spec.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .caption_event import (
    CaptionEvent, CaptionState, AnimationType, EmphasisLevel, EnergyLevel
)

logger = logging.getLogger(__name__)

_MIN_ANIM_MS = 80
_MAX_ANIM_MS = 250


def _clamp_ms(v: int) -> int:
    return max(_MIN_ANIM_MS, min(v, _MAX_ANIM_MS))


class CaptionStateMachine:
    """Assigns entry/exit animations and manages lifecycle state.

    Call wire() once per render frame (or offline as a precompute pass).
    """

    def wire(self, events: List[CaptionEvent]) -> List[CaptionEvent]:
        """Resolve animations for all events.  Mutates in-place.

        The state is set to IDLE initially; the renderer advances it.
        """
        prev: Optional[CaptionEvent] = None

        for ev in events:
            ev.state = CaptionState.IDLE

            # ── Enter animation ────────────────────────────────────────────
            enter, enter_ms = self._select_enter(ev, prev)
            ev.enter_animation = enter
            ev.enter_duration_ms = _clamp_ms(enter_ms)

            # ── Exit animation ─────────────────────────────────────────────
            exit_anim, exit_ms = self._select_exit(ev, prev)
            ev.exit_animation = exit_anim
            ev.exit_duration_ms = _clamp_ms(exit_ms)

            prev = ev

        return events

    def advance(self, ev: CaptionEvent, current_time: float) -> CaptionState:
        """Advance a single event's state based on current playback time.

        Returns the new state.  Caller responsible for rendering.
        """
        enter_sec = ev.enter_duration_ms / 1000.0
        exit_sec = ev.exit_duration_ms / 1000.0
        visible_start = ev.start_time + enter_sec
        exit_start = ev.end_time - exit_sec

        if current_time < ev.start_time:
            ev.state = CaptionState.IDLE
        elif current_time < visible_start:
            ev.state = CaptionState.ENTERING
        elif current_time < exit_start:
            if ev.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.HOOK):
                ev.state = CaptionState.EMPHASIZED
            else:
                ev.state = CaptionState.VISIBLE
        elif current_time < ev.end_time:
            ev.state = CaptionState.EXITING
        else:
            ev.state = CaptionState.COMPLETE

        return ev.state

    # ── Private ────────────────────────────────────────────────────────────

    @staticmethod
    def _select_enter(
        ev: CaptionEvent,
        prev: Optional[CaptionEvent],
    ) -> tuple[AnimationType, int]:
        """Select entry animation — justified by emphasis + energy + segment break."""

        # Razor cut (new segment) → SNAP or DIRECTIONAL
        if ev.segment_break_before:
            if ev.energy == EnergyLevel.HIGH:
                return AnimationType.SNAP, 90
            if ev.energy == EnergyLevel.LOW:
                return AnimationType.FADE, 200
            return AnimationType.DIRECTIONAL, 120

        # Hook words get the most dramatic entry
        if ev.emphasis == EmphasisLevel.HOOK:
            return AnimationType.OVERSHOOT, 150

        # Strong emphasis
        if ev.emphasis == EmphasisLevel.STRONG:
            return AnimationType.POP, 120

        # Moderate
        if ev.emphasis == EmphasisLevel.MODERATE:
            return AnimationType.SCALE, 110

        # High energy normal words
        if ev.energy == EnergyLevel.HIGH:
            return AnimationType.SNAP, 90

        # Low energy
        if ev.energy == EnergyLevel.LOW:
            return AnimationType.DRIFT, 200

        # Default
        return AnimationType.SNAP, 110

    @staticmethod
    def _select_exit(
        ev: CaptionEvent,
        prev: Optional[CaptionEvent],
    ) -> tuple[AnimationType, int]:
        """Select exit animation — typically shorter and simpler than entry."""

        if ev.emphasis == EmphasisLevel.HOOK:
            return AnimationType.SCALE, 100

        if ev.energy == EnergyLevel.HIGH:
            return AnimationType.SNAP, 80

        if ev.energy == EnergyLevel.LOW:
            return AnimationType.FADE, 180

        return AnimationType.SNAP, 90
