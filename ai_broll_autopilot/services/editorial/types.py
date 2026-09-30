"""Type definitions and data contracts for the AI Editorial Intelligence Pipeline.

Defines schemas for hook candidates, editorial moment maps, contextual B-roll scoring,
sound design events, structured edit specifications, and quality audit reports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class NarrativeRole(str, Enum):
    """Narrative function of an editorial moment or B-roll cutaway."""
    HOOK = "HOOK"
    SETUP = "SETUP"
    CLAIM = "CLAIM"
    EXPLANATION = "EXPLANATION"
    EXAMPLE = "EXAMPLE"
    REVEAL = "REVEAL"
    CONTRAST = "CONTRAST"
    STORY = "STORY"
    REACTION = "REACTION"
    STATISTIC = "STATISTIC"
    PAYOFF = "PAYOFF"
    CTA = "CTA"


class BrollNarrativeRole(str, Enum):
    """Justification answering 'Why is this visual here?'."""
    ILLUSTRATE = "ILLUSTRATE"
    REINFORCE = "REINFORCE"
    CONTRAST = "CONTRAST"
    EXPLAIN = "EXPLAIN"
    EMPHASIZE = "EMPHASIZE"
    REVEAL = "REVEAL"
    RESET_VISUAL_FATIGUE = "RESET_VISUAL_FATIGUE"


class SentimentCategory(str, Enum):
    """Emotional polarity and tone of the spoken discourse."""
    NEGATIVE = "negative"      # damage, loss, error, stress, conflict, decline
    POSITIVE = "positive"      # growth, celebration, progress, achievement
    TENSION = "tension"        # uncertainty, pressure, suspense, conflict
    REFLECTIVE = "reflective"  # philosophical, slower, atmospheric, contemplative
    FUNNY = "funny"            # comedic, absurd, ironic
    TECHNICAL = "technical"    # code, interfaces, architecture, diagrams
    NEUTRAL = "neutral"        # standard objective narration


class PacingCategory(str, Enum):
    """Adaptive pacing requirement determining clip cut lengths."""
    HIGH_ENERGY = "high_energy"            # ~2-3 sec
    NORMAL = "normal"                      # ~3-5 sec
    DEEP_EXPLANATION = "deep_explanation"  # ~4-6 sec
    REFLECTIVE = "reflective"              # ~6-8 sec


class SfxEventType(str, Enum):
    """Editorial event classifications for sound design."""
    REVEAL = "REVEAL"                      # subtle impact / hit
    STATISTIC = "STATISTIC"                # restrained accent
    SUCCESS = "SUCCESS"                    # positive accent
    FAILURE = "FAILURE"                    # low impact / drop
    SHOCK = "SHOCK"                        # stronger impact / braam
    QUESTION = "QUESTION"                  # tension / riser
    TEXT_POPUP = "TEXT_POPUP"              # pop / click
    FAST_TRANSITION = "FAST_TRANSITION"    # whoosh
    EMOTIONAL_MOMENT = "EMOTIONAL_MOMENT"  # restrained cinematic texture
    COMEDIC_MOMENT = "COMEDIC_MOMENT"      # comedic accent


class ShotType(str, Enum):
    """Visual framing category for visual variety enforcement."""
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    DETAIL = "detail"
    SCREEN = "screen"
    GRAPHIC = "graphic"


# ---------------------------------------------------------------------------
# Hook Candidate Data Contracts
# ---------------------------------------------------------------------------

@dataclass
class HookScoreBreakdown:
    """Detailed score breakdown across hook evaluation dimensions (0-100 scale)."""
    curiosity_gap: float = 50.0
    emotional_intensity: float = 50.0
    specificity: float = 50.0
    standalone_context: float = 50.0
    strong_claim: float = 50.0
    surprise_interrupt: float = 50.0
    narrative_importance: float = 50.0
    clarity: float = 50.0
    penalties: float = 0.0
    final_score: float = 50.0
    explanation: str = ""


@dataclass
class HookCandidate:
    """Contiguous transcript segment evaluated as a potential video opening."""
    candidate_id: str
    start_time: float
    end_time: float
    duration: float
    raw_text: str
    tightened_text: str
    retention_purpose: str  # e.g., 'CURIOSITY_GAP', 'STRONG_CLAIM', 'TENSION'
    retention_reason: str
    scores: HookScoreBreakdown
    is_opening: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": round(self.duration, 2),
            "raw_text": self.raw_text,
            "tightened_text": self.tightened_text,
            "retention_purpose": self.retention_purpose,
            "retention_reason": self.retention_reason,
            "scores": {
                "curiosity_gap": round(self.scores.curiosity_gap, 1),
                "emotional_intensity": round(self.scores.emotional_intensity, 1),
                "specificity": round(self.scores.specificity, 1),
                "standalone_context": round(self.scores.standalone_context, 1),
                "strong_claim": round(self.scores.strong_claim, 1),
                "surprise_interrupt": round(self.scores.surprise_interrupt, 1),
                "narrative_importance": round(self.scores.narrative_importance, 1),
                "clarity": round(self.scores.clarity, 1),
                "penalties": round(self.scores.penalties, 1),
                "final_score": round(self.scores.final_score, 1),
                "explanation": self.scores.explanation,
            },
            "is_opening": self.is_opening,
        }


# ---------------------------------------------------------------------------
# Editorial Moment Map Contracts
# ---------------------------------------------------------------------------

@dataclass
class EditIntent:
    """Shared editorial attention allocation for one moment."""
    semantic_importance: float = 0.0
    emotional_importance: float = 0.0
    hook_relevance: float = 0.0
    speaker_emphasis: float = 0.0
    visual_opportunity: float = 0.0
    meme_opportunity: float = 0.0
    caption_energy: float = 0.0
    broll_pressure: float = 0.0
    sfx_opportunity: float = 0.0
    chaos_score: float = 0.0
    quietness_score: float = 1.0
    treatment: str = "normal"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "semantic_importance": round(self.semantic_importance, 3),
            "emotional_importance": round(self.emotional_importance, 3),
            "hook_relevance": round(self.hook_relevance, 3),
            "speaker_emphasis": round(self.speaker_emphasis, 3),
            "visual_opportunity": round(self.visual_opportunity, 3),
            "meme_opportunity": round(self.meme_opportunity, 3),
            "caption_energy": round(self.caption_energy, 3),
            "broll_pressure": round(self.broll_pressure, 3),
            "sfx_opportunity": round(self.sfx_opportunity, 3),
            "chaos_score": round(self.chaos_score, 3),
            "quietness_score": round(self.quietness_score, 3),
            "treatment": self.treatment,
            "reason": self.reason,
        }


class EditorialMoment:
    """Granular narrative unit representing an editorial beat in the speech."""
    moment_id: str
    start_time: float
    end_time: float
    duration: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    semantic_topic: str = ""
    entities: List[str] = field(default_factory=list)
    action: str = ""
    sentiment: SentimentCategory = SentimentCategory.NEUTRAL
    emotional_intensity: float = 0.5  # 0.0 to 1.0
    speaker_emphasis: float = 0.5    # 0.0 to 1.0
    narrative_role: NarrativeRole = NarrativeRole.EXPLANATION
    information_density: float = 0.5 # 0.0 to 1.0
    visual_opportunity: float = 0.5  # 0.0 to 1.0
    pacing_requirement: PacingCategory = PacingCategory.NORMAL
    recommended_duration: float = 3.5
    visual_processing_load: float = 0.5
    energy_level: float = 0.5        # 0.0 to 1.0
    edit_intent: Optional[EditIntent] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moment_id": self.moment_id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": round(self.duration, 2),
            "text": self.text,
            "semantic_topic": self.semantic_topic,
            "entities": self.entities,
            "action": self.action,
            "sentiment": self.sentiment.value,
            "emotional_intensity": round(self.emotional_intensity, 2),
            "speaker_emphasis": round(self.speaker_emphasis, 2),
            "narrative_role": self.narrative_role.value,
            "information_density": round(self.information_density, 2),
            "visual_opportunity": round(self.visual_opportunity, 2),
            "pacing_requirement": self.pacing_requirement.value,
            "recommended_duration": round(self.recommended_duration, 2),
            "visual_processing_load": round(self.visual_processing_load, 2),
            "energy_level": round(self.energy_level, 2),
            "edit_intent": self.edit_intent.to_dict() if self.edit_intent else None,
        }


# ---------------------------------------------------------------------------
# Contextual B-Roll Evaluation Contracts
# ---------------------------------------------------------------------------

@dataclass
class BrollCandidateScore:
    """Multi-metric evaluation for candidate B-roll footage."""
    semantic_match: float = 0.0
    sentiment_match: float = 0.0
    action_match: float = 0.0
    narrative_match: float = 0.0
    visual_quality: float = 0.8
    freshness: float = 1.0
    duration_fit: float = 1.0
    variety_penalty: float = 0.0
    final_score: float = 0.0
    confidence: float = 0.0
    decision: Literal["ACCEPT", "REJECT", "RETAIN_A_ROLL"] = "RETAIN_A_ROLL"
    rejection_reason: Optional[str] = None


@dataclass
class ContextualBrollDecision:
    """Complete editorial decision for a B-roll cutaway."""
    shot_id: str
    moment_id: str
    start_time: float
    end_time: float
    duration: float
    narrative_role: BrollNarrativeRole
    reason: str
    search_query: str
    emotional_intent: str
    pacing_category: PacingCategory
    scores: BrollCandidateScore
    asset_path: Optional[str] = None
    asset_name: Optional[str] = None
    shot_type: ShotType = ShotType.MEDIUM
    subject_category: str = "general"
    status: Literal["planned", "matched", "retained_a_roll", "rejected"] = "planned"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "moment_id": self.moment_id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": round(self.duration, 2),
            "narrative_role": self.narrative_role.value,
            "reason": self.reason,
            "search_query": self.search_query,
            "emotional_intent": self.emotional_intent,
            "pacing_category": self.pacing_category.value,
            "shot_type": self.shot_type.value,
            "subject_category": self.subject_category,
            "confidence": round(self.scores.confidence, 2),
            "final_score": round(self.scores.final_score, 2),
            "status": self.status,
            "asset_path": self.asset_path,
        }


# ---------------------------------------------------------------------------
# Sound Design Contracts
# ---------------------------------------------------------------------------

@dataclass
class SfxCueDecision:
    """Editorially selected and temporally synchronized sound effect."""
    cue_id: str
    event_type: SfxEventType
    timestamp: float
    duration: float
    sound_name: str
    sound_file: str
    volume: float
    reason: str
    emotional_compatibility: float
    synced_with: Literal["caption", "broll_entrance", "punch_in", "reveal", "statistic"] = "broll_entrance"
    target_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "event_type": self.event_type.value,
            "timestamp": round(self.timestamp, 2),
            "duration": round(self.duration, 2),
            "sound_name": self.sound_name,
            "sound_file": self.sound_file,
            "volume": round(self.volume, 2),
            "reason": self.reason,
            "emotional_compatibility": round(self.emotional_compatibility, 2),
            "synced_with": self.synced_with,
            "target_id": self.target_id,
        }


# ---------------------------------------------------------------------------
# Structured Edit Specification Contracts
# ---------------------------------------------------------------------------

@dataclass
class EditorialSegmentSpec:
    """Timeline slice with narrative and emotional characteristics."""
    segment_id: str
    role: NarrativeRole
    sentiment: SentimentCategory
    energy: float
    start_time: float
    duration: float
    text: str


@dataclass
class EditorialCaptionSpec:
    """High-impact animated caption overlay."""
    caption_id: str
    text: str
    start_time: float
    duration: float
    position: str = "center"
    style: str = "bold_impact"
    behind_subject: bool = False
    highlight_color: str = "#FFDD00"


@dataclass
class EditorialCameraSpec:
    """Dynamic punch-in camera keyframe."""
    camera_id: str
    timestamp: float
    scale: float
    duration: float = 0.3
    reason: str = "emphasis"


@dataclass
class EditorialEditSpecification:
    """The master declarative edit specification emitted by Stockpile for Diffusion Studio."""
    spec_id: str
    title: str
    total_duration: float
    hook: HookCandidate
    moments: List[EditorialMoment]
    broll_shots: List[ContextualBrollDecision]
    captions: List[EditorialCaptionSpec]
    sfx_cues: List[SfxCueDecision]
    camera_moves: List[EditorialCameraSpec]
    energy_curve: List[Dict[str, float]]
    edit_intents: List[EditIntent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "title": self.title,
            "total_duration": round(self.total_duration, 2),
            "hook": self.hook.to_dict(),
            "moments": [m.to_dict() for m in self.moments],
            "broll_shots": [s.to_dict() for s in self.broll_shots],
            "captions": [
                {
                    "id": c.caption_id,
                    "text": c.text,
                    "start": round(c.start_time, 2),
                    "duration": round(c.duration, 2),
                    "position": c.position,
                    "behind_subject": c.behind_subject,
                    "highlight_color": c.highlight_color,
                }
                for c in self.captions
            ],
            "sfx_cues": [s.to_dict() for s in self.sfx_cues],
            "camera_moves": [
                {
                    "id": cm.camera_id,
                    "time": round(cm.timestamp, 2),
                    "scale": round(cm.scale, 2),
                    "duration": round(cm.duration, 2),
                    "reason": cm.reason,
                }
                for cm in self.camera_moves
            ],
            "energy_curve": self.energy_curve,
            "edit_intents": [i.to_dict() for i in self.edit_intents],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Quality Audit Gate Contracts
# ---------------------------------------------------------------------------

@dataclass
class QualityCheckItem:
    name: str
    category: Literal["hook", "broll", "sfx", "pacing", "captions", "overall"]
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    severity: Literal["error", "warning", "info"] = "info"


@dataclass
class QualityAuditReport:
    passed: bool
    overall_score: float  # 0.0 to 1.0
    checks: List[QualityCheckItem]
    recommendations: List[str] = field(default_factory=list)
    repaired_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "overall_score": round(self.overall_score, 2),
            "checks": [
                {
                    "name": c.name,
                    "category": c.category,
                    "passed": c.passed,
                    "score": round(c.score, 2),
                    "message": c.message,
                    "severity": c.severity,
                }
                for c in self.checks
            ],
            "recommendations": self.recommendations,
            "repaired_items": self.repaired_items,
        }
