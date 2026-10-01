"""Kinetic caption and impact-word motion profiles.

The editor can use a fixed profile (boom/slide/bounce/etc.) or ``impact-auto``.
In impact-auto mode the caption's semantic classification selects a matching
motion recipe, including a dedicated camera-impact treatment for extreme words.
"""

from typing import Dict, Any


CAPTION_MOTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "word-pop": {"label": "Word Pop", "openreel": "word-highlight", "recipe": "kinetic:word-pop", "description": "Active word scales up and settles."},
    "boom": {"label": "Boom", "openreel": "impact-punch", "recipe": "kinetic:boom", "description": "Fast overshoot, settle and impact punch."},
    "slam": {"label": "Slam", "openreel": "impact-slam", "recipe": "kinetic:slam", "description": "Hard snap-in with a short impact shake."},
    "slide-left": {"label": "Slide Left", "openreel": "slide-left", "recipe": "kinetic:slide-left", "description": "Caption enters from the right and slides left into place."},
    "slide-right": {"label": "Slide Right", "openreel": "slide-right", "recipe": "kinetic:slide-right", "description": "Caption enters from the left and slides right into place."},
    "slide-up": {"label": "Slide Up", "openreel": "slide-up", "recipe": "kinetic:slide-up", "description": "Clean upward entrance for short caption groups."},
    "bounce": {"label": "Bounce", "openreel": "bounce", "recipe": "kinetic:bounce", "description": "Spring-like overshoot and settle."},
    "zoom": {"label": "Zoom Punch", "openreel": "zoom-punch", "recipe": "kinetic:zoom-punch", "description": "Rapid punch toward the impact word."},
    "shake": {"label": "Shake", "openreel": "impact-shake", "recipe": "kinetic:shake", "description": "Short decaying impact shake."},
    "word-impact-camera": {
        "label": "Word Impact — Camera",
        "openreel": "impact-camera",
        "recipe": "kinetic:word-impact-camera",
        "description": "Extreme impact word flies toward the viewer, overshoots the frame and hits with a camera punch.",
        "params": {
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
        },
    },
    "typewriter": {"label": "Typewriter", "openreel": "typewriter", "recipe": "motion-anything:typewriter-multi", "description": "Sequential reveal."},
    "focus": {"label": "True Focus", "openreel": "word-highlight", "recipe": "kinetic:true-focus", "description": "Stable line with active-word emphasis."},
    "scramble": {"label": "Text Scramble", "openreel": "word-by-word", "recipe": "kinetic:scramble", "description": "Fast decode-style word transition."},
    "impact-auto": {"label": "AI Impact Auto", "openreel": "impact-auto", "recipe": "kinetic:impact-auto", "description": "Automatically chooses an effect from the impact word's semantic type."},
}

# Semantic categories that deserve the most aggressive treatment. The extreme
# camera-impact recipe is intentionally sparse: it should feel like the editor
# suddenly lost its mind, not like every subtitle is a transition.
IMPACT_EFFECTS: Dict[str, str] = {
    "hook": "word-impact-camera",
    "chaos": "word-impact-camera",
    "extreme": "word-impact-camera",
    "money": "zoom",
    "number": "zoom",
    "negation": "slam",
    "cta": "slide-up",
    "action": "slide-left",
    "strong": "bounce",
    "normal": "word-pop",
}


def normalize_motion_profile(name: str) -> str:
    key = (name or "word-pop").strip().lower()
    aliases = {
        "pop": "impact-auto",
        "impact": "impact-auto",
        "auto": "impact-auto",
        "boom/pop": "boom",
        "slide": "slide-left",
        "camera-impact": "word-impact-camera",
        "impact-camera": "word-impact-camera",
        "hit": "word-impact-camera",
    }
    key = aliases.get(key, key)
    return key if key in CAPTION_MOTION_PROFILES else "word-pop"


def impact_effect_for_semantic_type(semantic_type: str) -> str:
    return IMPACT_EFFECTS.get((semantic_type or "normal").strip().lower(), "word-pop")


def apply_caption_motion(subtitles: list, profile: str) -> list:
    """Annotate subtitle events with requested or automatically selected motion."""
    profile = normalize_motion_profile(profile)
    result = []
    for subtitle in subtitles or []:
        item = dict(subtitle)
        semantic_type = str(item.get("semantic_type") or item.get("semanticType") or "normal")
        selected = impact_effect_for_semantic_type(semantic_type) if profile == "impact-auto" else profile
        cfg = CAPTION_MOTION_PROFILES[selected]
        item["animationStyle"] = cfg["openreel"]
        item["motionProfile"] = selected
        item["motionRecipe"] = cfg["recipe"]
        item["impactEffect"] = selected
        item["impactSemanticType"] = semantic_type
        if cfg.get("params"):
            item["motionParams"] = dict(cfg["params"])
        result.append(item)
    return result