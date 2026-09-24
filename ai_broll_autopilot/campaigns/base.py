"""Base campaign models and specifications for AI B-Roll Autopilot."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class CuratedMoment:
    """Pre-curated timestamped moment from campaign guidelines."""
    moment_id: str             # e.g. "C45"
    timestamp_range: str       # e.g. "01:07:12-01:08:21"
    start_time_sec: float      # e.g. 4032.0
    end_time_sec: float        # e.g. 4101.0
    screen_hook: str           # e.g. "TRAE SAYS KNICKS FANS STARTED THE RIVALRY"
    post_caption: str          # e.g. "Trae says New York started it..."
    broll_theme: Optional[str] = None
    broll_sources: List[str] = field(default_factory=list)
    angle: Optional[str] = None
    youtube_url: Optional[str] = None


@dataclass
class CampaignConfig:
    """Complete specification governing a video clipping campaign."""
    id: str
    name: str
    client: str
    rate: str
    total_budget: str
    platforms: List[str]
    description: str
    episode_url: Optional[str] = None

    # Video specs
    target_width: int = 1080
    target_height: int = 1920
    duration_min: float = 20.0
    duration_max: float = 60.0
    target_duration: float = 35.0

    # Audio rules
    allow_bgm: bool = True
    bgm_genre: Optional[str] = None
    preserve_dialogue_only: bool = False

    # Visual & B-roll rules
    allow_ai_broll: bool = True
    max_broll_ratio: float = 0.60
    max_cutaway_seconds: float = 2.5
    speed_multiplier: float = 1.0

    # Frame Overlay & Framing rules
    frame_overlay_required: bool = False
    frame_viewport: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)

    # Watermark rules
    watermark_required: bool = False
    watermark_asset_path: Optional[str] = None
    watermark_position: str = "bottom_safe"  # "bottom_safe", "top_safe", "center"
    watermark_scale: float = 0.28
    watermark_x_offset: int = 0
    watermark_y_offset: int = -220

    # Subtitles & Hook rules
    subtitles_required: bool = True
    subtitle_style: str = "hormozi"
    subtitle_position: str = "bottom"
    subtitle_margin_v: int = 280
    hook_required: bool = True
    hook_position: str = "top"

    # Rules and instant rejection guidelines
    rules_checklist: List[str] = field(default_factory=list)
    instant_rejections: List[str] = field(default_factory=list)

    # Prompt overrides
    director_system_prompt: Optional[str] = None

    # Pre-curated moments catalog
    curated_moments: List[CuratedMoment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration for REST API and web UI consumption."""
        return {
            "id": self.id,
            "name": self.name,
            "client": self.client,
            "rate": self.rate,
            "total_budget": self.total_budget,
            "platforms": self.platforms,
            "description": self.description,
            "episode_url": self.episode_url,
            "target_width": self.target_width,
            "target_height": self.target_height,
            "duration_min": self.duration_min,
            "duration_max": self.duration_max,
            "target_duration": self.target_duration,
            "allow_bgm": self.allow_bgm,
            "preserve_dialogue_only": self.preserve_dialogue_only,
            "allow_ai_broll": self.allow_ai_broll,
            "max_broll_ratio": self.max_broll_ratio,
            "max_cutaway_seconds": self.max_cutaway_seconds,
            "frame_overlay_required": self.frame_overlay_required,
            "frame_viewport": self.frame_viewport,
            "watermark_required": self.watermark_required,
            "watermark_position": self.watermark_position,
            "subtitle_style": self.subtitle_style,
            "subtitle_position": self.subtitle_position,
            "hook_required": self.hook_required,
            "rules_checklist": self.rules_checklist,
            "instant_rejections": self.instant_rejections,
            "curated_moments": [
                {
                    "moment_id": m.moment_id,
                    "timestamp_range": m.timestamp_range,
                    "start_time_sec": m.start_time_sec,
                    "end_time_sec": m.end_time_sec,
                    "screen_hook": m.screen_hook,
                    "post_caption": m.post_caption,
                    "broll_theme": m.broll_theme,
                    "broll_sources": m.broll_sources,
                    "angle": m.angle,
                    "youtube_url": m.youtube_url or (f"https://www.youtube.com/watch?v=uf0q07QagUs&t={int(m.start_time_sec)}s")
                }
                for m in self.curated_moments
            ]
        }
