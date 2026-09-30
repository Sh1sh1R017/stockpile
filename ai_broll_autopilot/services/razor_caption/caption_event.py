"""CaptionEvent — core data contract for the Rapid Razor Caption Engine.

Every word that appears on screen is represented as a CaptionEvent.  The engine
never deals with raw text strings after this point; all downstream stages
(segmenter, importance scorer, spatial engine, state machine) operate on these
typed objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CaptionMode(str, Enum):
    """User-selectable caption mode.  RAPID_RAZOR is NOT applied automatically everywhere."""
    RAPID_RAZOR = "rapid_razor"
    NORMAL = "normal"
    MINIMAL = "minimal"
    USER_STYLE = "user_style"


class EmphasisLevel(int, Enum):
    """Hierarchical emphasis — never emphasize everything."""
    NORMAL = 0      # plain display
    MODERATE = 1    # slight weight / size lift
    STRONG = 2      # accent color + scale
    HOOK = 3        # accent + scale + animation + optional behind-subject


class CaptionState(str, Enum):
    """State machine for each caption event lifecycle."""
    IDLE = "idle"
    ENTERING = "entering"
    VISIBLE = "visible"
    EMPHASIZED = "emphasized"
    EXITING = "exiting"
    COMPLETE = "complete"


class AnimationType(str, Enum):
    """Entry / exit animation primitives.  Duration: 80–250 ms."""
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
    """9-region layout grid.  Never random — always editorially justified."""
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
    BEHIND_SUBJECT = "behind_subject"   # BACKGROUND → CAPTION → SUBJECT_MASK


# ---------------------------------------------------------------------------
# Core dataclass
# ---------------------------------------------------------------------------

@dataclass
class CaptionEvent:
    """A single editorially-meaningful word or phrase unit on the timeline.

    Produced by the Segmenter, enriched by ImportanceScorer, positioned by
    SpatialEngine, and driven through the StateMachine during playback.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    word: str = ""

    # ── Timing (seconds, wall-clock in the rendered output) ───────────────
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0           # computed: end_time - start_time

    # ── Source transcript metadata ─────────────────────────────────────────
    confidence: float = 1.0
    speaker: str = "default"
    sentence_id: int = 0
    phrase_id: int = 0

    # ── Editorial importance (0.0 → 1.0) ─────────────────────────────────
    semantic_importance: float = 0.0
    emotional_importance: float = 0.0
    novelty: float = 0.0
    numeric_value: bool = False       # contains a number
    named_entity: bool = False        # proper noun / brand / person
    action_word: bool = False         # verb / call-to-action
    hook_relevance: float = 0.0       # proximity to hook phrase
    speaker_emphasis: float = 0.0     # prosody / pitch / loudness signal
    word_importance_score: float = 0.0  # composite 0.0–1.0

    # ── Emphasis ──────────────────────────────────────────────────────────
    emphasis: EmphasisLevel = EmphasisLevel.NORMAL
    emotion: str = "neutral"          # e.g. "surprise", "anger", "joy"

    # ── Segmentation ──────────────────────────────────────────────────────
    segment_break_before: bool = False  # razor cut lands before this word
    segment_break_reason: str = ""      # why: "pause", "semantic", "emphasis", "sentence_boundary"

    # ── Spatial placement ─────────────────────────────────────────────────
    region: SpatialRegion = SpatialRegion.LOWER_CENTER
    position_x: float = 0.5          # normalized 0–1
    position_y: float = 0.85         # normalized 0–1
    position_reason: str = ""         # editorial justification

    # ── Compositing ───────────────────────────────────────────────────────
    layer: LayerMode = LayerMode.ABOVE_SUBJECT
    subject_id: Optional[str] = None
    collision_resolved: bool = False
    alternate_region: Optional[SpatialRegion] = None

    # ── Animation ─────────────────────────────────────────────────────────
    enter_animation: AnimationType = AnimationType.SNAP
    exit_animation: AnimationType = AnimationType.SNAP
    enter_duration_ms: int = 120
    exit_duration_ms: int = 80
    emphasis_scale: float = 1.0       # 1.0 = no scale

    # ── Typography ────────────────────────────────────────────────────────
    font_weight: str = "Bold"         # Normal / Bold / ExtraBold / Black
    font_size_scale: float = 1.0      # relative to base size
    tracking: float = 0.0             # letter-spacing em units
    line_height: float = 1.2
    uppercase: bool = True
    fill_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    accent_color: str = "#FFE600"     # used for STRONG / HOOK
    opacity: float = 1.0
    rotation_deg: float = 0.0

    # ── SFX ───────────────────────────────────────────────────────────────
    sfx_event: Optional[str] = None   # e.g. "KEYWORD_POP", "TEXT_SNAP", "MAJOR_HOOK"

    # ── Music beat alignment ───────────────────────────────────────────────
    beat_aligned: bool = False
    nearest_beat_time: Optional[float] = None

    # ── ZapCap Semantic & Style Metadata ──────────────────────────────────
    semantic_type: str = "normal"     # "normal", "hook", "money", "number", "negation", "action", "cta"
    emoji: Optional[str] = None       # e.g. "💵", "🎰", "⏳", "❌", "🎯", "🔄", "🧠", "🔥"
    style_preset: str = "hormozi"
    color_palette: Optional[Dict[str, str]] = None

    # ── State machine ─────────────────────────────────────────────────────
    state: CaptionState = CaptionState.IDLE

    # ── Energy context ─────────────────────────────────────────────────────
    energy: EnergyLevel = EnergyLevel.MEDIUM

    # ── Mode ──────────────────────────────────────────────────────────────
    mode: CaptionMode = CaptionMode.RAPID_RAZOR

    def to_edit_plan_entry(self) -> Dict[str, Any]:
        """Serialize to the EditPlan razor_captions schema."""
        return {
            "type": "caption",
            "mode": self.mode.value,
            "text": self.word,
            "word": self.word,
            "start": round(self.start_time, 4),
            "end": round(self.end_time, 4),
            "importance": round(self.word_importance_score, 3),
            "semantic_type": self.semantic_type,
            "emoji": self.emoji,
            "style_preset": self.style_preset,
            "color_palette": self.color_palette or {
                "main": self.fill_color,
                "second": self.accent_color,
                "third": "#00FF66",
            },
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
