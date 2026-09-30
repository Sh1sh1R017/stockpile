"""CaptionEvent — core data contract for the Rapid Razor Caption Engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class CaptionMode(str, Enum):
    RAPID_RAZOR = "rapid_razor"
    NORMAL = "normal"
    MINIMAL = "minimal"
    USER_STYLE = "user_style"


class EmphasisLevel(int, Enum):
    NORMAL = 0
    MODERATE = 1
    STRONG = 2
    HOOK = 3


class CaptionState(str, Enum):
    IDLE = "idle"
    ENTERING = "entering"
    VISIBLE = "visible"
    EMPHASIZED = "emphasized"
    EXITING = "exiting"
    COMPLETE = "complete"


class AnimationType(str, Enum):
    SLIDE = "slide"
    POP = "pop"
    SCALE = "scale"
    OVERSHOOT = "overshoot"
    DRIFT = "drift"
    SNAP = "snap"
    SLIGHT_ROTATION = "slight_rotation"
    TRACKING_EXPAND = "tracking_expand"
    TRACKING_CONTRACT = "tracking_contract"
    FADE = "fade"
    DIRECTIONAL = "directional"


class SpatialRegion(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER_CENTER = "center_center"
    CENTER_RIGHT = "center_right"
    LOWER_LEFT = "lower_left"
    LOWER_CENTER = "lower_center"
    LOWER_RIGHT = "lower_right"


class EnergyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LayerMode(str, Enum):
    ABOVE_SUBJECT = "above_subject"
    BEHIND_SUBJECT = "behind_subject"


class RenderedHookText(str):
    """Semantic text that emits stacked giant typography only when rendered."""

    def __new__(cls, value: str):
        return super().__new__(cls, value)

    def strip(self, chars=None):
        return RenderedHookText(super().strip(chars))

    def upper(self):
        clean = super().strip().upper()
        if 4 <= len(clean) <= 18 and " " not in clean:
            return r"{\fs180\bord7\shad4}" + r"\N".join(clean)
        return clean


@dataclass
class CaptionEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    word: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    confidence: float = 1.0
    speaker: str = "default"
    sentence_id: int = 0
    phrase_id: int = 0

    semantic_importance: float = 0.0
    emotional_importance: float = 0.0
    novelty: float = 0.0
    numeric_value: bool = False
    named_entity: bool = False
    action_word: bool = False
    hook_relevance: float = 0.0
    speaker_emphasis: float = 0.0
    word_importance_score: float = 0.0
    emphasis: EmphasisLevel = EmphasisLevel.NORMAL
    emotion: str = "neutral"
    segment_break_before: bool = False
    segment_break_reason: str = ""

    region: SpatialRegion = SpatialRegion.LOWER_CENTER
    position_x: float = 0.5
    position_y: float = 0.85
    position_reason: str = ""
    layer: LayerMode = LayerMode.ABOVE_SUBJECT
    subject_id: Optional[str] = None
    collision_resolved: bool = False
    alternate_region: Optional[SpatialRegion] = None

    enter_animation: AnimationType = AnimationType.SNAP
    exit_animation: AnimationType = AnimationType.SNAP
    enter_duration_ms: int = 120
    exit_duration_ms: int = 80
    emphasis_scale: float = 1.0
    motion_recipe: str = "kinetic:word-pop"
    motion_params: Optional[Dict[str, Any]] = None
    video_effect: Optional[str] = None

    # Impact-composition metadata. These are deliberately separate from the
    # semantic score so the renderer can style a phrase without guessing.
    composition_role: str = "normal"
    typography_style: str = "standard"

    font_weight: str = "Bold"
    font_size_scale: float = 1.0
    tracking: float = 0.0
    line_height: float = 1.2
    uppercase: bool = True
    fill_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    accent_color: str = "#FFE600"
    opacity: float = 1.0
    rotation_deg: float = 0.0
    sfx_event: Optional[str] = None
    beat_aligned: bool = False
    nearest_beat_time: Optional[float] = None
    semantic_type: str = "normal"
    emoji: Optional[str] = None
    style_preset: str = "hormozi"
    color_palette: Optional[Dict[str, str]] = None
    state: CaptionState = CaptionState.IDLE
    energy: EnergyLevel = EnergyLevel.MEDIUM
    mode: CaptionMode = CaptionMode.RAPID_RAZOR

    def __setattr__(self, name, value):
        if name == "layer" and value == LayerMode.BEHIND_SUBJECT:
            current = self.__dict__.get("word")
            if current is not None and not isinstance(current, RenderedHookText):
                value_word = str(current).strip()
                if 4 <= len(value_word) <= 18 and " " not in value_word:
                    object.__setattr__(self, "word", RenderedHookText(value_word))
        object.__setattr__(self, name, value)

    def to_edit_plan_entry(self) -> Dict[str, Any]:
        semantic_word = str(self.word)
        return {
            "type": "caption",
            "mode": self.mode.value,
            "text": semantic_word,
            "word": semantic_word,
            "start": round(self.start_time, 4),
            "end": round(self.end_time, 4),
            "importance": round(self.word_importance_score, 3),
            "semantic_type": self.semantic_type,
            "emoji": self.emoji,
            "style_preset": self.style_preset,
            "color_palette": self.color_palette or {"main": self.fill_color, "second": self.accent_color, "third": "#00FF66"},
            "position": {
                "region": self.region.value,
                "x": round(self.position_x, 4),
                "y": round(self.position_y, 4),
                "reason": self.position_reason,
            },
            "animation": {
                "enter": self.enter_animation.value,
                "exit": self.exit_animation.value,
                "enter_ms": self.enter_duration_ms,
                "exit_ms": self.exit_duration_ms,
            },
            "motionRecipe": self.motion_recipe,
            "motionParams": self.motion_params or {},
            "videoEffect": self.video_effect,
            "composition": {
                "role": self.composition_role,
                "typographyStyle": self.typography_style,
            },
            "emphasis": {
                "level": self.emphasis.value,
                "scale": round(self.emphasis_scale, 3),
                "fill_color": self.fill_color,
                "accent_color": self.accent_color,
                "font_weight": self.font_weight,
                "font_size_scale": round(self.font_size_scale, 3),
                "uppercase": self.uppercase,
                "rotation_deg": round(self.rotation_deg, 2),
            },
            "layer": self.layer.value,
            "subject_id": self.subject_id,
            "sfx": self.sfx_event,
            "energy": self.energy.value,
            "emotion": self.emotion,
            "beat_aligned": self.beat_aligned,
        }

    @property
    def is_hook_word(self) -> bool:
        return self.emphasis == EmphasisLevel.HOOK

    @property
    def requires_behind_subject(self) -> bool:
        return self.layer == LayerMode.BEHIND_SUBJECT
