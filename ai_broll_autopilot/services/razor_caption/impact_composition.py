"""Editorial impact-composition planner for human-looking short-form captions.

Turns a sentence into a visual hierarchy instead of rendering every word with
identical typography. One high-impact word becomes the hero; surrounding words
stay supportive and can use lighter directional motion. The planner is
intentionally deterministic so a render can be reproduced.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

from .caption_event import CaptionEvent, EmphasisLevel, SpatialRegion


HERO_TERMS = {
    "chaos", "insane", "unhinged", "absurd", "ridiculous", "wild", "crazy",
    "massive", "huge", "never", "nothing", "nobody", "impossible", "broke",
    "million", "billion", "wtf", "what", "stop", "secret", "destroyed",
}

HERO_SEMANTICS = {"hook", "chaos", "extreme", "money", "number", "negation"}

SUPPORT_ANIMATIONS = (
    "kinetic:slide-left",
    "kinetic:slide-right",
    "kinetic:slide-up",
    "kinetic:bounce",
)

SUPPORT_REGIONS = (
    SpatialRegion.TOP_LEFT,
    SpatialRegion.TOP_RIGHT,
    SpatialRegion.CENTER_LEFT,
    SpatialRegion.CENTER_RIGHT,
    SpatialRegion.LOWER_LEFT,
    SpatialRegion.LOWER_RIGHT,
)


def _clean(word: str) -> str:
    return re.sub(r"[^a-z0-9$%]+", "", str(word).lower())


def _seed(events: List[CaptionEvent]) -> int:
    raw = "|".join(f"{e.phrase_id}:{e.word}" for e in events)
    return int(hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8], 16)


def compose_impact_group(events: List[CaptionEvent]) -> List[CaptionEvent]:
    """Assign hero/support roles and visual hierarchy to a caption phrase."""
    if not events:
        return events

    hero_candidates = [
        e for e in events
        if (e.semantic_type or "normal").lower() in HERO_SEMANTICS
        or _clean(e.word) in HERO_TERMS
        or e.emphasis == EmphasisLevel.HOOK
    ]
    if not hero_candidates:
        hero_candidates = [e for e in events if e.emphasis == EmphasisLevel.STRONG]
    if not hero_candidates:
        return events

    hero = max(hero_candidates, key=lambda e: (e.word_importance_score, e.emphasis.value, e.emotional_importance))
    # Chaos budget decides whether a candidate earns the expensive hero
    # composition. Keyword presence alone is never enough.
    if getattr(hero, "chaos_tier", "normal") not in {"impact", "absurd"}:
        return events
    seed = _seed(events)

    # Hero typography: deliberately much larger and visually distinct.
    hero.composition_role = "hero"
    hero.typography_style = "impact-hero"
    hero.font_size_scale = max(hero.font_size_scale, 1.55)
    hero.emphasis_scale = max(hero.emphasis_scale, 1.60)
    hero.font_weight = "Black"
    hero.tracking = max(hero.tracking, 0.02)
    hero.position_reason = "impact-hero"

    if hero.motion_recipe == "kinetic:word-pop":
        hero.motion_recipe = "kinetic:word-impact-camera"

    # Supporting words intentionally orbit the hero instead of sharing one flat
    # subtitle box. Deterministic alternation avoids unstable renders.
    support_index = 0
    for ev in events:
        if ev is hero:
            continue
        ev.composition_role = "support"
        ev.typography_style = "support-editorial"
        ev.font_size_scale = min(ev.font_size_scale, 0.92)
        ev.emphasis_scale = min(ev.emphasis_scale, 1.05)
        ev.font_weight = "Bold"
        if ev.motion_recipe == "kinetic:word-pop":
            ev.motion_recipe = SUPPORT_ANIMATIONS[(seed + support_index) % len(SUPPORT_ANIMATIONS)]
        ev.position_reason = "impact-support"
        # Only move support words when they are not already spatially meaningful.
        if ev.region == SpatialRegion.LOWER_CENTER:
            ev.region = SUPPORT_REGIONS[(seed + support_index) % len(SUPPORT_REGIONS)]
            ev.position_x = {
                SpatialRegion.TOP_LEFT: 0.22,
                SpatialRegion.TOP_RIGHT: 0.78,
                SpatialRegion.CENTER_LEFT: 0.20,
                SpatialRegion.CENTER_RIGHT: 0.80,
                SpatialRegion.LOWER_LEFT: 0.24,
                SpatialRegion.LOWER_RIGHT: 0.76,
            }[ev.region]
            ev.position_y = {
                SpatialRegion.TOP_LEFT: 0.25,
                SpatialRegion.TOP_RIGHT: 0.25,
                SpatialRegion.CENTER_LEFT: 0.48,
                SpatialRegion.CENTER_RIGHT: 0.48,
                SpatialRegion.LOWER_LEFT: 0.70,
                SpatialRegion.LOWER_RIGHT: 0.70,
            }[ev.region]
        support_index += 1

    # Tell downstream renderers that this phrase is a composition, not a flat line.
    for ev in events:
        if ev is not hero:
            params = dict(ev.motion_params or {})
            params["composition_role"] = "support"
            ev.motion_params = params
    params = dict(hero.motion_params or {})
    params.update({
        "composition_role": "hero",
        "hero": True,
        "impact_scale": max(float(params.get("impact_scale", 1.72)), 1.72),
        "frame_bleed": True,
    })
    hero.motion_params = params
    return events
