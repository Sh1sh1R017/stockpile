"""Kinetic caption and impact-word motion profiles.

The editor can use a fixed profile (boom/slide/bounce/etc.) or ``impact-auto``.
In impact-auto mode the caption's semantic classification selects a matching
motion recipe, so strong words can drive the visual treatment without manually
keyframing every caption.
"""

from typing import Dict, Any


CAPTION_MOTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "word-pop": {
        "label": "Word Pop", "openreel": "word-highlight",
        "recipe": "kinetic:word-pop", "description": "Active word scales up and settles."
    },
    "boom": {
        "label": "Boom", "openreel": "impact-punch",
        "recipe": "kinetic:boom", "description": "Fast overshoot, settle and impact punch."
    },
    "slam": {
        "label": "Slam", "openreel": "impact-slam",
        "recipe": "kinetic:slam", "description": "Hard snap-in with a short impact shake."
    },
    "slide-left": {
        "label": "Slide Left", "openreel": "slide-left",
        "recipe": "kinetic:slide-left", "description": "Caption enters from the right and slides left into place."
    },
    "slide-right": {
        "label": "Slide Right", "openreel": "slide-right",
        "recipe": "kinetic:slide-right", "description": "Caption enters from the left and slides right into place."
    },
    "slide-up": {
        "label": "Slide Up", "openreel": "slide-up",
        "recipe": "kinetic:slide-up", "description": "Clean upward entrance for short caption groups."
    },
    "bounce": {
        "label": "Bounce", "openreel": "bounce",
        "recipe": "kinetic:bounce", "description": "Spring-like overshoot and settle."
    },
    "zoom": {
        "label": "Zoom Punch", "openreel": "zoom-punch",
        "recipe": "kinetic:zoom-punch", "description": "Rapid camera/text punch toward the impact word."
    },
    "shake": {
        "label": "Shake", "openreel": "impact-shake",
        "recipe": "kinetic:shake", "description": "Short decaying impact shake."
    },
    "typewriter": {
        "label": "Typewriter", "openreel": "typewriter",
        "recipe": "kinetic:typewriter", "description": "Sequential reveal."
    },
    "focus": {
        "label": "True Focus", "openreel": "word-highlight",
        "recipe": "kinetic:true-focus", "description": "Keeps the line stable while focusing the active word."
    },
    "scramble": {
        "label": "Text Scramble", "openreel": "word-by-word",
        "recipe": "kinetic:scramble", "description": "Fast decode-style word transition."
    },
    "impact-auto": {
        "label": "AI Impact Auto", "openreel": "impact-auto",
        "recipe": "kinetic:impact-auto", "description": "Automatically chooses an effect from the impact word's semantic type."
    },
}

# Semantic caption categories -> visual treatment. This is intentionally conservative:
# only semantically meaningful words get a strong effect, while normal words remain calm.
IMPACT_EFFECTS: Dict[str, str] = {
    "hook": "boom",
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
        "pop": "word-pop",
        "impact": "impact-auto",
        "auto": "impact-auto",
        "boom/pop": "boom",
        "slide": "slide-left",
    }
    key = aliases.get(key, key)
    return key if key in CAPTION_MOTION_PROFILES else "word-pop"


def impact_effect_for_semantic_type(semantic_type: str) -> str:
    return IMPACT_EFFECTS.get((semantic_type or "normal").strip().lower(), "word-pop")


def apply_caption_motion(subtitles: list, profile: str) -> list:
    """Annotate subtitle events with the requested or automatically selected motion.

    In ``impact-auto`` mode the semantic_type assigned by the Razor importance scorer
    determines the effect. The resulting animationStyle/motionRecipe fields are kept
    in the canonical subtitle payload so the render adapters can consume them.
    """
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
        result.append(item)
    return result
