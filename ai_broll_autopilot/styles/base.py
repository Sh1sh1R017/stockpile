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
    editorial_guidelines: List[str] = field(default_factory=list)

    # Reference-style editorial controls
    reference_style: bool = False
    broll_target_ratio: Optional[float] = None
    caption_words_per_group: int = 3
    caption_y_percent: float = 58.0
    broll_min_duration: float = 0.8
    broll_max_duration: float = 2.2
    max_continuous_aroll_seconds: float = 3.5
    max_zoom_scale: float = 1.05
    hero_broll_max_duration: float = 2.6

    # Reference-edit cadence controls. These model the supplied final edit's
    # rhythm: short visual punctuation, normal contextual holds, and occasional
    # long hero scenes.
    micro_broll_min_duration: float = 0.45
    micro_broll_max_duration: float = 0.85
    hero_broll_min_duration: float = 3.0
    hero_broll_target_ratio: float = 0.20
    visual_burst_window_seconds: float = 3.5
    visual_burst_min_cuts: int = 3
    semantic_callout_max: int = 4
    semantic_callout_min_duration: float = 0.7
    semantic_callout_max_duration: float = 2.8
    visual_container_scale: float = 0.944
    visual_container_width_ratio: float = 0.944
    visual_container_height_ratio: float = 0.574
    visual_container_radius: int = 52
    use_black_canvas: bool = False

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
            "editorial_guidelines": list(self.editorial_guidelines),
            "reference_style": self.reference_style,
            "broll_target_ratio": self.broll_target_ratio,
            "caption_words_per_group": self.caption_words_per_group,
            "caption_y_percent": self.caption_y_percent,
            "broll_min_duration": self.broll_min_duration,
            "broll_max_duration": self.broll_max_duration,
            "max_continuous_aroll_seconds": self.max_continuous_aroll_seconds,
            "micro_broll_min_duration": self.micro_broll_min_duration,
            "micro_broll_max_duration": self.micro_broll_max_duration,
            "hero_broll_min_duration": self.hero_broll_min_duration,
            "hero_broll_target_ratio": self.hero_broll_target_ratio,
            "visual_burst_window_seconds": self.visual_burst_window_seconds,
            "visual_burst_min_cuts": self.visual_burst_min_cuts,
            "semantic_callout_max": self.semantic_callout_max,
            "semantic_callout_min_duration": self.semantic_callout_min_duration,
            "semantic_callout_max_duration": self.semantic_callout_max_duration,
            "max_zoom_scale": self.max_zoom_scale,
            "hero_broll_max_duration": self.hero_broll_max_duration,
            "visual_container_scale": self.visual_container_scale,
            "visual_container_width_ratio": self.visual_container_width_ratio,
            "visual_container_height_ratio": self.visual_container_height_ratio,
            "visual_container_radius": self.visual_container_radius,
            "use_black_canvas": self.use_black_canvas,
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
