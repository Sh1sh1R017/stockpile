"""Caption State Machine — lifecycle + editorial impact motion wiring."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from .caption_event import CaptionEvent, CaptionState, AnimationType, EmphasisLevel, EnergyLevel
from .impact_composition import compose_impact_group

logger = logging.getLogger(__name__)

_MIN_ANIM_MS = 80
_MAX_ANIM_MS = 600

CAMERA_IMPACT_PARAMS = {
    "start_scale": 0.18,
    "impact_scale": 1.72,
    "overshoot_scale": 1.12,
    "duration_ms": 560,
    "rotation_deg": -4.0,
    "motion_blur": 0.72,
    "camera_punch": 0.82,
    "camera_shake": 0.68,
    "flash": 0.16,
    "perspective": 0.35,
    "frame_bleed": True,
}

CHAOS_IMPACT_WORDS = {
    "chaos", "insane", "unhinged", "absurd", "ridiculous", "wild",
    "nuts", "bonkers", "destroyed", "exploded", "massive", "crazy",
    "wtf", "what", "never", "impossible",
}


def _clamp_ms(v: int) -> int:
    return max(_MIN_ANIM_MS, min(v, _MAX_ANIM_MS))


class CaptionStateMachine:
    """Assign entry/exit animations and phrase-level visual hierarchy."""

    def wire(self, events: List[CaptionEvent]) -> List[CaptionEvent]:
        """Resolve animations, hero/support composition and impact recipes."""
        # Compose each phrase as a visual unit first. This is what turns
        # "JOEY DIAZ WAS PURE CHAOS" into supporting text + a dominant CHAOS
        # treatment instead of four identical subtitle words.
        by_phrase = {}
        for ev in events:
            by_phrase.setdefault(ev.phrase_id, []).append(ev)
        for group in by_phrase.values():
            compose_impact_group(group)

        prev: Optional[CaptionEvent] = None
        for ev in events:
            ev.state = CaptionState.IDLE
            enter, enter_ms = self._select_enter(ev, prev)
            ev.enter_animation = enter
            ev.enter_duration_ms = _clamp_ms(enter_ms)
            exit_anim, exit_ms = self._select_exit(ev, prev)
            ev.exit_animation = exit_anim
            ev.exit_duration_ms = _clamp_ms(exit_ms)
            self._apply_impact_recipe(ev)
            prev = ev
        return events

    @staticmethod
    def _apply_impact_recipe(ev: CaptionEvent) -> None:
        semantic = (ev.semantic_type or "normal").strip().lower()
        clean_word = re.sub(r"[^a-z0-9$%]+", "", str(ev.word).lower())
        is_extreme = (
            semantic in {"hook", "chaos", "extreme"}
            or ev.emphasis == EmphasisLevel.HOOK
            or clean_word in CHAOS_IMPACT_WORDS
        )
        is_strong = semantic in {"strong", "action"} or ev.emphasis == EmphasisLevel.STRONG

        if is_extreme:
            ev.motion_recipe = "kinetic:word-impact-camera"
            ev.motion_params = {**CAMERA_IMPACT_PARAMS, **(ev.motion_params or {})}
            ev.video_effect = "impact-camera-punch"
            ev.emphasis_scale = max(ev.emphasis_scale, 1.55)
            ev.font_size_scale = max(ev.font_size_scale, 1.35)
            ev.enter_animation = AnimationType.OVERSHOOT
            ev.enter_duration_ms = _clamp_ms(560)
            ev.sfx_event = ev.sfx_event or "MAJOR_HOOK"
            return

        if is_strong:
            ev.motion_recipe = ev.motion_recipe if ev.motion_recipe != "kinetic:word-pop" else "kinetic:boom"
            ev.motion_params = {
                "start_scale": 0.72,
                "impact_scale": 1.24,
                "duration_ms": 260,
                "camera_punch": 0.22,
                **(ev.motion_params or {}),
            }
            ev.video_effect = "impact-punch"

    def advance(self, ev: CaptionEvent, current_time: float) -> CaptionState:
        total_dur = max(0.05, ev.end_time - ev.start_time)
        enter_sec = min(total_dur * 0.35, ev.enter_duration_ms / 1000.0)
        exit_sec = min(total_dur * 0.25, ev.exit_duration_ms / 1000.0)
        visible_start = ev.start_time + enter_sec
        exit_start = max(visible_start, ev.end_time - exit_sec)
        if current_time < ev.start_time:
            ev.state = CaptionState.IDLE
        elif current_time < visible_start:
            ev.state = CaptionState.ENTERING
        elif current_time < exit_start:
            ev.state = CaptionState.EMPHASIZED if ev.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.HOOK) else CaptionState.VISIBLE
        elif current_time < ev.end_time:
            ev.state = CaptionState.EXITING
        else:
            ev.state = CaptionState.COMPLETE
        return ev.state

    @staticmethod
    def _select_enter(ev: CaptionEvent, prev: Optional[CaptionEvent]) -> tuple[AnimationType, int]:
        if getattr(ev, "composition_role", None) == "hero":
            return AnimationType.OVERSHOOT, 560
        if ev.segment_break_before:
            if ev.energy == EnergyLevel.HIGH:
                return AnimationType.SNAP, 90
            if ev.energy == EnergyLevel.LOW:
                return AnimationType.FADE, 200
            return AnimationType.DIRECTIONAL, 120
        if ev.emphasis == EmphasisLevel.HOOK:
            return AnimationType.OVERSHOOT, 560
        if ev.emphasis == EmphasisLevel.STRONG:
            return AnimationType.POP, 120
        if ev.emphasis == EmphasisLevel.MODERATE:
            return AnimationType.SCALE, 110
        if ev.energy == EnergyLevel.HIGH:
            return AnimationType.SNAP, 90
        if ev.energy == EnergyLevel.LOW:
            return AnimationType.DRIFT, 200
        return AnimationType.SNAP, 110

    @staticmethod
    def _select_exit(ev: CaptionEvent, prev: Optional[CaptionEvent]) -> tuple[AnimationType, int]:
        if getattr(ev, "composition_role", None) == "hero":
            return AnimationType.SCALE, 120
        if ev.emphasis == EmphasisLevel.HOOK:
            return AnimationType.SCALE, 100
        if ev.energy == EnergyLevel.HIGH:
            return AnimationType.SNAP, 80
        if ev.energy == EnergyLevel.LOW:
            return AnimationType.FADE, 180
        return AnimationType.SNAP, 90
