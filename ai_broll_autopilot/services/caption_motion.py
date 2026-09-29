"""Caption motion profiles inspired by motion-anything's kinetic-text recipe model.

These are intentionally mapped to Stockpile/OpenReel/ASS primitives instead of
embedding the motion-anything application itself into the video pipeline.
"""

from typing import Dict, Any


CAPTION_MOTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "word-pop": {
        "label": "Word Pop",
        "openreel": "word-highlight",
        "recipe": "motion-anything:kinetic-text",
        "description": "Subtle active-word scale pop.",
    },
    "bounce": {
        "label": "Bounce",
        "openreel": "bounce",
        "recipe": "motion-anything:bounce-cards",
        "description": "Short spring-like emphasis on the active word.",
    },
    "typewriter": {
        "label": "Typewriter",
        "openreel": "typewriter",
        "recipe": "motion-anything:typewriter-multi",
        "description": "Sequential reveal suitable for hook or statement captions.",
    },
    "focus": {
        "label": "True Focus",
        "openreel": "word-highlight",
        "recipe": "motion-anything:true-focus",
        "description": "Active word gets emphasis while the line remains stable.",
    },
    "scramble": {
        "label": "Text Scramble",
        "openreel": "word-by-word",
        "recipe": "motion-anything:text-scramble",
        "description": "Fast decode-style transition between words.",
    },
    "slide-up": {
        "label": "Slide Up",
        "openreel": "word-by-word",
        "recipe": "motion-anything:entrance",
        "description": "Clean upward entrance for short caption groups.",
    },
}


def normalize_motion_profile(name: str) -> str:
    key = (name or "word-pop").strip().lower()
    return key if key in CAPTION_MOTION_PROFILES else "word-pop"


def apply_caption_motion(subtitles: list, profile: str) -> list:
    profile = normalize_motion_profile(profile)
    cfg = CAPTION_MOTION_PROFILES[profile]
    result = []
    for subtitle in subtitles or []:
        item = dict(subtitle)
        item["animationStyle"] = cfg["openreel"]
        item["motionProfile"] = profile
        item["motionRecipe"] = cfg["recipe"]
        result.append(item)
    return result
