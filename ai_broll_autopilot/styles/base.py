"""Style Profile System for Stockpile.

Defines visual aesthetics, typography, caption animations, pacing, and color palettes
compatible with OpenReel's rendering engine and timeline specifications.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class StyleProfile:
    """A visual aesthetic profile defining styling for captions, overlays, transitions, and pacing."""
    id: str
    name: str
    description: str = ""

    # Typography & Subtitles
    font_family: str = "Montserrat"
    font_size: int = 54
    font_weight: str = "bold"            # "bold", "800", "900", "normal"
    font_style: str = "normal"           # "normal", "italic"
    primary_color: str = "#FFFFFF"       # Main text color
    highlight_color: str = "#FFDD00"     # Spoken/highlighted word color
    upcoming_color: str = "rgba(255, 255, 255, 0.7)" # Upcoming word color
    background_color: str = "transparent" # Subtitle box background
    stroke_color: Optional[str] = "#000000" # Stroke/outline color
    stroke_width: Optional[int] = 4       # Stroke width in pixels
    shadow_color: Optional[str] = "rgba(0, 0, 0, 0.75)"
    shadow_blur: Optional[int] = 6
    caption_animation_style: str = "word-highlight" # "word-highlight", "bounce", "word-by-word", "karaoke", "typewriter", "none"
    caption_position: str = "bottom"     # "bottom", "center", "top"

    # Editorial & Pacing
    broll_cut_pacing: str = "dynamic"    # "rapid", "dynamic", "moderate", "smooth"
    default_broll_duration: float = 2.4  # Default seconds for a B-roll cutaway
    zoom_intensity: float = 1.06         # Subtle punch-in scale factor for emphatic speech
    transition_type: str = "cut"         # "cut", "crossfade", "slide", "zoom", "glitch", "whip"
    color_grading_preset: Optional[str] = None # e.g. "punchy_contrast", "cinematic_warm", "cool_tech"

    # Audio Mix
    sound_effects_enabled: bool = True
    bgm_ducking_volume: float = 0.15     # Music volume during active speech (0.0 to 1.0)
    bgm_normal_volume: float = 0.35      # Music volume during music-forward moments

    def to_dict(self) -> Dict[str, Any]:
        """Convert style profile to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "font_style": self.font_style,
            "primary_color": self.primary_color,
            "highlight_color": self.highlight_color,
            "upcoming_color": self.upcoming_color,
            "background_color": self.background_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "shadow_color": self.shadow_color,
            "shadow_blur": self.shadow_blur,
            "caption_animation_style": self.caption_animation_style,
            "caption_position": self.caption_position,
            "broll_cut_pacing": self.broll_cut_pacing,
            "default_broll_duration": self.default_broll_duration,
            "zoom_intensity": self.zoom_intensity,
            "transition_type": self.transition_type,
            "color_grading_preset": self.color_grading_preset,
            "sound_effects_enabled": self.sound_effects_enabled,
            "bgm_ducking_volume": self.bgm_ducking_volume,
            "bgm_normal_volume": self.bgm_normal_volume,
        }

    def to_openreel_subtitle_style(self) -> Dict[str, Any]:
        """Generate OpenReel native SubtitleStyle object matching packages/core/src/types/timeline.ts."""
        style: Dict[str, Any] = {
            "fontFamily": self.font_family,
            "fontSize": self.font_size,
            "color": self.primary_color,
            "backgroundColor": self.background_color,
            "position": self.caption_position,
        }
        if self.highlight_color:
            style["highlightColor"] = self.highlight_color
        if self.upcoming_color:
            style["upcomingColor"] = self.upcoming_color
        return style

    def to_openreel_text_style(self) -> Dict[str, Any]:
        """Generate OpenReel native TextStyle object matching packages/core/src/text/types.ts."""
        return {
            "fontFamily": self.font_family,
            "fontSize": self.font_size,
            "fontWeight": self.font_weight if self.font_weight in ["normal", "bold"] else "bold",
            "fontStyle": self.font_style,
            "color": self.primary_color,
            "backgroundColor": self.background_color if self.background_color != "transparent" else None,
            "strokeColor": self.stroke_color,
            "strokeWidth": self.stroke_width,
            "shadowColor": self.shadow_color,
            "shadowBlur": self.shadow_blur,
            "textAlign": "center",
            "verticalAlign": "middle",
            "lineHeight": 1.2,
            "letterSpacing": 0.5,
        }
