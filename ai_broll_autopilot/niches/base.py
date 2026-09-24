"""Niche Profile System for Stockpile.

Defines content profiles across diverse domains (sports, business, tech, gaming, etc.)
independent of any specific campaign or creator.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class NicheEditingPreferences:
    """Editing behavior preferences tailored to a specific content niche."""
    pace: str = "dynamic"                  # "fast", "dynamic", "moderate", "calm"
    cut_frequency: str = "contextual"      # "rapid", "contextual", "sparse"
    broll_frequency: str = "contextual"    # "high", "contextual", "minimal"
    caption_style: str = "bold"            # "bold", "clean", "minimal", "playful"
    transition_style: str = "minimal"      # "minimal", "punchy", "smooth"
    zoom_style: str = "subtle"             # "none", "subtle", "dynamic"
    max_broll_ratio: float = 0.35          # Maximum ratio of video duration covered by B-roll
    meme_cutaways: bool = False            # Allow contextual meme cutaways if appropriate


@dataclass
class NicheProfile:
    """Reusable semantic profile describing content subject matter and visual vocabulary."""
    id: str
    name: str
    parent_niche: str                      # "sports", "business", "technology", "gaming", "entertainment", "general"
    visual_keywords: List[str] = field(default_factory=list)
    broll_categories: List[str] = field(default_factory=list)
    preferred_energy: str = "medium"       # "high", "medium", "calm"
    editing: NicheEditingPreferences = field(default_factory=NicheEditingPreferences)
    avoid: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_niche": self.parent_niche,
            "visual_keywords": self.visual_keywords,
            "broll_categories": self.broll_categories,
            "preferred_energy": self.preferred_energy,
            "editing": {
                "pace": self.editing.pace,
                "cut_frequency": self.editing.cut_frequency,
                "broll_frequency": self.editing.broll_frequency,
                "caption_style": self.editing.caption_style,
                "transition_style": self.editing.transition_style,
                "zoom_style": self.editing.zoom_style,
                "max_broll_ratio": self.editing.max_broll_ratio,
                "meme_cutaways": self.editing.meme_cutaways,
            },
            "avoid": self.avoid,
            "description": self.description,
        }
