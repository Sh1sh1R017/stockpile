"""Caption State Machine — lifecycle + editorial impact motion wiring."""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional

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


CHAOS_WORD_BONUS = 0.22
CHAOS_REGEN_PER_SEC = 0.22
CHAOS_COSTS = {"kinetic": 0.20, "impact": 0.48, "absurd": 0.82}


def _clamp_ms(v: int) -> int:
    return max(_MIN_ANIM_MS, min(v, _MAX_ANIM_MS))


class CaptionStateMachine:
    """Assign entry/exit animations and phrase-level visual hierarchy."""

    def wire(
        self,
        events: List[CaptionEvent],
        editorial_intents: Optional[List[Any]] = None,
    ) -> List[CaptionEvent]:
        """Resolve animations using shared editorial intent when available."""

        # Compose each phrase as a visual unit first. This is what turns
        # "JOEY DIAZ WAS PURE CHAOS" into supporting text + a dominant CHAOS
        # treatment instead of four identical subtitle words.
        if editorial_intents:
            self._apply_editorial_intents(events, editorial_intents)
        else:
            self._apply_chaos_budget(events)

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
    def _apply_editorial_intents(events: List[CaptionEvent], editorial_intents: List[Any]) -> None:
        """Apply Creative Director decisions to caption words by moment time range."""
        ranges = []
        for intent in editorial_intents:
            if hasattr(intent, "start_time"):
                start = float(getattr(intent, "start_time", 0.0))
                end = float(getattr(intent, "end_time", start))
                getter = lambda key, default=None, obj=intent: getattr(obj, key, default)
            elif isinstance(intent, dict):
                start = float(intent.get("start_time", 0.0))
                end = float(intent.get("end_time", start))
                getter = lambda key, default=None, obj=intent: obj.get(key, default)
            else:
                continue
            ranges.append((start, end, getter))

        for ev in events:
            matched = None
            for start, end, getter in ranges:
                if start <= ev.start_time < max(end, start + 0.01):
                    matched = getter
                    break
            if matched is None and ranges:
                matched = min(ranges, key=lambda item: abs(item[0] - ev.start_time))[2]
            if matched is None:
                continue

            ev.chaos_score = float(matched("chaos_score", ev.chaos_score) or 0.0)
            ev.chaos_tier = str(
                matched("chaos_tier", matched("treatment", ev.chaos_tier)) or "normal"
            )
            ev.chaos_budget_remaining = float(
                matched("chaos_budget_remaining", ev.chaos_budget_remaining) or 0.0
            )
            ev.editorial_treatment = str(
                matched("treatment", matched("chaos_tier", ev.editorial_treatment)) or "normal"
            )
            ev.hook_relevance = float(matched("hook_relevance", ev.hook_relevance) or 0.0)
            ev.speaker_emphasis = float(matched("speaker_emphasis", ev.speaker_emphasis) or 0.0)
            ev.semantic_importance = float(
                matched("semantic_importance", ev.semantic_importance) or 0.0
            )
            ev.emotional_importance = float(
                matched("emotional_importance", ev.emotional_importance) or 0.0
            )

    @staticmethod
    def _apply_chaos_budget(events: List[CaptionEvent]) -> None:
        """Score and ration impact intensity across the timeline."""
        budget = 1.0
        previous_time = events[0].start_time if events else 0.0
        for ev in events:
            elapsed = max(0.0, ev.start_time - previous_time)
            budget = min(1.0, budget + elapsed * CHAOS_REGEN_PER_SEC)
            semantic = (ev.semantic_type or "normal").strip().lower()
            clean_word = re.sub(r"[^a-z0-9$%]+", "", str(ev.word).lower())
            lexical = CHAOS_WORD_BONUS if clean_word in CHAOS_IMPACT_WORDS else 0.0
            energy_bonus = {EnergyLevel.LOW: 0.0, EnergyLevel.MEDIUM: 0.06, EnergyLevel.HIGH: 0.14}[ev.energy]
            raw = (
                0.42 * max(0.0, min(1.0, ev.word_importance_score))
                + 0.18 * max(0.0, min(1.0, ev.emotional_importance))
                + 0.14 * max(0.0, min(1.0, ev.hook_relevance))
                + 0.12 * max(0.0, min(1.0, ev.speaker_emphasis))
                + energy_bonus
                + lexical
            )
            if semantic in {"chaos", "extreme"}:
                raw += 0.16
            if ev.emphasis == EmphasisLevel.HOOK:
                raw += 0.18
            score = max(0.0, min(1.0, raw))
            ev.chaos_score = score

            if score >= 0.78:
                desired = "absurd"
            elif score >= 0.60:
                desired = "impact"
            elif score >= 0.40:
                desired = "kinetic"
            else:
                desired = "normal"

            if desired == "absurd" and budget < CHAOS_COSTS["absurd"]:
                desired = "impact" if budget >= CHAOS_COSTS["impact"] else "kinetic" if budget >= CHAOS_COSTS["kinetic"] else "normal"
            elif desired == "impact" and budget < CHAOS_COSTS["impact"]:
                desired = "kinetic" if budget >= CHAOS_COSTS["kinetic"] else "normal"
            elif desired == "kinetic" and budget < CHAOS_COSTS["kinetic"]:
                desired = "normal"

            budget = max(0.0, budget - CHAOS_COSTS.get(desired, 0.0))
            ev.chaos_tier = desired
            ev.editorial_treatment = desired
            ev.chaos_budget_remaining = budget
            previous_time = ev.start_time

    @staticmethod
    def _apply_impact_recipe(ev: CaptionEvent) -> None:
        # Shared intent is authoritative. Do not let keyword/emphasis heuristics
        # re-promote a quiet or normal moment after Creative Director approval.
        if ev.editorial_treatment in {"quiet", "normal"}:
            return
        is_extreme = ev.chaos_tier in {"impact", "absurd"}
        is_strong = ev.chaos_tier == "kinetic" or (ev.semantic_type or "").strip().lower() in {"strong", "action"} or ev.emphasis == EmphasisLevel.STRONG

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
