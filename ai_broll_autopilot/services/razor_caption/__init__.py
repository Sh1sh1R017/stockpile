"""Rapid Razor Caption Engine — word-level energetic caption system for short-form video."""

from .caption_event import CaptionEvent, CaptionMode, EmphasisLevel, CaptionState, AnimationType, SpatialRegion
from .engine import RazorCaptionEngine

__all__ = [
    "CaptionEvent",
    "CaptionMode",
    "EmphasisLevel",
    "CaptionState",
    "AnimationType",
    "SpatialRegion",
    "RazorCaptionEngine",
]
