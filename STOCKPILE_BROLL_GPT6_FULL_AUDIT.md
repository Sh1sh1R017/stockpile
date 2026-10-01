# STOCKPILE — GPT-6 FULL B-ROLL SOURCE AUDIT PACKET

Repository: Sh1sh1R017/stockpile
Source ref: gpt6/broll-source-dump (branched from main)

## INSTRUCTIONS FOR GPT-6

Audit the supplied source as one integrated B-roll pipeline AND perform the repo-wide audit appendix below. Do not invent functions or root causes. Trace exact call graphs before proposing patches. Preserve existing Stockpile features. Return concrete file/function-level diffs and regression tests.

## REQUIRED OUTPUT
1. Verified current call graph
2. Exact root causes with file/function names
3. Minimal patch plan
4. Concrete code/diff
5. Regression tests
6. Expected rendered behavior
7. Compatibility risks

## PRIMARY SOURCE FILES


============================================================
FILE: ai_broll_autopilot/services/editorial/types.py
============================================================

```python
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
    start_time: float = 0.0
    end_time: float = 0.0
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
    chaos_tier: str = "normal"
    chaos_budget_remaining: float = 1.0
    quietness_score: float = 1.0
    treatment: str = "normal"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
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
            "chaos_tier": self.chaos_tier,
            "chaos_budget_remaining": round(self.chaos_budget_remaining, 3),
            "quietness_score": round(self.quietness_score, 3),
            "treatment": self.treatment,
            "reason": self.reason,
        }


@dataclass
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

```

============================================================
FILE: ai_broll_autopilot/services/editorial/broll_intelligence.py
============================================================

```python
"""Contextual, Sentiment-Aware B-Roll Editorial Intelligence.

Evaluates B-roll cutaway candidates using multi-metric contextual scoring, aligns emotional sentiment,
assigns narrative justifications, computes short-form editorial durations, and rejects weak/generic
footage in favor of clean A-roll.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialMoment,
    NarrativeRole,
    PacingCategory,
    SentimentCategory,
    ShotType,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine

logger = logging.getLogger("autopilot.editorial.broll")


class BrollIntelligence:
    """Contextual and sentiment-aware B-roll decision engine."""

    SENTIMENT_FOOTAGE_MAPPINGS = {
        SentimentCategory.NEGATIVE: {
            "boost": ["stressed", "decline", "crash", "red chart", "loss", "head in hands", "empty", "dark", "rain", "frustrated", "error", "fire", "broken"],
            "penalize": ["celebrate", "laughing", "cheering", "beach", "party", "sunny", "fireworks", "champagne", "thumbs up"],
        },
        SentimentCategory.POSITIVE: {
            "boost": ["celebration", "growth", "green chart", "success", "handshake", "smiling", "high five", "trophy", "skyline", "bright", "cheering"],
            "penalize": ["crying", "ruins", "funeral", "depressed", "garbage", "dark alley", "poverty"],
        },
        SentimentCategory.TENSION: {
            "boost": ["suspense", "ticking clock", "shadow", "countdown", "intense eye", "whisper", "boardroom confrontation", "police lights", "running"],
            "penalize": ["relaxing", "spa", "sleeping", "picnic", "lazy"],
        },
        SentimentCategory.REFLECTIVE: {
            "boost": ["looking out window", "sunset", "walking alone", "nature", "silhouette", "slow motion", "coffee cup", "peaceful", "books"],
            "penalize": ["fast action", "explosion", "club", "laser", "sports slam dunk"],
        },
        SentimentCategory.TECHNICAL: {
            "boost": ["code", "software interface", "server room", "diagram", "circuit board", "data visualization", "keyboard typing", "screen ui"],
            "penalize": ["farm", "animals", "comedy", "beach", "forest"],
        },
        SentimentCategory.FUNNY: {
            "boost": ["facepalm", "laughing", "awkward look", "confused", "double take", "comic contrast"],
            "penalize": ["grave", "tragedy", "hospital", "war"],
        },
    }

    # A candidate must be genuinely useful; B-roll coverage is never the objective.
    ACCEPTANCE_THRESHOLD = 0.72
    MIN_SEMANTIC_SCORE = 0.58
    MIN_NARRATIVE_SCORE = 0.65

    # Generic/text-heavy stock is only acceptable when the narration specifically calls for it.
    GENERIC_VISUAL_TERMS = {
        "generic stock", "generic b roll", "random b roll", "stock footage",
        "news broadcast", "tv broadcast", "news studio", "powerpoint presentation",
        "business presentation", "generic dashboard", "generic chart", "generic graph",
        "random terminal", "code screen", "coding screen", "stock chart",
    }
    TEXT_HEAVY_TERMS = {
        "presentation", "powerpoint", "news broadcast", "news ticker", "headline montage",
        "text animation", "quote card", "title card", "infographic", "article screenshot",
    }

    def __init__(self, acceptance_threshold: float = ACCEPTANCE_THRESHOLD):
        self.acceptance_threshold = acceptance_threshold

    def evaluate_and_plan_shot(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        is_first_moment: bool = False,
    ) -> Optional[ContextualBrollDecision]:
        """Evaluate whether a moment justifies B-roll and select the most contextually relevant visual."""
        if is_first_moment or moment.start_time < 1.2:
            logger.debug(f"Moment [{moment.moment_id}] is the opening hook: retaining A-roll.")
            return None

        if moment.visual_opportunity < 0.40 and moment.speaker_emphasis >= 0.70:
            logger.info(f"Moment [{moment.moment_id}]: speaker emphasis wins over abstract B-roll.")
            return None

        narrative_role = self._assign_narrative_role(moment)
        reason = self._generate_role_reason(moment, narrative_role)
        target_duration = self._calculate_adaptive_duration(moment)
        shot_start = round(moment.start_time, 2)
        shot_end = round(min(moment.end_time, shot_start + target_duration), 2)
        actual_duration = round(max(0.0, shot_end - shot_start), 2)

        min_duration = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
        if actual_duration < min_duration:
            logger.debug(f"Moment [{moment.moment_id}]: only {actual_duration:.2f}s available; retain A-roll.")
            return None

        search_query = self._build_search_query(moment, narrative_role)

        if not available_assets:
            variety_engine.record_placed_shot(
                shot_id=f"shot_{moment.moment_id}",
                shot_type=ShotType.MEDIUM,
                subject_category=moment.semantic_topic or "editorial",
                camera_movement="dynamic",
                location="contextual",
                semantic_theme=moment.semantic_topic,
            )
            return ContextualBrollDecision(
                shot_id=f"broll_{moment.moment_id}",
                moment_id=moment.moment_id,
                start_time=shot_start,
                end_time=shot_end,
                duration=actual_duration,
                narrative_role=narrative_role,
                pacing_category=moment.pacing_requirement,
                shot_type=ShotType.MEDIUM,
                subject_category=moment.semantic_topic or "editorial",
                search_query=search_query,
                asset_path=None,
                reason=reason,
                emotional_intent=moment.sentiment.value if hasattr(moment.sentiment, "value") else str(moment.sentiment),
                scores=BrollCandidateScore(
                    semantic_match=0.85,
                    sentiment_match=0.8,
                    narrative_match=0.85,
                    visual_quality=0.8,
                    final_score=0.85,
                    confidence=0.85,
                    decision="ACCEPT",
                ),
            )

        scored_candidates: List[Tuple[Dict[str, Any], BrollCandidateScore]] = []
        for asset in available_assets:
            score = self.score_candidate_asset(
                moment=moment,
                asset=asset,
                target_duration=actual_duration,
                narrative_role=narrative_role,
                variety_engine=variety_engine,
            )
            scored_candidates.append((asset, score))

        scored_candidates.sort(key=lambda x: x[1].final_score, reverse=True)
        if not scored_candidates or not self._candidate_passes_gate(scored_candidates[0][1]):
            best_score = scored_candidates[0][1].final_score if scored_candidates else 0.0
            logger.info(
                f"Moment [{moment.moment_id}]: best B-roll {best_score:.2f} failed relevance gate; retaining A-roll."
            )
            return None

        best_asset, best_score = scored_candidates[0]
        shot_type = self._infer_shot_type(best_asset)
        subject_category = best_asset.get("category", "general")

        variety_engine.record_placed_shot(
            shot_id=f"shot_{moment.moment_id}",
            shot_type=shot_type,
            subject_category=subject_category,
            camera_movement=best_asset.get("camera_movement", "static"),
            location=best_asset.get("location", "indoor"),
            semantic_theme=moment.semantic_topic,
        )

        decision = ContextualBrollDecision(
            shot_id=f"broll_{moment.moment_id}",
            moment_id=moment.moment_id,
            start_time=shot_start,
            end_time=shot_end,
            duration=actual_duration,
            narrative_role=narrative_role,
            reason=reason,
            search_query=search_query,
            emotional_intent=f"Aligns with {moment.sentiment.value} emotional tone ({moment.emotional_intensity:.1f})",
            pacing_category=moment.pacing_requirement,
            scores=best_score,
            asset_path=best_asset.get("file_path") or best_asset.get("asset_path"),
            asset_name=Path(best_asset.get("file_path") or best_asset.get("asset_path") or "cutaway.mp4").name,
            shot_type=shot_type,
            subject_category=subject_category,
            status="matched",
        )

        logger.info(
            f"Accepted B-roll [{decision.shot_id}] ({decision.duration:.2f}s): '{best_asset.get('title', 'asset')}' "
            f"score={best_score.final_score:.2f}, semantic={best_score.semantic_match:.2f}, role={narrative_role.value}"
        )
        return decision

    def _candidate_passes_gate(self, score: BrollCandidateScore) -> bool:
        """Apply hard editorial gates before a candidate can enter the timeline."""
        return bool(
            score.decision == "ACCEPT"
            and score.final_score >= self.acceptance_threshold
            and score.semantic_match >= self.MIN_SEMANTIC_SCORE
            and score.narrative_match >= self.MIN_NARRATIVE_SCORE
        )

    def score_candidate_asset(
        self,
        moment: EditorialMoment,
        asset: Dict[str, Any],
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        variety_engine: VisualVarietyEngine,
    ) -> BrollCandidateScore:
        """Calculate contextual score; literal semantic fit dominates generic emotional resonance."""
        title = (asset.get("title") or asset.get("name") or "").lower()
        tags_raw = asset.get("tags") or []
        tags_str = " ".join(tags_raw) if isinstance(tags_raw, list) else str(tags_raw)
        prompt = (asset.get("prompt") or tags_str).lower()
        description = str(asset.get("description") or "").lower()
        asset_text = f"{title} {prompt} {description}"
        moment_text = moment.text.lower()

        from ai_broll_autopilot.services.retrieval_engine import retrieval_engine
        detected_domain, active_rules = retrieval_engine._disambiguate_context(moment)
        retrieval_eval = retrieval_engine._evaluate_single_candidate(
            moment=moment,
            asset=asset,
            target_duration=target_duration,
            narrative_role=narrative_role,
            variety_engine=variety_engine,
            detected_domain=detected_domain,
            active_rules=active_rules,
        )
        if retrieval_eval.is_vetoed:
            return retrieval_eval.to_score_breakdown()

        semantic_score = 0.25
        for ent in moment.entities:
            if ent.lower() in asset_text:
                semantic_score += 0.35
                break
        topic_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", moment.semantic_topic.lower()) if w not in {"with", "from", "that", "this"}]
        topic_hits = sum(1 for tw in topic_words if tw in asset_text)
        if topic_hits:
            semantic_score += min(0.30, topic_hits * 0.15)
        moment_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", moment_text))
        asset_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", asset_text))
        overlap = len(moment_words.intersection(asset_words))
        semantic_score += min(0.20, overlap * 0.05)
        semantic_score = min(1.0, max(0.05, semantic_score))

        sentiment_score = 0.55
        mapping = self.SENTIMENT_FOOTAGE_MAPPINGS.get(moment.sentiment, {})
        if any(b in asset_text for b in mapping.get("boost", [])):
            sentiment_score += 0.30
        if any(p in asset_text for p in mapping.get("penalize", [])):
            sentiment_score -= 0.55
        sentiment_score = min(1.0, max(0.05, sentiment_score))

        action_score = 0.50
        if moment.action != "explaining concept":
            action_terms = [t.strip() for t in moment.action.lower().split(" / ") if t.strip()]
            action_score = 0.95 if any(term in asset_text for term in action_terms) else 0.35

        narrative_score = 0.60
        if narrative_role in {BrollNarrativeRole.ILLUSTRATE, BrollNarrativeRole.EXPLAIN, BrollNarrativeRole.REINFORCE} and semantic_score >= 0.70:
            narrative_score = 0.90
        elif narrative_role == BrollNarrativeRole.CONTRAST and sentiment_score >= 0.80:
            narrative_score = 0.88
        elif semantic_score >= 0.80:
            narrative_score = 0.78

        quality_score = float(asset.get("score", 8)) / 10.0
        if asset.get("watermarked", False):
            quality_score = 0.1

        # Reject/penalize metadata that explicitly says the visual is text-heavy unless text is the subject.
        text_heavy_flag = bool(
            asset.get("text_heavy") or asset.get("has_overlay_text") or asset.get("contains_text_overlay")
        )
        generic_hits = sum(1 for term in self.GENERIC_VISUAL_TERMS if term in asset_text)
        text_hits = sum(1 for term in self.TEXT_HEAVY_TERMS if term in asset_text)
        if text_heavy_flag:
            text_hits += 1
        if text_hits and semantic_score < 0.78:
            quality_score *= 0.55
        if generic_hits and semantic_score < 0.72:
            quality_score *= 0.60

        freshness_score = 1.0
        used_count = int(asset.get("use_count", asset.get("usage_count", 0)) or 0)
        if used_count > 0:
            freshness_score = max(0.2, 1.0 - (used_count * 0.3))

        asset_dur = float(asset.get("duration", target_duration) or target_duration)
        duration_fit = 1.0 if asset_dur >= target_duration else max(0.4, asset_dur / max(0.5, target_duration))

        shot_type = self._infer_shot_type(asset)
        subject = asset.get("category", "general")
        variety_factor = variety_engine.evaluate_variety(
            candidate_shot_type=shot_type,
            subject_category=subject,
        )

        weighted_base = (
            semantic_score * 0.40
            + action_score * 0.20
            + narrative_score * 0.15
            + sentiment_score * 0.10
            + quality_score * 0.05
            + freshness_score * 0.05
            + duration_fit * 0.05
        )
        final_score = round(weighted_base * variety_factor, 2)
        confidence = round(weighted_base, 2)

        decision = "ACCEPT" if final_score >= self.acceptance_threshold else "RETAIN_A_ROLL"
        rejection_reason = None
        if semantic_score < self.MIN_SEMANTIC_SCORE:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Visual is not specific enough to the spoken proposition"
        elif narrative_score < self.MIN_NARRATIVE_SCORE:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Visual does not clearly explain or reinforce the narrative beat"
        elif text_hits and semantic_score < 0.78:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Text-heavy/generic visual is not sufficiently tied to the spoken idea"
        elif generic_hits and semantic_score < 0.72:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Generic stock visual is too weakly related to the spoken idea"
        elif variety_factor < 0.6:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Repetitive visual choice"
        elif decision != "ACCEPT":
            rejection_reason = "Low composite confidence"

        return BrollCandidateScore(
            semantic_match=semantic_score,
            sentiment_match=sentiment_score,
            action_match=action_score,
            narrative_match=narrative_score,
            visual_quality=quality_score,
            freshness=freshness_score,
            duration_fit=duration_fit,
            variety_penalty=round(1.0 - variety_factor, 2),
            final_score=final_score,
            confidence=confidence,
            decision=decision,
            rejection_reason=rejection_reason,
        )

    def _assign_narrative_role(self, moment: EditorialMoment) -> BrollNarrativeRole:
        if moment.narrative_role == NarrativeRole.CONTRAST:
            return BrollNarrativeRole.CONTRAST
        if moment.narrative_role in [NarrativeRole.EXPLANATION, NarrativeRole.EXAMPLE]:
            return BrollNarrativeRole.EXPLAIN
        if moment.narrative_role in [NarrativeRole.CLAIM, NarrativeRole.STATISTIC]:
            return BrollNarrativeRole.REINFORCE
        if moment.narrative_role == NarrativeRole.REVEAL:
            return BrollNarrativeRole.REVEAL
        if moment.speaker_emphasis >= 0.75:
            return BrollNarrativeRole.EMPHASIZE
        return BrollNarrativeRole.ILLUSTRATE

    def _generate_role_reason(self, moment: EditorialMoment, role: BrollNarrativeRole) -> str:
        if role == BrollNarrativeRole.ILLUSTRATE:
            return f"Visually illustrates spoken concept '{moment.semantic_topic}' to clarify meaning."
        if role == BrollNarrativeRole.REINFORCE:
            return "Reinforces the key claim with evidence-based visual imagery."
        if role == BrollNarrativeRole.CONTRAST:
            return "Creates visual juxtaposition highlighting the spoken contradiction."
        if role == BrollNarrativeRole.EXPLAIN:
            return "Provides explanatory context while the speaker describes complex details."
        if role == BrollNarrativeRole.EMPHASIZE:
            return "Emphasizes the climax of spoken delivery."
        if role == BrollNarrativeRole.REVEAL:
            return "Synchronizes the visual reveal with the spoken turning point."
        return "Resets visual fatigue to sustain viewer engagement."

    def _calculate_adaptive_duration(self, moment: EditorialMoment) -> float:
        """Choose an editorial hold, never a duration based on source asset length."""
        pacing = moment.pacing_requirement
        min_dur = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
        max_dur = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8))
        hero_max = float(getattr(Config, "BROLL_HERO_MAX_DURATION", 2.4))

        if pacing == PacingCategory.HIGH_ENERGY:
            base_dur = 0.75 if moment.information_density < 0.70 else 1.0
        elif pacing == PacingCategory.REFLECTIVE:
            base_dur = 1.55
        elif pacing == PacingCategory.DEEP_EXPLANATION:
            base_dur = 1.65
        else:
            base_dur = 1.35

        if moment.information_density >= 0.85:
            base_dur += 0.20
        elif moment.information_density <= 0.25 and pacing == PacingCategory.HIGH_ENERGY:
            base_dur -= 0.10

        # A hero/reveal may breathe slightly longer, but never turns into a 4-8s hold.
        if moment.narrative_role == NarrativeRole.REVEAL and moment.speaker_emphasis >= 0.75:
            base_dur = min(hero_max, max(base_dur, 1.55))

        upper = min(max_dur, hero_max)
        return round(max(min_dur, min(upper, base_dur, max(min_dur, moment.duration))), 2)

    def _build_search_query(self, moment: EditorialMoment, role: BrollNarrativeRole) -> str:
        entities = " ".join(moment.entities[:2]) if moment.entities else ""
        if entities and len(entities) > 3:
            return f"{entities} {moment.sentiment.value}".strip()
        if moment.action != "explaining concept":
            return f"{moment.action} {moment.sentiment.value}".strip()
        return f"{moment.semantic_topic} {moment.sentiment.value}".strip()

    def _infer_shot_type(self, asset: Dict[str, Any]) -> ShotType:
        text = f"{asset.get('title', '')} {asset.get('prompt', '')}".lower()
        if any(w in text for w in ["close up", "macro", "hands", "fingers", "detail"]):
            return ShotType.DETAIL
        if any(w in text for w in ["wide", "aerial", "skyline", "drone", "landscape"]):
            return ShotType.WIDE
        if any(w in text for w in ["screen", "interface", "monitor", "dashboard", "chart"]):
            return ShotType.SCREEN
        return ShotType.MEDIUM

```

============================================================
FILE: ai_broll_autopilot/services/retrieval_engine.py
============================================================

```python
"""Hierarchical Semantic B-Roll Retrieval & Contradiction Filtering Engine.

Provides deep contextual matching, homonym/metaphor disambiguation, and strict veto rules
inspired by video-db/Director and Andrea13235/Retention:
- Disambiguates metaphors (e.g. 'running a startup' vs physical sprinting; 'pitching VCs' vs baseball).
- Multi-metric candidate evaluation (semantic, topic, entity, action, emotional, temporal, visual quality).
- Strict Semantic Contradiction Filter: detects topic domain mismatches (e.g. basketball footage in tech SaaS videos).
- Strict Veto Rules: immediately disqualifies contradictory candidates (veto_score >= 0.65).
- Clean Fallback to A-Roll: when confidence < 0.65, intentionally preserves speaker A-roll.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialMoment,
    PacingCategory,
    SentimentCategory,
    ShotType,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine

logger = logging.getLogger("autopilot.retrieval")


class SemanticDomain(str, Enum):
    """Broad conceptual domain classifications for disambiguation."""
    TECH_SOFTWARE = "tech_software"
    BUSINESS_FINANCE = "business_finance"
    SPORTS_ATHLETICS = "sports_athletics"
    HEALTH_MEDICAL = "health_medical"
    LEGAL_GOVERNMENT = "legal_government"
    ENTERTAINMENT_ARTS = "entertainment_arts"
    EDUCATION_SCIENCE = "education_science"
    LIFESTYLE_TRAVEL = "lifestyle_travel"
    GENERAL = "general"


@dataclass
class DisambiguationRule:
    """Homonym or metaphorical phrase disambiguation definition."""
    term: str
    context_keywords: List[str]
    inferred_domain: SemanticDomain
    veto_domains: List[SemanticDomain]
    veto_keywords: List[str]
    rationale: str


@dataclass
class CandidateEvaluationResult:
    """Detailed multi-metric evaluation breakdown for a candidate B-roll asset."""
    asset_id: str
    asset_name: str
    asset_path: str
    semantic_match: float
    topic_coherence: float
    action_match: float
    visual_quality: float
    sentiment_resonance: float
    duration_fit: float
    freshness: float
    variety_penalty: float
    contradiction_score: float
    final_score: float
    confidence: float
    is_vetoed: bool = False
    veto_reason: Optional[str] = None

    def to_score_breakdown(self) -> BrollCandidateScore:
        decision = "ACCEPT" if (not self.is_vetoed and self.final_score >= 0.65) else (
            "REJECT" if self.is_vetoed else "RETAIN_A_ROLL"
        )
        return BrollCandidateScore(
            semantic_match=round(self.semantic_match, 3),
            sentiment_match=round(self.sentiment_resonance, 3),
            action_match=round(self.action_match, 3),
            narrative_match=round(self.topic_coherence, 3),
            visual_quality=round(self.visual_quality, 3),
            freshness=round(self.freshness, 3),
            duration_fit=round(self.duration_fit, 3),
            variety_penalty=round(self.variety_penalty, 3),
            final_score=round(self.final_score, 3),
            confidence=round(self.confidence, 3),
            decision=decision,
            rejection_reason=self.veto_reason,
        )


class SemanticRetrievalEngine:
    """Hierarchical semantic retrieval engine with disambiguation and strict veto gating."""

    # Disambiguation definitions for common metaphorical traps
    DISAMBIGUATION_RULES = [
        DisambiguationRule(
            term="running",
            context_keywords=["company", "startup", "business", "software", "code", "app", "tests", "pipeline", "servers", "operations", "cro", "ceo"],
            inferred_domain=SemanticDomain.TECH_SOFTWARE,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["sprint", "marathon", "track", "sneakers", "jogging", "athletics", "basketball", "gym", "treadmill"],
            rationale="Dialogue refers to running an enterprise/software, not physical athletics.",
        ),
        DisambiguationRule(
            term="pitch",
            context_keywords=["investor", "vc", "seed", "fundraise", "deck", "valuation", "venture", "angel", "startup"],
            inferred_domain=SemanticDomain.BUSINESS_FINANCE,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["baseball", "mound", "catcher", "batter", "strike", "cricket", "pitcher"],
            rationale="Dialogue refers to a venture capital pitch, not baseball/cricket.",
        ),
        DisambiguationRule(
            term="court",
            context_keywords=["lawyer", "judge", "trial", "legal", "lawsuit", "verdict", "supreme court", "attorney", "litigation"],
            inferred_domain=SemanticDomain.LEGAL_GOVERNMENT,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["basketball", "dunk", "hoop", "tennis", "nba", "referee", "foul", "court side"],
            rationale="Dialogue refers to a court of law, not a basketball/tennis court.",
        ),
        DisambiguationRule(
            term="apple",
            context_keywords=["iphone", "mac", "tim cook", "steve jobs", "ios", "silicon", "cupertino", "tech", "app store"],
            inferred_domain=SemanticDomain.TECH_SOFTWARE,
            veto_domains=[SemanticDomain.LIFESTYLE_TRAVEL],
            veto_keywords=["orchard", "fruit", "grocery", "pie", "cider", "harvest", "tree"],
            rationale="Dialogue refers to Apple Inc. technology, not fruit farming.",
        ),
        DisambiguationRule(
            term="dunk",
            context_keywords=["basketball", "nba", "points", "hoop", "slam", "rebound", "collin sexton", "trae", "lebron", "score"],
            inferred_domain=SemanticDomain.SPORTS_ATHLETICS,
            veto_domains=[SemanticDomain.BUSINESS_FINANCE, SemanticDomain.TECH_SOFTWARE],
            veto_keywords=["donuts", "coffee", "cookies", "biscuit", "dunking tea"],
            rationale="Dialogue refers to a basketball slam dunk.",
        ),
    ]

    # Domain keyword signatures
    DOMAIN_SIGNATURES = {
        SemanticDomain.TECH_SOFTWARE: {
            "keywords": ["ai", "software", "code", "cloud", "saas", "api", "database", "developer", "machine learning", "neural", "platform", "algorithm", "backend", "frontend", "server", "model", "python", "javascript"],
            "forbidden_visuals": ["basketball", "football", "boxing", "dunk", "slam dunk", "touchdown", "tennis", "soccer", "marathon"],
        },
        SemanticDomain.BUSINESS_FINANCE: {
            "keywords": ["revenue", "cro", "sales", "arr", "ebitda", "profit", "margins", "fundraising", "valuation", "investors", "growth", "equity", "enterprise", "market", "customer", "b2b"],
            "forbidden_visuals": ["slam dunk", "boxing ring", "football field", "court dunk", "hockey rink"],
        },
        SemanticDomain.SPORTS_ATHLETICS: {
            "keywords": ["dunk", "points", "game", "championship", "hoop", "rebound", "nba", "defense", "offense", "quarter", "coach", "playoff", "athlete", "score"],
            "forbidden_visuals": ["software dashboard", "code editor", "server rack", "excel spreadsheet", "powerpoint"],
        },
    }

    def __init__(self, acceptance_threshold: float = 0.65, contradiction_veto_threshold: float = 0.60):
        self.acceptance_threshold = acceptance_threshold
        self.contradiction_veto_threshold = contradiction_veto_threshold

    def retrieve_and_rank_candidates(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        target_duration: float,
        narrative_role: BrollNarrativeRole,
    ) -> List[CandidateEvaluationResult]:
        """Rank and evaluate all candidate B-roll assets with strict contradiction veto rules."""
        results: List[CandidateEvaluationResult] = []

        # 1. Infer primary domain & active disambiguation rules for this moment
        detected_domain, active_rules = self._disambiguate_context(moment)

        for asset in available_assets:
            evaluation = self._evaluate_single_candidate(
                moment=moment,
                asset=asset,
                target_duration=target_duration,
                narrative_role=narrative_role,
                variety_engine=variety_engine,
                detected_domain=detected_domain,
                active_rules=active_rules,
            )
            results.append(evaluation)

        # Sort: un-vetoed first, then descending final_score
        results.sort(key=lambda x: (not x.is_vetoed, x.final_score), reverse=True)
        return results

    def select_best_decision(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        shot_start: float,
        shot_end: float,
    ) -> Optional[ContextualBrollDecision]:
        """Select the best B-roll candidate, or return None to intentionally retain A-roll."""
        ranked = self.retrieve_and_rank_candidates(
            moment=moment,
            available_assets=available_assets,
            variety_engine=variety_engine,
            target_duration=target_duration,
            narrative_role=narrative_role,
        )

        if not ranked:
            return None

        best = ranked[0]

        # Check veto or below acceptance threshold
        if best.is_vetoed:
            logger.info(
                f"Moment [{moment.moment_id}]: Top candidate '{best.asset_name}' VETOED: {best.veto_reason}. "
                f"Intentionally retaining A-roll."
            )
            return None

        if best.final_score < self.acceptance_threshold:
            logger.info(
                f"Moment [{moment.moment_id}]: Best candidate '{best.asset_name}' score ({best.final_score:.2f}) "
                f"< threshold ({self.acceptance_threshold}). Retaining A-roll over weak visual."
            )
            return None

        # Best candidate passed all gates
        shot_type = ShotType.MEDIUM
        raw_type = best.asset_path.lower()
        if "close" in raw_type or "cu" in raw_type:
            shot_type = ShotType.CLOSE_UP
        elif "wide" in raw_type:
            shot_type = ShotType.WIDE
        elif "screen" in raw_type or "ui" in raw_type:
            shot_type = ShotType.SCREEN

        variety_engine.record_placed_shot(
            shot_id=f"shot_{moment.moment_id}",
            shot_type=shot_type,
            subject_category=moment.semantic_topic or "general",
            camera_movement="dynamic",
            location="indoor",
            semantic_theme=moment.semantic_topic,
        )

        return ContextualBrollDecision(
            shot_id=f"broll_{moment.moment_id}",
            moment_id=moment.moment_id,
            start_time=shot_start,
            end_time=shot_end,
            duration=round(shot_end - shot_start, 2),
            narrative_role=narrative_role,
            reason=f"Contextual match for '{moment.text[:40]}' ({best.asset_name})",
            search_query=best.asset_name,
            emotional_intent=moment.sentiment.value,
            pacing_category=moment.pacing_requirement,
            scores=best.to_score_breakdown(),
            asset_path=best.asset_path,
            asset_name=best.asset_name,
            shot_type=shot_type,
            subject_category=moment.semantic_topic or "general",
            status="matched",
        )

    def _disambiguate_context(self, moment: EditorialMoment) -> Tuple[SemanticDomain, List[DisambiguationRule]]:
        """Identify if any homonyms or metaphorical phrases exist in the moment text."""
        text_lower = moment.text.lower()
        active_rules = []

        for rule in self.DISAMBIGUATION_RULES:
            if rule.term in text_lower:
                # Check if any context keywords confirm the rule
                hits = sum(1 for kw in rule.context_keywords if kw in text_lower)
                if hits > 0:
                    active_rules.append(rule)

        # Inferred domain based on signatures
        domain_scores = {d: 0 for d in SemanticDomain}
        for d, sig in self.DOMAIN_SIGNATURES.items():
            for kw in sig["keywords"]:
                if kw in text_lower:
                    domain_scores[d] += 1

        best_domain = max(domain_scores.items(), key=lambda x: x[1])
        inferred = best_domain[0] if best_domain[1] > 0 else SemanticDomain.GENERAL

        return inferred, active_rules

    def _evaluate_single_candidate(
        self,
        moment: EditorialMoment,
        asset: Dict[str, Any],
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        variety_engine: VisualVarietyEngine,
        detected_domain: SemanticDomain,
        active_rules: List[DisambiguationRule],
    ) -> CandidateEvaluationResult:
        """Score a single candidate asset against contextual criteria and contradiction rules."""
        asset_id = str(asset.get("id", asset.get("asset_id", "asset_unknown")))
        asset_name = asset.get("title", asset.get("name", "Unknown Visual"))
        asset_path = asset.get("file_path", asset.get("path", ""))
        tags = [t.lower() for t in asset.get("tags", [])]
        category = asset.get("category", "").lower()
        description = asset.get("description", "").lower()

        combined_asset_text = f"{asset_name.lower()} {category} {' '.join(tags)} {description}"
        moment_text_lower = moment.text.lower()

        # -------------------------------------------------------------
        # STEP 1: CONTRADICTION & VETO AUDIT
        # -------------------------------------------------------------
        contradiction_score = 0.0
        is_vetoed = False
        veto_reason = None

        # Check Active Disambiguation Rules
        for rule in active_rules:
            # Check if candidate contains veto keywords for this disambiguated term
            for veto_kw in rule.veto_keywords:
                if veto_kw in combined_asset_text:
                    is_vetoed = True
                    contradiction_score = 1.0
                    veto_reason = f"Metaphor contradiction: '{rule.term}' refers to {rule.inferred_domain.value}. Vetoed due to athlete/sports visual '{veto_kw}'."
                    break
            if is_vetoed:
                break

        # Check Inferred Domain Signature Forbidden Visuals
        if not is_vetoed and detected_domain in self.DOMAIN_SIGNATURES:
            forbidden = self.DOMAIN_SIGNATURES[detected_domain]["forbidden_visuals"]
            for f_kw in forbidden:
                if f_kw in combined_asset_text:
                    is_vetoed = True
                    contradiction_score = 0.95
                    veto_reason = f"Domain contradiction: Content is {detected_domain.value}. Disallowed visual '{f_kw}' detected."
                    break

        # Negative keyword audit (e.g. somber reflective dialogue vs beach party)
        if not is_vetoed:
            if moment.sentiment == SentimentCategory.NEGATIVE:
                party_cues = ["beach", "party", "cheering", "fireworks", "celebration"]
                if any(p in combined_asset_text for p in party_cues):
                    contradiction_score = 0.80
                    is_vetoed = True
                    veto_reason = "Emotional contradiction: Somber/serious dialogue paired with celebratory visual."

        # -------------------------------------------------------------
        # STEP 2: MULTI-METRIC CONTEXTUAL SCORING
        # -------------------------------------------------------------
        # 1. Semantic Match (word overlap & keyword presence)
        moment_tokens = set(re.findall(r"\w+", moment_text_lower))
        asset_tokens = set(re.findall(r"\w+", combined_asset_text))
        overlap = len(moment_tokens.intersection(asset_tokens))
        semantic_match = min(1.0, overlap / max(1, len(moment_tokens) * 0.35))

        # 2. Topic Coherence
        topic_coherence = 0.5
        if moment.semantic_topic and moment.semantic_topic.lower() in combined_asset_text:
            topic_coherence = 0.95
        elif category in moment_text_lower:
            topic_coherence = 0.85

        # 3. Action Match
        action_match = 0.5
        if moment.action and moment.action.lower() in combined_asset_text:
            action_match = 0.90

        # 4. Sentiment Resonance
        sentiment_resonance = 0.6
        if moment.sentiment == SentimentCategory.TECHNICAL:
            tech_indicators = ["code", "software", "screen", "server", "data", "chart"]
            if any(t in combined_asset_text for t in tech_indicators):
                sentiment_resonance = 0.95
        elif moment.sentiment == SentimentCategory.POSITIVE:
            pos_indicators = ["success", "growth", "handshake", "smile", "skyline", "trophy"]
            if any(p in combined_asset_text for p in pos_indicators):
                sentiment_resonance = 0.90

        # 5. Visual Quality & Resolution
        visual_quality = 0.85
        width = asset.get("width", 1920)
        height = asset.get("height", 1080)
        if width < 1280 or height < 720:
            visual_quality = 0.40

        # 6. Duration Fit
        asset_duration = float(asset.get("duration", 10.0))
        if asset_duration < target_duration:
            duration_fit = max(0.2, asset_duration / max(1.0, target_duration))
        else:
            duration_fit = 1.0

        # 7. Freshness (usage penalty)
        usage_count = int(asset.get("usage_count", 0))
        freshness = max(0.2, 1.0 - (usage_count * 0.25))

        # 8. Visual Variety Penalty
        shot_type = ShotType.MEDIUM
        variety_penalty = variety_engine.calculate_variety_penalty(
            candidate_shot_type=shot_type,
            candidate_subject=category,
            candidate_motion=asset.get("camera_movement", "dynamic"),
        )

        # -------------------------------------------------------------
        # STEP 3: COMPUTE FINAL WEIGHTED SCORE
        # -------------------------------------------------------------
        if is_vetoed:
            final_score = 0.0
            confidence = 0.0
        else:
            weighted = (
                0.30 * semantic_match
                + 0.15 * topic_coherence
                + 0.15 * action_match
                + 0.15 * visual_quality
                + 0.10 * sentiment_resonance
                + 0.08 * duration_fit
                + 0.07 * freshness
                - (0.35 * variety_penalty)
                - (0.50 * contradiction_score)
            )
            final_score = max(0.0, min(1.0, weighted))
            confidence = final_score

        return CandidateEvaluationResult(
            asset_id=asset_id,
            asset_name=asset_name,
            asset_path=asset_path,
            semantic_match=semantic_match,
            topic_coherence=topic_coherence,
            action_match=action_match,
            visual_quality=visual_quality,
            sentiment_resonance=sentiment_resonance,
            duration_fit=duration_fit,
            freshness=freshness,
            variety_penalty=variety_penalty,
            contradiction_score=contradiction_score,
            final_score=final_score,
            confidence=confidence,
            is_vetoed=is_vetoed,
            veto_reason=veto_reason,
        )


# Singleton instance
retrieval_engine = SemanticRetrievalEngine()

```

============================================================
FILE: ai_broll_autopilot/services/editorial/pacing_model.py
============================================================

```python
"""Editorial Retention and Pacing Model.

Constructs macro-level energy curves, balances narrative rhythm, and prevents
simultaneous visual events from creating clutter or accidentally lengthening
approved B-roll durations.
"""

import logging
from typing import Any, Dict, List, Tuple

from ai_broll_autopilot.services.editorial.types import (
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    EditorialMoment,
    SfxCueDecision,
)

logger = logging.getLogger("autopilot.editorial.pacing")


class PacingModel:
    """Calculates macro-rhythm energy curves and audits cognitive processing load."""

    def build_energy_curve(self, moments: List[EditorialMoment]) -> List[Dict[str, float]]:
        """Construct the macro energy retention curve across the timeline."""
        curve: List[Dict[str, float]] = []
        for m in moments:
            curve.append({
                "time": round(m.start_time, 2),
                "energy": round(m.energy_level, 2),
                "density": round(m.information_density, 2),
                "role": m.narrative_role.value,
            })
            mid_t = round((m.start_time + m.end_time) / 2.0, 2)
            curve.append({
                "time": mid_t,
                "energy": round(m.energy_level, 2),
                "density": round(m.information_density, 2),
                "role": m.narrative_role.value,
            })
        return curve

    def audit_and_balance_load(
        self,
        moments: List[EditorialMoment],
        broll_shots: List[ContextualBrollDecision],
        captions: List[EditorialCaptionSpec],
        camera_moves: List[EditorialCameraSpec],
        sfx_cues: List[SfxCueDecision],
    ) -> Tuple[List[ContextualBrollDecision], List[EditorialCameraSpec], List[SfxCueDecision]]:
        """Balance events without ever extending an approved B-roll interval."""
        pruned_camera: List[EditorialCameraSpec] = []
        pruned_sfx: List[SfxCueDecision] = list(sfx_cues)
        balanced_broll: List[ContextualBrollDecision] = list(broll_shots)
        min_broll_duration = 0.45

        # A punch-in is for the speaker; don't stack it on stock footage.
        for cam in camera_moves:
            collides_with_broll = any(
                b.start_time <= cam.timestamp < b.end_time for b in balanced_broll
            )
            if collides_with_broll:
                logger.debug(f"Descheduled camera punch-in at {cam.timestamp:.2f}s: overlaps with B-roll.")
            else:
                pruned_camera.append(cam)

        # Sort by timeline position so overlap resolution is deterministic.
        balanced_broll.sort(key=lambda b: (float(b.start_time), float(b.end_time)))

        # Never pad B-roll to create an artificial gap. If two shots collide or
        # nearly collide, trim the earlier shot only when doing so leaves a valid
        # editorial interval. Otherwise drop the weaker/later shot.
        repaired: List[ContextualBrollDecision] = []
        for current in balanced_broll:
            current.start_time = round(max(0.0, float(current.start_time)), 2)
            current.end_time = round(max(current.start_time, float(current.end_time)), 2)
            current.duration = round(current.end_time - current.start_time, 2)

            if not repaired:
                if current.duration >= min_broll_duration:
                    repaired.append(current)
                continue

            previous = repaired[-1]
            overlap = previous.end_time - current.start_time

            if overlap > 0:
                proposed_end = round(current.start_time, 2)
                if proposed_end - previous.start_time >= min_broll_duration:
                    previous.end_time = proposed_end
                    previous.duration = round(previous.end_time - previous.start_time, 2)
                else:
                    # Preserve the already accepted earlier shot and reject the
                    # overlapping later one instead of extending either clip.
                    logger.debug(
                        f"Dropped overlapping B-roll [{current.shot_id}] to preserve [{previous.shot_id}]."
                    )
                    continue

            # Very small gaps are intentional A-roll breathing room; never use
            # the gap as a reason to extend the preceding B-roll.
            if current.duration >= min_broll_duration:
                repaired.append(current)

        balanced_broll = repaired

        # Stagger captions slightly after a B-roll entrance so the visual can register first.
        for b in balanced_broll:
            for cap in captions:
                if abs(b.start_time - cap.start_time) < 0.15 and b.start_time > 2.0:
                    cap.start_time = round(b.start_time + 0.20, 2)

        return balanced_broll, pruned_camera, pruned_sfx

```

============================================================
FILE: ai_broll_autopilot/services/editorial/pipeline.py
============================================================

```python
"""AI Editorial Intelligence Pipeline Coordinator.

Orchestrates the entire editorial decision workflow:
1. Rebuilt Hook Detection & Selection (highest-scoring candidate opens the video)
2. Editorial Moment Map (roles, sentiment, entities, intensity, density)
3. Contextual, Sentiment-Aware B-Roll with Adaptive Pacing & Variety Control
4. Semantically Relatable, Density-Controlled Sound Design & Visual Sync
5. Macro Retention Energy Curve & Cognitive Processing Load Balancing
6. Quality Gate Audit and Automatic Repairs
7. Clean structured specification export for Diffusion Studio composition execution.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.services.editorial.broll_intelligence import BrollIntelligence
from ai_broll_autopilot.services.editorial.hook_engine import HookEngine
from ai_broll_autopilot.services.editorial.moment_analyzer import MomentAnalyzer
from ai_broll_autopilot.services.editorial.pacing_model import PacingModel
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.sound_designer import SoundDesigner
from ai_broll_autopilot.services.editorial.types import (
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    EditorialEditSpecification,
    HookCandidate,
    NarrativeRole,
    QualityAuditReport,
    EditIntent,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine
from ai_broll_autopilot.services.editorial.creative_director import creative_director

logger = logging.getLogger("autopilot.editorial.pipeline")


class EditorialIntelligencePipeline:
    """Master Editorial Intelligence Pipeline producing human-editor quality edit specifications."""

    def __init__(self):
        self.hook_engine = HookEngine()
        self.moment_analyzer = MomentAnalyzer()
        self.broll_intelligence = BrollIntelligence()
        self.variety_engine = VisualVarietyEngine()
        self.sound_designer = SoundDesigner()
        self.pacing_model = PacingModel()
        self.quality_gate = EditorialQualityGate()

    def process(
        self,
        source_media: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        video_duration: float,
        available_broll_assets: Optional[List[Dict[str, Any]]] = None,
        custom_hook: Optional[str] = None,
        clip_interval: Optional[Tuple[float, float]] = None,
        niche_profile: Optional[Any] = None,
        style_profile: Optional[Any] = None,
    ) -> Tuple[EditorialEditSpecification, QualityAuditReport]:
        """Execute the end-to-end editorial intelligence pipeline."""
        spec_id = f"edit_spec_{uuid.uuid4().hex[:8]}"
        self.variety_engine.reset()
        assets = available_broll_assets or []

        # -------------------------------------------------------------
        # STEP 1: HOOK DETECTION & SELECTION
        # -------------------------------------------------------------
        hook_candidates = self.hook_engine.generate_candidates(
            transcript_segments=transcript_segments,
            video_duration=video_duration,
            target_clip_interval=clip_interval,
        )

        selected_hook: Optional[HookCandidate] = None
        if hook_candidates:
            selected_hook = hook_candidates[0]  # Top scoring candidate
            logger.info(
                f"Selected primary opening hook [{selected_hook.candidate_id}] (Score: {selected_hook.scores.final_score:.1f}): "
                f"'{selected_hook.tightened_text}'"
            )
        else:
            # Fallback natural opener
            first_text = transcript_segments[0].get("text", "") if transcript_segments else "Key Takeaway"
            selected_hook = self.hook_engine.evaluate_candidate(
                candidate_id="hook_default",
                raw_text=first_text,
                start_time=0.0,
                end_time=min(4.0, video_duration),
                duration=min(4.0, video_duration),
                full_transcript=first_text,
            )

        # -------------------------------------------------------------
        # STEP 2: EDITORIAL MOMENT MAP
        # -------------------------------------------------------------
        # Filter segments for this short's time window if clip_interval is provided
        clip_in = clip_interval[0] if clip_interval else 0.0
        clip_out = clip_interval[1] if clip_interval else video_duration
        target_duration = max(1.0, clip_out - clip_in)

        scoped_segments = []
        for s in transcript_segments:
            st = s.get("start", 0.0)
            et = s.get("end", 0.0)
            if et > clip_in and st < clip_out:
                scoped_segments.append({
                    "start": max(0.0, round(st - clip_in, 2)),
                    "end": min(target_duration, round(et - clip_in, 2)),
                    "text": s.get("text", ""),
                    "words": s.get("words", []),
                })

        moments = self.moment_analyzer.analyze_transcript(
            transcript_segments=scoped_segments,
            video_duration=target_duration,
        )

        # -------------------------------------------------------------
        # STEP 3: CENTRAL CREATIVE DIRECTOR / EDIT INTENT
        # -------------------------------------------------------------
        # Every downstream system receives the same attention allocation.
        # This prevents captions, B-roll, memes, SFX, and camera motion from
        # independently deciding that the same sentence deserves maximum impact.
        hook_moment_id = ""
        if selected_hook:
            hook_start = float(selected_hook.start_time)
            hook_moment = min(
                moments,
                key=lambda m: abs(float(m.start_time) - hook_start),
                default=None,
            )
            hook_moment_id = hook_moment.moment_id if hook_moment else ""

        edit_intents = creative_director.analyze(moments, hook_moment_id=hook_moment_id)
        for moment, intent in zip(moments, edit_intents):
            # The dataclass contract lives in editorial.types; copy the
            # provider-agnostic decision into the moment for serialization.
            moment.edit_intent = intent

        # -------------------------------------------------------------
        # STEP 4: CONTEXTUAL, SENTIMENT-AWARE B-ROLL SELECTION
        # -------------------------------------------------------------
        broll_decisions: List[ContextualBrollDecision] = []

        for idx, moment in enumerate(moments):
            intent = moment.edit_intent
            # Keep high-value visual opportunities while allowing genuinely
            # quiet moments to remain A-roll instead of filling the timeline.
            if intent and intent.broll_pressure < 0.30 and idx != 0:
                continue
            decision = self.broll_intelligence.evaluate_and_plan_shot(
                moment=moment,
                available_assets=assets,
                variety_engine=self.variety_engine,
                is_first_moment=(idx == 0),
            )
            if decision:
                broll_decisions.append(decision)

        # -------------------------------------------------------------
        # STEP 5: KINETIC TEXT OVERLAYS & HOOK CARD
        # -------------------------------------------------------------
        captions: List[EditorialCaptionSpec] = []
        hook_title_text = custom_hook or selected_hook.tightened_text
        if len(hook_title_text.split()) > 7:
            # Condense for title card impact
            hook_title_text = " ".join(hook_title_text.split()[:6]).upper() + "..."
        else:
            hook_title_text = hook_title_text.upper()

        captions.append(
            EditorialCaptionSpec(
                caption_id="cap_hook_title",
                text=hook_title_text,
                start_time=0.5,
                duration=2.2,
                position="center",
                style="bold_impact",
                # Subject-aware placement is resolved later by the render settings /
                # caption compositor; do not override the user's setting here.
                behind_subject=False,
                highlight_color="#FFDD00",
            )
        )

        # Additional callout for major statistics or payoff
        for m in moments[1:]:
            if m.narrative_role == NarrativeRole.STATISTIC and m.entities:
                captions.append(
                    EditorialCaptionSpec(
                        caption_id=f"cap_stat_{m.moment_id}",
                        text=f"{m.entities[0].upper()} IMPACT",
                        start_time=round(m.start_time + 0.2, 2),
                        duration=1.8,
                        position="center",
                        style="stat_callout",
                        behind_subject=False,
                        highlight_color="#00FFAA",
                    )
                )
                break  # Max 1 additional callout to avoid text clutter

        # -------------------------------------------------------------
        # STEP 6: CAMERA PUNCH-IN ZOOMS
        # -------------------------------------------------------------
        camera_moves: List[EditorialCameraSpec] = []
        for m in moments:
            # Camera punches now require Creative Director approval instead of
            # firing on every claim/reveal independently.
            intent = m.edit_intent
            if intent and intent.treatment in {"impact", "absurd"} and m.speaker_emphasis >= 0.62:
                camera_moves.append(
                    EditorialCameraSpec(
                        camera_id=f"cam_punch_{m.moment_id}",
                        timestamp=round(m.start_time, 2),
                        scale=1.22,
                        duration=0.3,
                        reason=f"Punch-in on emphatic delivery in '{m.semantic_topic}'",
                    )
                )

        # -------------------------------------------------------------
        # STEP 7: SOUND DESIGN & SYNCHRONIZATION
        # -------------------------------------------------------------
        sfx_cues = self.sound_designer.design_soundscape(
            moments=moments,
            captions=captions,
            camera_moves=camera_moves,
            broll_shots=broll_decisions,
            video_duration=target_duration,
            edit_intents=edit_intents,
        )

        # -------------------------------------------------------------
        # STEP 8: PACING & COGNITIVE PROCESSING LOAD BALANCING
        # -------------------------------------------------------------
        broll_decisions, camera_moves, sfx_cues = self.pacing_model.audit_and_balance_load(
            moments=moments,
            broll_shots=broll_decisions,
            captions=captions,
            camera_moves=camera_moves,
            sfx_cues=sfx_cues,
        )
        energy_curve = self.pacing_model.build_energy_curve(moments)

        # -------------------------------------------------------------
        # STEP 9: ASSEMBLE MASTER EDIT SPECIFICATION
        # -------------------------------------------------------------
        spec = EditorialEditSpecification(
            spec_id=spec_id,
            title=selected_hook.tightened_text[:50],
            total_duration=target_duration,
            hook=selected_hook,
            moments=moments,
            broll_shots=broll_decisions,
            captions=captions,
            sfx_cues=sfx_cues,
            camera_moves=camera_moves,
            energy_curve=energy_curve,
            edit_intents=edit_intents,
            metadata={
                "generator": "Stockpile Editorial Intelligence Pipeline",
                "version": "2.0.0",
                "source_media": source_media,
                "hook_candidates_count": len(hook_candidates),
                "broll_count": len(broll_decisions),
                "sfx_count": len(sfx_cues),
                "niche": getattr(niche_profile, "name", "generic"),
                "style": getattr(style_profile, "name", "clean_podcast"),
                "creative_director": {
                    "version": "1.0",
                    "intent_count": len(edit_intents),
                    "treatment_counts": {
                        treatment: sum(1 for i in edit_intents if i.treatment == treatment)
                        for treatment in ("quiet", "normal", "kinetic", "impact", "absurd")
                    },
                    "average_chaos": round(sum(i.chaos_score for i in edit_intents) / max(1, len(edit_intents)), 3),
                },
            },
        )

        # -------------------------------------------------------------
        # STEP 10: QUALITY GATE AUDIT & AUTO-REPAIR
        # -------------------------------------------------------------
        repaired_spec, quality_report = self.quality_gate.audit_and_repair(spec)

        logger.info(
            f"Editorial Pipeline generated spec [{spec_id}] "
            f"({len(repaired_spec.broll_shots)} B-roll, {len(repaired_spec.sfx_cues)} SFX, "
            f"{len(repaired_spec.camera_moves)} Zooms). Quality Score: {quality_report.overall_score:.2f}."
        )
        return repaired_spec, quality_report


editorial_pipeline = EditorialIntelligencePipeline()

```

============================================================
FILE: ai_broll_autopilot/services/edit_director.py
============================================================

```python
"""Edit Director Service generating declarative, non-destructive Edit Plans.

Translates speech transcripts, niche content profiles, and visual style preferences
into structured edit plans compatible with OpenReel.
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.niches import niche_registry, NicheProfile
from ai_broll_autopilot.styles import style_registry, StyleProfile
from ai_broll_autopilot.services.clip_detector import ClipCandidate

logger = logging.getLogger(__name__)


def _clean_json_str(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


@dataclass
class EditPlan:
    """Canonical EditPlan Schema v2.1.
    
    Represents an intelligent, non-destructive edit structure linking:
    - Source media metadata
    - Cuts-First A-roll keep intervals and detected dead-air/filler cuts
    - Contextual, sentiment-aware B-roll shots with strict veto validation
    - Word-level kinetic subtitles in safe area
    - Content-aware motion graphics (numbers, stats, key term badges, lower thirds)
    - Keyframe punch-in camera zooms
    - Multi-track sound design (SFX cues + ducked BGM)
    - Visual QA compliance metrics
    """
    plan_id: str
    title: str
    target_duration: float
    source_media: Dict[str, Any]
    clip_interval: Dict[str, float]       # {"in_point": float, "out_point": float}
    niche: Dict[str, Any]
    style: Dict[str, Any]
    version: str = "2.1"
    cuts: List[Dict[str, Any]] = field(default_factory=list)           # Cuts-First cut candidates
    keep_intervals: List[Any] = field(default_factory=list)            # Contiguous kept intervals
    a_roll_ranges: List[Dict[str, Any]] = field(default_factory=list)  # Mapped A-roll chunks
    shots: List[Dict[str, Any]] = field(default_factory=list)          # B-roll cutaways
    text_overlays: List[Dict[str, Any]] = field(default_factory=list)  # Title / graphic callouts
    graphics: List[Dict[str, Any]] = field(default_factory=list)       # Content-aware kinetic graphics
    subtitles: List[Dict[str, Any]] = field(default_factory=list)      # Word-level timed subtitles
    zooms: List[Dict[str, Any]] = field(default_factory=list)          # Keyframe punch-ins
    audio_cues: Dict[str, Any] = field(default_factory=dict)           # BGM and SFX cues
    cadence_profile: Dict[str, Any] = field(default_factory=dict)      # Rhythm configuration
    editorial_spec: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    visual_qa: Optional[Dict[str, Any]] = None
    review_items: List[Dict[str, Any]] = field(default_factory=list)
    razor_captions: List[Dict[str, Any]] = field(default_factory=list) # Rapid Razor Caption events
    subtitles_behind_subject: bool = False
    hook_text: Optional[str] = None
    render_settings: Dict[str, Any] = field(default_factory=dict)
    render_stale: bool = False
    edit_revision: int = 1
    openshorts_jobs: List[Dict[str, Any]] = field(default_factory=list)
    last_render_revision: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "version": self.version,
            "plan_id": self.plan_id,
            "title": self.title,
            "target_duration": round(self.target_duration, 2),
            "source_media": self.source_media,
            "clip_interval": {
                "in_point": round(self.clip_interval["in_point"], 2),
                "out_point": round(self.clip_interval["out_point"], 2),
            },
            "niche": self.niche,
            "style": self.style,
            "cuts": self.cuts,
            "keep_intervals": self.keep_intervals,
            "a_roll_ranges": self.a_roll_ranges,
            "shots": self.shots,
            "text_overlays": self.text_overlays,
            "graphics": self.graphics,
            "subtitles": self.subtitles,
            "zooms": self.zooms,
            "audio_cues": self.audio_cues,
            "cadence_profile": self.cadence_profile,
            "review_items": self.review_items,
            "razor_captions": self.razor_captions,
            "subtitles_behind_subject": self.subtitles_behind_subject,
            "hook_text": self.hook_text,
            "render_settings": self.render_settings,
            "render_stale": self.render_stale,
            "edit_revision": self.edit_revision,
            "openshorts_jobs": self.openshorts_jobs,
            "last_render_revision": self.last_render_revision,
        }
        if self.editorial_spec:
            d["editorial_spec"] = self.editorial_spec
        if self.quality_report:
            d["quality_report"] = self.quality_report
        if self.visual_qa:
            d["visual_qa"] = self.visual_qa
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EditPlan":
        return cls(
            plan_id=d.get("plan_id", f"plan_{uuid.uuid4().hex[:8]}"),
            title=d.get("title", "Untitled Edit Plan"),
            target_duration=float(d.get("target_duration", 0.0)),
            source_media=d.get("source_media", {}),
            clip_interval=d.get("clip_interval", {"in_point": 0.0, "out_point": float(d.get("target_duration", 0.0))}),
            niche=d.get("niche", {}),
            style=d.get("style", {}),
            version=d.get("version", "2.1"),
            cuts=d.get("cuts", []),
            keep_intervals=d.get("keep_intervals", []),
            a_roll_ranges=d.get("a_roll_ranges", []),
            shots=d.get("shots", []),
            text_overlays=d.get("text_overlays", []),
            graphics=d.get("graphics", []),
            subtitles=d.get("subtitles", []),
            zooms=d.get("zooms", []),
            audio_cues=d.get("audio_cues", {}),
            cadence_profile=d.get("cadence_profile", {}),
            editorial_spec=d.get("editorial_spec"),
            quality_report=d.get("quality_report"),
            visual_qa=d.get("visual_qa"),
            review_items=d.get("review_items", []),
            razor_captions=d.get("razor_captions", []),
            subtitles_behind_subject=bool(d.get("subtitles_behind_subject", False)),
            hook_text=d.get("hook_text"),
            render_settings=d.get("render_settings", {}),
            render_stale=bool(d.get("render_stale", False)),
            edit_revision=int(d.get("edit_revision", 1)),
            openshorts_jobs=d.get("openshorts_jobs", []),
            last_render_revision=d.get("last_render_revision"),
        )


class EditDirectorService:
    """Plans intelligent cuts, B-roll cutaways, subtitles, and graphics based on niche & style."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    async def plan_edit(
        self,
        source_media: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        clip_candidate: Optional[ClipCandidate] = None,
        in_point: Optional[float] = None,
        out_point: Optional[float] = None,
        niche_id: Optional[str] = None,
        style_id: Optional[str] = None,
        custom_hook: Optional[str] = None,
    ) -> EditPlan:
        """Create a complete non-destructive Edit Plan.

        Args:
            source_media: Dict with path, duration, width, height, fps.
            transcript_segments: Whisper speech segments.
            clip_candidate: Optional detected ClipCandidate.
            in_point: Optional override in-point in seconds.
            out_point: Optional override out-point in seconds.
            niche_id: Niche ID (or auto-detect).
            style_id: Style ID (or auto-select).
            custom_hook: Optional custom title/hook card text.

        Returns:
            EditPlan instance.
        """
        # 1. Resolve Clip Boundaries
        if clip_candidate:
            clip_in = clip_candidate.start_time
            clip_out = clip_candidate.end_time
            title = clip_candidate.title
        else:
            clip_in = in_point if in_point is not None else 0.0
            clip_out = out_point if out_point is not None else source_media.get("duration", 60.0)
            title = source_media.get("title", Path(source_media.get("path", "video.mp4")).stem)

        clip_duration = max(1.0, clip_out - clip_in)

        # 2. Filter Transcript Segments for this Clip Interval
        clip_segments = []
        for s in transcript_segments:
            seg_start = s.get("start", 0.0)
            seg_end = s.get("end", 0.0)
            if seg_end > clip_in and seg_start < clip_out:
                # Normalize segment relative to clip start (0.0s)
                clip_segments.append({
                    "start": max(0.0, round(seg_start - clip_in, 2)),
                    "end": min(clip_duration, round(seg_end - clip_in, 2)),
                    "text": s.get("text", "").strip(),
                    "words": s.get("words", []),
                })

        # 3. Resolve Niche and Style Profiles
        niche = niche_registry.get_profile(niche_id)
        style = style_registry.get_style(style_id)

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # -------------------------------------------------------------
        # 4. Cuts-First Retention Analysis
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.retention_engine import retention_engine
        is_podcast = (niche_id == "clean_podcast" or "podcast" in style_id.lower())
        detected_cuts = retention_engine.analyze_and_detect_cuts(
            transcript_segments=clip_segments,
            video_duration=clip_duration,
            is_podcast=is_podcast,
        )
        keep_intervals = retention_engine.compute_keep_intervals(
            video_duration=clip_duration,
            cuts=detected_cuts,
        )

        a_roll_ranges = []
        for s_keep, e_keep in keep_intervals:
            a_roll_ranges.append({
                "start": s_keep,
                "end": e_keep,
                "duration": round(e_keep - s_keep, 2),
                "source_in": round(clip_in + s_keep, 2),
                "source_out": round(clip_in + e_keep, 2),
            })

        cuts_data = [c.to_dict() for c in detected_cuts]

        # -------------------------------------------------------------
        # 5. Execute AI Editorial Intelligence Pipeline
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.editorial.pipeline import editorial_pipeline
        available_assets = []
        try:
            from ai_broll_autopilot.core.database import db
            available_assets = db.list_broll_assets(niche_id=niche_id, limit=60)
        except Exception:
            pass

        spec, quality_report = editorial_pipeline.process(
            source_media=source_media,
            transcript_segments=transcript_segments,
            video_duration=clip_duration,
            available_broll_assets=available_assets,
            custom_hook=custom_hook or (clip_candidate.hook_text if clip_candidate else None),
            clip_interval=(clip_in, clip_out),
            niche_profile=niche,
            style_profile=style,
        )

        # 6. Build Subtitles Structure from Segments
        subtitles = self._build_timed_subtitles(clip_segments, style)

        shots_data = [
            {
                "shot_id": s.shot_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration,
                "category": s.subject_category,
                "search_query": s.search_query,
                "dialogue_trigger": s.reason,
                "rationale": s.reason,
                "narrative_role": s.narrative_role.value,
                "emotional_intent": s.emotional_intent,
                "confidence": s.scores.confidence,
                "pacing_category": s.pacing_category.value,
                "shot_type": s.shot_type.value,
                "asset_path": s.asset_path,
            }
            for s in spec.broll_shots
        ]

        text_overlays_data = [
            {
                "id": c.caption_id,
                "text": c.text,
                "start_time": c.start_time,
                "duration": c.duration,
                "position": c.position,
                "behind_subject": c.behind_subject,
                "emphasis_color": c.highlight_color,
            }
            for c in spec.captions
        ]

        # 6b. Content-Aware Rapid Razor Captions
        razor_captions_data = []
        try:
            from ai_broll_autopilot.services.razor_caption.engine import RazorCaptionEngine
            broll_active_times = [
                (float(s["start_time"]), float(s["end_time"]))
                for s in shots_data if s.get("asset_path")
            ]
            razor_engine = RazorCaptionEngine(
                max_group_size=3 if getattr(style, "reference_style", False) else 5
            )
            events = razor_engine.process(
                segments=clip_segments,
                broll_active_times=broll_active_times,
                editorial_intents=spec.edit_intents,
            )
            razor_captions_data = [e.to_edit_plan_entry() for e in events]
        except Exception as re_err:
            logger.warning(f"Could not generate Razor captions: {re_err}")

        # -------------------------------------------------------------
        # 7. Content-Aware Motion Graphics Engine
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.graphics_engine import graphics_engine
        detected_graphics = graphics_engine.generate_graphics(
            transcript_segments=clip_segments,
            video_duration=clip_duration,
            title=title,
            highlight_color=style.highlight_color,
        )
        graphics_data = [g.to_dict() for g in detected_graphics]

        zooms_data = [
            {
                "time": cm.timestamp,
                "scale": cm.scale,
                "duration": cm.duration,
                "reason": cm.reason,
                "easing": "ease-out",
            }
            for cm in spec.camera_moves
        ]

        audio_cues_data = {
            "bgm_ducking": True,
            "bgm_volume": style.bgm_ducking_volume,
            "sfx": [
                {
                    "id": cue.cue_id,
                    "event_type": cue.event_type.value,
                    "time": cue.timestamp,
                    "duration": cue.duration,
                    "file": cue.sound_file,
                    "volume": cue.volume,
                    "reason": cue.reason,
                    "synced_with": cue.synced_with,
                }
                for cue in spec.sfx_cues
            ],
        }

        cadence_profile = {
            "rhythm_pacing": style.broll_cut_pacing,
            "default_shot_duration": style.default_broll_duration,
            "max_broll_ratio": niche.editing.max_broll_ratio,
            "zoom_intensity": style.zoom_intensity,
            "is_podcast": is_podcast,
        }

        # -------------------------------------------------------------
        # 8. Post-Render Visual QA Simulation
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.visual_qa import visual_qa
        qa_result = visual_qa.verify_rendered_video(
            video_path=source_media.get("path", ""),
            target_duration=clip_duration,
        )

        plan = EditPlan(
            plan_id=plan_id,
            title=f"AI Edit: {spec.hook.tightened_text[:40]}",
            target_duration=clip_duration,
            source_media=source_media,
            clip_interval={"in_point": clip_in, "out_point": clip_out},
            niche=niche.to_dict(),
            style=style.to_dict(),
            version="2.1",
            cuts=cuts_data,
            keep_intervals=keep_intervals,
            a_roll_ranges=a_roll_ranges,
            shots=shots_data,
            text_overlays=text_overlays_data,
            graphics=graphics_data,
            subtitles=subtitles,
            razor_captions=razor_captions_data,
            zooms=zooms_data,
            audio_cues=audio_cues_data,
            cadence_profile=cadence_profile,
            editorial_spec=spec.to_dict(),
            quality_report=quality_report.to_dict(),
            visual_qa=qa_result.to_dict(),
            review_items=[
                {"type": "cut", "count": len(cuts_data)},
                {"type": "shot", "count": len(shots_data)},
                {"type": "graphic", "count": len(graphics_data)},
            ],
        )

        # -------------------------------------------------------------
        # 9. Iterative Review & Auto-Repair Pass
        # -------------------------------------------------------------
        from ai_broll_autopilot.services.iterative_editor import iterative_editor
        repair_result = iterative_editor.audit_and_repair_plan(plan)
        if repair_result.repaired_items and plan.quality_report:
            plan.quality_report["repaired_items"] = repair_result.repaired_items

        return plan

    async def _plan_with_llm(
        self,
        clip_segments: List[Dict[str, Any]],
        clip_duration: float,
        niche: NicheProfile,
        style: StyleProfile,
        custom_hook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prompt Gemini to create high-retention edit structure respecting niche constraints."""
        max_broll_ratio = niche.editing.max_broll_ratio
        max_broll_seconds = clip_duration * max_broll_ratio
        default_shot_dur = style.default_broll_duration
        target_shots = max(1, min(6, int(max_broll_seconds / default_shot_dur)))

        formatted_segs = "\n".join([
            f"[{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}"
            for s in clip_segments
        ])

        prompt = f"""You are the Master AI Video Editor & Director for high-retention vertical short-form video (TikTok, YouTube Shorts, Instagram Reels).

CONTENT NICHE: {niche.name} ({niche.id})
DESCRIPTION: {niche.description}
VISUAL KEYWORDS: {', '.join(niche.visual_keywords[:15])}
B-ROLL CATEGORIES: {', '.join(niche.broll_categories)}
AVOID: {', '.join(niche.avoid)}

VISUAL STYLE: {style.name}
DEFAULT B-ROLL PACING: {style.broll_cut_pacing} (~{default_shot_dur}s per shot)
TOTAL CLIP DURATION: {clip_duration:.1f}s
MAX B-ROLL COVERAGE: {max_broll_ratio*100:.0f}% (~{max_broll_seconds:.1f}s total B-roll)
TARGET NUMBER OF B-ROLL SHOTS: {target_shots}
STYLE GUIDELINES:
{chr(10).join(f"- {g}" for g in style.editorial_guidelines)}

DIRECTOR RULES:
1. The speaker's face MUST be visible for the opening hook (first 0.6s to 1.0s) unless the dialogue requires an immediate literal visual.
2. Cutaways MUST directly illustrate spoken keywords, actions, claims, reveals, reactions, or visual metaphors. Never add generic filler just to cover time.
3. Every B-roll shot MUST specify 2-4 clean retrieval queries for the SAME visual event; vary wording, not meaning.
4. Favor varied cadence: mostly 0.8-1.8s inserts, with occasional 2.5-4.0s holds when a visual deserves to breathe.
5. Captions should follow the spoken rhythm and emphasis. For center-stack styles, use short phrase chunks (usually 1-3 words per line) rather than long full-sentence blocks.
6. Use 1-3 editorial text callouts only when they add meaning; do not duplicate the spoken caption verbatim.
7. Use restrained punch-ins (scale {style.zoom_intensity:.3f}) only on emphatic beats. Never use large digital zooms to fake energy.
8. Use transition effects sparingly. A glitch/analog beat belongs only on a major change in idea or visual world.
9. SFX should accent meaningful cuts/reveals rather than firing on every edit. Duck BGM to {style.bgm_ducking_volume} during spoken dialogue.

CLIP TRANSCRIPT:
{formatted_segs}

Respond ONLY with valid JSON matching:
{{
  "hook_title": "{custom_hook or 'KEY TAKEAWAY'}",
  "text_overlays": [
    {{
      "id": "overlay_1",
      "text": "HOOK PHRASE",
      "start_time": 0.5,
      "duration": 2.0,
      "position": "center",
      "emphasis_color": "{style.highlight_color}"
    }}
  ],
  "shots": [
    {{
      "shot_id": "broll_1",
      "start_time": <seconds relative to 0.0>,
      "end_time": <seconds>,
      "duration": <seconds>,
      "category": "<one of the broll categories>",
      "search_query": "<2-4 search keywords for footage>",
      "dialogue_trigger": "<quote from transcript>",
      "rationale": "<why this cutaway enhances viewer retention>"
    }}
  ],
  "zooms": [
    {{
      "time": <seconds>,
      "scale": {style.zoom_intensity},
      "duration": 0.3,
      "easing": "ease-out"
    }}
  ],
  "audio_cues": {{
    "bgm_ducking": true,
    "bgm_volume": {style.bgm_ducking_volume},
    "sfx_triggers": [
      {{"time": 0.5, "sound": "whoosh", "volume": 0.4}}
    ]
  }}
}}"""

        models_to_try = [self.model_name] + [m for m in getattr(Config, "GEMINI_FALLBACK_MODELS", []) if m != self.model_name]
        response = None
        last_err = None
        for model_cand in models_to_try:
            try:
                def _call_model(cand=model_cand):
                    return self.client.models.generate_content(
                        model=cand,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            http_options=types.HttpOptions(
                                retry_options=types.HttpRetryOptions(attempts=1),
                                timeout=10000,
                            )
                        )
                    )
                response = await asyncio.to_thread(_call_model)
                if response and response.text:
                    break
            except Exception as me:
                last_err = me
                continue
        if not response or not response.text:
            raise last_err or RuntimeError("No response from Gemini")

        raw_json = _clean_json_str(response.text)
        return json.loads(raw_json)

    def _plan_algorithmic(
        self,
        clip_segments: List[Dict[str, Any]],
        clip_duration: float,
        niche: NicheProfile,
        style: StyleProfile,
        custom_hook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deterministic rule-based edit director respecting niche and style parameters."""
        max_broll_seconds = clip_duration * niche.editing.max_broll_ratio
        shot_duration = style.default_broll_duration
        if style.caption_layout == "center_stack":
            # Reference-style pacing: short visual inserts with occasional longer holds.
            shot_duration = min(1.8, max(0.8, shot_duration))
        target_shots = max(1, min(7, int(max_broll_seconds / max(0.8, shot_duration))))

        # 1. Identify visual keywords spoken in segments
        niche_kws = {kw.lower(): kw for kw in niche.visual_keywords}
        keyword_hits = []

        for seg in clip_segments:
            st = seg["start"]
            # Skip first 1.0s to preserve speaker hook
            if st < 1.0:
                continue
            text_lower = seg["text"].lower()
            for kw_lower, kw_orig in niche_kws.items():
                if kw_lower in text_lower:
                    keyword_hits.append({
                        "time": st,
                        "keyword": kw_orig,
                        "text": seg["text"],
                    })

        # 2. Schedule B-Roll shots spaced across the timeline
        shots = []
        allocated_time = 0.9  # Preserve a visible speaker hook, then cut on the next meaningful beat.
        step = max(1.4, (clip_duration - 1.5) / max(1, target_shots))

        for i in range(target_shots):
            shot_start = round(allocated_time, 2)
            shot_end = round(min(clip_duration - 0.5, shot_start + shot_duration), 2)
            actual_dur = round(shot_end - shot_start, 2)
            if actual_dur < 1.0:
                break

            # Find matching keyword near this timestamp if possible
            matched_kw = niche.visual_keywords[i % len(niche.visual_keywords)]
            for hit in keyword_hits:
                if abs(hit["time"] - shot_start) <= 2.5:
                    matched_kw = hit["keyword"]
                    break

            cat = niche.broll_categories[i % len(niche.broll_categories)]

            shots.append({
                "shot_id": f"broll_{i+1}",
                "start_time": shot_start,
                "end_time": shot_end,
                "duration": actual_dur,
                "category": cat,
                "search_query": f"{niche.name} {matched_kw}",
                "dialogue_trigger": f"Illustrates {matched_kw}",
                "rationale": f"Contextual cutaway matching topic '{matched_kw}' in {niche.name}.",
            })

            allocated_time += actual_dur + step

        # 3. Create Hook Overlay Card
        hook_text = custom_hook
        if not hook_text and clip_segments:
            first_words = clip_segments[0]["text"].split()[:5]
            hook_text = " ".join(first_words).upper()
        if not hook_text:
            hook_text = niche.name.upper()

        text_overlays = [{
            "id": "overlay_hook",
            "text": hook_text,
            "start_time": 0.35,
            "duration": 1.8,
            "position": "center",
            "behind_subject": False,
            "emphasis_color": style.highlight_color,
        }]

        # 4. Schedule Punch-in Zooms
        zooms = []
        zoom_times = [round(clip_duration * 0.35, 2), round(clip_duration * 0.70, 2)]
        for zt in zoom_times:
            if zt < clip_duration - 2.0:
                zooms.append({
                    "time": zt,
                    "scale": style.zoom_intensity,
                    "duration": 0.25,
                    "easing": "ease-out",
                })

        # 5. Audio Cues
        sfx_triggers = []
        for shot in shots:
            sfx_triggers.append({
                "time": shot["start_time"],
                "sound": "whoosh",
                "volume": 0.35,
            })

        audio_cues = {
            "bgm_ducking": True,
            "bgm_volume": style.bgm_ducking_volume,
            "sfx_triggers": sfx_triggers,
        }

        return {
            "hook_title": hook_text,
            "text_overlays": text_overlays,
            "shots": shots,
            "zooms": zooms,
            "audio_cues": audio_cues,
        }

    def _build_timed_subtitles(
        self,
        clip_segments: List[Dict[str, Any]],
        style: StyleProfile,
    ) -> List[Dict[str, Any]]:
        """Construct word-level timed subtitle structures compatible with OpenReel."""
        if getattr(style, "reference_style", False):
            all_words: List[Dict[str, Any]] = []
            for seg in clip_segments:
                st = float(seg.get("start", 0.0))
                et = float(seg.get("end", st))
                words = seg.get("words", []) or []
                if words:
                    for word in words:
                        text = str(word.get("word", word.get("text", ""))).strip()
                        if text:
                            all_words.append({
                                "text": text,
                                "startTime": round(float(word.get("start", st)), 3),
                                "endTime": round(float(word.get("end", et)), 3),
                            })
                else:
                    tokens = str(seg.get("text", "")).split()
                    if tokens:
                        token_dur = max(0.01, et - st) / len(tokens)
                        for idx, token in enumerate(tokens):
                            all_words.append({
                                "text": token,
                                "startTime": round(st + idx * token_dur, 3),
                                "endTime": round(st + (idx + 1) * token_dur, 3),
                            })

            subtitles: List[Dict[str, Any]] = []
            group_size = max(2, min(4, int(getattr(style, "caption_words_per_group", 3))))
            group: List[Dict[str, Any]] = []
            subtitle_index = 1
            for word in all_words:
                group.append(word)
                span = float(word["endTime"]) - float(group[0]["startTime"])
                token = str(word["text"]).rstrip()
                should_break = (
                    len(group) >= group_size
                    or token.endswith((".", "!", "?", ",", ";", ":"))
                    or span >= 1.65
                )
                if should_break:
                    subtitles.append(self._build_reference_subtitle_group(style, group, subtitle_index))
                    subtitle_index += 1
                    group = []
            if group:
                subtitles.append(self._build_reference_subtitle_group(style, group, subtitle_index))
            return subtitles

        subtitles = []
        for i, seg in enumerate(clip_segments):
            st = seg["start"]
            et = seg["end"]
            text = seg["text"].strip()
            if not text:
                continue

            words = seg.get("words", [])
            timed_words = []
            if words:
                for w in words:
                    timed_words.append({
                        "text": w.get("word", "").strip(),
                        "startTime": max(0.0, round(w.get("start", st), 2)),
                        "endTime": max(0.0, round(w.get("end", et), 2)),
                    })
            else:
                raw_words = text.split()
                if raw_words:
                    word_dur = (et - st) / len(raw_words)
                    for j, rw in enumerate(raw_words):
                        timed_words.append({
                            "text": rw,
                            "startTime": round(st + j * word_dur, 2),
                            "endTime": round(st + (j + 1) * word_dur, 2),
                        })

            subtitles.append({
                "id": f"sub_{i+1:03d}",
                "text": text,
                "startTime": st,
                "endTime": et,
                "animationStyle": style.caption_animation_style,
                "motionProfile": "word-pop",
                "motionRecipe": "motion-anything:word-pop",
                "behind_subject": False,
                "style": style.to_openreel_subtitle_style(),
                "words": timed_words,
            })

        return subtitles

    @staticmethod
    def _build_reference_subtitle_group(
        style: StyleProfile,
        group: List[Dict[str, Any]],
        index: int,
    ) -> Dict[str, Any]:
        start = float(group[0]["startTime"])
        end = max(start + 0.05, float(group[-1]["endTime"]))
        return {
            "id": f"sub_{index:03d}",
            "text": " ".join(str(word["text"]).strip() for word in group),
            "startTime": round(start, 3),
            "endTime": round(end, 3),
            "animationStyle": style.caption_animation_style,
            "motionProfile": style.caption_animation_style or "word-pop",
            "motionRecipe": f"motion-anything:{style.caption_animation_style or 'word-pop'}",
            "behind_subject": False,
            "style": {
                **style.to_openreel_subtitle_style(),
                "fontSize": max(48, int(style.font_size)),
                "highlightColor": style.highlight_color,
            },
            "words": [
                {
                    "text": str(word["text"]),
                    "startTime": float(word["startTime"]),
                    "endTime": float(word["endTime"]),
                }
                for word in group
            ],
        }


# Global instance
edit_director = EditDirectorService()

```

============================================================
FILE: ai_broll_autopilot/services/timeline.py
============================================================

```python
"""Timeline Engine calculating tracks, dynamic transitions, and multi-track audio mixing."""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class TimelineEngine:
    """Manages timeline calculation, dynamic visual transitions, and multi-track audio filtergraphs."""

    def __init__(self, target_width: int = 1080, target_height: int = 1920, target_fps: int = 30):
        self.width = target_width
        self.height = target_height
        self.fps = target_fps

    def build_filtergraph(
        self,
        shots: List[Dict[str, Any]],
        audio_sfx_list: List[Dict[str, Any]] = None,
        ass_subtitles_path: str = None,
        bgm_stream_idx: int = None,
        bgm_volume: float = 0.15,
        ducking_enabled: bool = True,
        watermark_stream_idx: int = None,
        watermark_position: str = "bottom_safe",
        watermark_scale: float = 0.28,
        frame_overlay_stream_idx: int = None,
        viewport: Tuple[int, int, int, int] = None,
        behind_subject_text: Dict[str, Any] = None,
        subject_matte_stream_idx: int = None,
        behind_subject_ass_path: str = None,
        layout_mode: str = "single",
        cyber_grid_backdrop_idx: int = None,
        cyber_grid_mask_before_idx: int = None,
        cyber_grid_mask_after_idx: int = None,
        reference_style: bool = False,
        reference_card_mask_idx: int = None,
        reference_card_width_ratio: float = 0.944,
        reference_card_height_ratio: float = 0.574,
        reference_card_radius: int = 52,
    ) -> Tuple[str, str, str]:
        """Construct FFmpeg complex filtergraph for compositing B-roll video transitions,
        subject-aware typography and behind-subject captions, frame overlay mask, and multi-track audio mixing with BGM auto-ducking.

        Returns:
            (filtergraph_string, final_video_layer_name, final_audio_layer_name)
        """
        filters = []
        audio_sfx_list = audio_sfx_list or []
        active_broll_intervals = []

        reference_mask_labels = []
        if reference_style and reference_card_mask_idx is not None:
            reference_mask_labels = [f"ref_mask_{i}" for i in range(len(shots) + 1)]
            filters.append(
                f"[{reference_card_mask_idx}:v]fps={self.fps},format=gray,"
                f"split={len(reference_mask_labels)}"
                + "".join(f"[{label}]" for label in reference_mask_labels)
            )

        # -------------------------------------------------------------
        # 1. Base Video Normalization & Layout Setup
        # -------------------------------------------------------------
        if layout_mode == "before_after_cyber_grid" and cyber_grid_backdrop_idx is not None:
            # Dual-card Cyber Grid Before & After Compositing
            filters.append("[0:v]split=2[v_raw][v_proc]")

            # Left Card: BEFORE (352x600, raw video, rounded corners)
            filters.append(
                f"[v_raw]scale=352:600:force_original_aspect_ratio=increase,crop=352:600,setsar=1,fps={self.fps}[v_b_crop]"
            )
            filters.append(f"[{cyber_grid_mask_before_idx}:v]scale=352:600[m_b]")
            filters.append("[v_b_crop][m_b]alphamerge[v_before]")

            # Right Card: AFTER (600x1060, punch-in zoom 1.40x, color grading, cutaway B-roll overlays, rounded corners)
            filters.append(
                f"[v_proc]scale=600*1.40:1060*1.40:force_original_aspect_ratio=increase,"
                f"crop=600:1060:(in_w-600)/2:min(in_h-1060\\,in_h*0.10),setsar=1,fps={self.fps},"
                f"eq=contrast=1.20:saturation=1.28:brightness=-0.02,unsharp=5:5:0.8:5:5:0.0[v_a_graded]"
            )

            # Overlay B-roll shots inside the AFTER card
            current_after = "v_a_graded"
            for idx, shot in enumerate(shots, start=1):
                if not shot.get("asset_path"):
                    continue
                start_t = float(shot["start_time"])
                end_t = float(shot["end_time"])
                active_broll_intervals.append((start_t, end_t))
                speed = float(shot.get("speed") or 1.0)
                broll_stream = f"[{idx}:v]"
                scaled_broll = f"broll_after_{idx}"
                next_after = f"after_layer_{idx}"
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"scale=600:1060:force_original_aspect_ratio=increase,crop=600:1060,setsar=1,fps={self.fps},"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_after}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_after}]"
                )
                current_after = next_after

            # Apply rounded corner alpha mask to the AFTER card
            filters.append(f"[{cyber_grid_mask_after_idx}:v]scale=600:1060[m_a]")
            filters.append(f"[{current_after}][m_a]alphamerge[v_after]")

            # Composite both cards onto the 1080x1920 cyber grid backdrop
            filters.append(
                f"[{cyber_grid_backdrop_idx}:v]scale={self.width}:{self.height},setsar=1,fps={self.fps}[bg_canvas]"
            )
            filters.append("[bg_canvas][v_before]overlay=64:550:eof_action=pass[comp_b]")
            filters.append("[comp_b][v_after]overlay=440:320:eof_action=pass[cyber_comp]")
            current_layer = "cyber_comp"
        else:
            if reference_style and reference_card_mask_idx is not None:
                # Reference style: a centered editorial card on a near-black canvas.
                # Measurements are based on the supplied final edit: ~94% canvas width
                # and ~57% canvas height, with strongly rounded corners.
                card_w = int(round(self.width * reference_card_width_ratio))
                card_h = int(round(self.height * reference_card_height_ratio))
                card_w -= card_w % 2
                card_h -= card_h % 2
                card_x = (self.width - card_w) // 2
                card_y = (self.height - card_h) // 2

                reference_scale = (
                    f"scale={card_w}:{card_h}:force_original_aspect_ratio=increase,"
                    f"crop={card_w}:{card_h},setsar=1,fps={self.fps},"
                    f"eq=contrast=1.05:saturation=1.03:brightness=-0.01"
                )
                filters.append(f"[0:v]{reference_scale}[base_card]")
                filters.append("[base_card][ref_mask_0]alphamerge[base_card_rounded]")
                filters.append(
                    f"color=c=#050505:s={self.width}x{self.height}:r={self.fps}:d=300[reference_canvas]"
                )
                filters.append(
                    f"[reference_canvas][base_card_rounded]overlay={card_x}:{card_y}:eof_action=pass[base]"
                )

                scale_and_pad = (
                    f"scale={card_w}:{card_h}:force_original_aspect_ratio=increase,"
                    f"crop={card_w}:{card_h},setsar=1,fps={self.fps},"
                    f"eq=contrast=1.05:saturation=1.03:brightness=-0.01"
                )
                current_layer = "base"
            elif viewport:
                vp_x, vp_y, vp_w, vp_h = viewport
                scale_and_pad = (
                    f"scale={vp_w}:{vp_h}:force_original_aspect_ratio=increase,"
                    f"crop={vp_w}:{vp_h},pad={self.width}:{self.height}:{vp_x}:{vp_y}:color=black,setsar=1,fps={self.fps}"
                )
                filters.append(f"[0:v]{scale_and_pad}[base]")
                current_layer = "base"
            else:
                scale_and_pad = (
                    f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps}"
                )
                filters.append(f"[0:v]{scale_and_pad}[base]")
                current_layer = "base"

            # If subject matte compositing is enabled, split base into background and subject foreground source
            if subject_matte_stream_idx is not None and not reference_style:
                filters.append("[base]split=2[base_bg][subject_src]")
                current_layer = "base_bg"

        # -------------------------------------------------------------
        # 1b. Backward-Compatible Subject-Aware Layered Text Overlay
        # -------------------------------------------------------------
        if behind_subject_text and behind_subject_text.get("text") and not behind_subject_ass_path:
            raw_text = behind_subject_text.get("text", "").replace("'", "")
            t_start = float(behind_subject_text.get("start_time", 0.5))
            t_dur = float(behind_subject_text.get("duration", 2.5))
            t_end = t_start + t_dur
            pos_y = float(behind_subject_text.get("transform", {}).get("position", {}).get("y", 0.28))
            font_size = int(behind_subject_text.get("style", {}).get("fontSize", 68))
            font_color = behind_subject_text.get("style", {}).get("color", "yellow")
            if font_color.startswith("#"):
                font_color = "0x" + font_color[1:]

            drawtext_flt = (
                f"drawtext=text='{raw_text}':fontsize={font_size}:fontcolor={font_color}:"
                f"bordercolor=black:borderw=5:x=(w-text_w)/2:y={int(self.height * pos_y)}:"
                f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
            )

            if subject_matte_stream_idx is not None:
                filters.append(f"[{current_layer}]{drawtext_flt}[bg_with_text]")
                filters.append(
                    f"[{subject_matte_stream_idx}:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},format=gray[subject_mask]"
                )
                filters.append(f"[subject_src][subject_mask]alphamerge[subject_fg]")
                filters.append(
                    f"[bg_with_text][subject_fg]overlay=0:0:enable='between(t,{t_start:.2f},{t_end:.2f})':eof_action=pass[layer_subj_comp]"
                )
                current_layer = "layer_subj_comp"
            else:
                filters.append(f"[{current_layer}]{drawtext_flt}[layer_subj_txt]")
                current_layer = "layer_subj_txt"

        # -------------------------------------------------------------
        # 2. B-Roll Video Overlays with Dynamic Transitions (Single Layout)
        # -------------------------------------------------------------
        if layout_mode != "before_after_cyber_grid":
            for idx, shot in enumerate(shots, start=1):
                if not shot.get("asset_path"):
                    continue

                broll_stream = f"[{idx}:v]"
                scaled_broll = f"broll_{idx}"
                next_layer = f"layer_{idx}"

                start_t = float(shot["start_time"])
                end_t = float(shot["end_time"])
                active_broll_intervals.append((start_t, end_t))
                duration = max(0.2, end_t - start_t)

                trans = shot.get("transition", {})
                type_in = trans.get("type_in", "dissolve")
                from ai_broll_autopilot.config import Config
                is_streamer_or_meme = (
                    shot.get("style") == "meme" or
                    any(k in str(shot.get("meme_template", "")).lower() for k in ("speed", "caseoh", "jynx", "homeless", "pornstar", "shave", "doctor", "chad", "harold")) or
                    any(k in str(shot.get("search_prompt", "")).lower() for k in ("speed", "caseoh", "jynx", "streamer"))
                )
                speed = float(shot.get("speed") or (Config.STREAMER_SPEED_MULTIPLIER if is_streamer_or_meme else Config.BROLL_SPEED_MULTIPLIER))

                if reference_style:
                    type_in = "cut"

                # Snappy fast-paced transitions (0.18s max)
                dur_in = min(0.20, trans.get("duration_in", 0.18))
                dur_out = min(0.20, trans.get("duration_out", 0.18))

                # Apply transition effects with high-velocity speed acceleration
                if reference_style:
                    reference_card_label = f"broll_ref_card_{idx}"
                    mask_label = reference_mask_labels[idx] if idx < len(reference_mask_labels) else None
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    if mask_label:
                        filters.append(
                            f"[{scaled_broll}][{mask_label}]alphamerge[{reference_card_label}]"
                        )
                    else:
                        reference_card_label = scaled_broll
                    filters.append(
                        f"[{current_layer}][{reference_card_label}]"
                        f"overlay=x='(W-w)/2':y='(H-h)/2':"
                        f"enable='between(t,{start_t:.2f},{end_t:.2f})':"
                        f"eof_action=pass[{next_layer}]"
                    )
                elif type_in == "slide_left":
                    # Whip slide in from right
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},"
                        f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(1-(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                    filters.append(
                        f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                    )
                elif type_in == "slide_right":
                    # Whip slide in from left
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},"
                        f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(-1+(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                    filters.append(
                        f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                    )
                elif type_in == "cut":
                    # Direct hard cut
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},"
                        f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    filters.append(
                        f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                    )
                else:
                    # Default: Smooth crossfade alpha dissolve (in and out) with speedup
                    shot_dur = max(0.4, end_t - start_t)
                    fade_out_st = max(0.0, shot_dur - dur_out)
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},"
                        f"format=yuva420p,"
                        f"fade=t=in:st=0:d={dur_in:.2f}:alpha=1,"
                        f"fade=t=out:st={fade_out_st:.2f}:d={dur_out:.2f}:alpha=1,"
                        f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    filters.append(
                        f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                    )

                current_layer = next_layer

        # -------------------------------------------------------------
        # 2c. Subject-Aware Layered Caption Compositing (Captions Behind Subject)
        # -------------------------------------------------------------
        if behind_subject_ass_path:
            import os
            from pathlib import Path
            if os.path.exists(behind_subject_ass_path):
                clean_behind_ass = str(Path(behind_subject_ass_path).resolve()).replace('\\', '/').replace(':', '\\:')
                # Burn behind-subject captions onto the composed background
                filters.append(f"[{current_layer}]subtitles='{clean_behind_ass}'[caption_under_subject]")

                if subject_matte_stream_idx is not None:
                    # Prepare subject mask from matte stream
                    filters.append(
                        f"[{subject_matte_stream_idx}:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                        f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},format=gray[subject_mask]"
                    )
                    # Merge A-roll RGB with alpha mask to get isolated foreground subject
                    filters.append(f"[subject_src][subject_mask]alphamerge[subject_fg]")

                    # B-Roll occlusion protection: ensure A-roll subject does NOT appear over active B-roll
                    if active_broll_intervals:
                        broll_cond = "+".join(f"between(t,{st:.2f},{et:.2f})" for st, et in active_broll_intervals)
                        enable_expr = f":enable='not({broll_cond})'"
                    else:
                        enable_expr = ""

                    filters.append(
                        f"[caption_under_subject][subject_fg]overlay=0:0{enable_expr}:eof_action=pass[subject_caption_layer]"
                    )
                    current_layer = "subject_caption_layer"
                else:
                    # Graceful fallback: keep captions visible without subject occlusion
                    current_layer = "caption_under_subject"

        # -------------------------------------------------------------
        # 3. Normal Kinetic Subtitle Burn-In (Overlayed on top of subject layer)
        # -------------------------------------------------------------
        if ass_subtitles_path:
            import os
            from pathlib import Path
            if os.path.exists(ass_subtitles_path):
                clean_ass = str(Path(ass_subtitles_path).resolve()).replace('\\', '/').replace(':', '\\:')
                filters.append(f"[{current_layer}]subtitles='{clean_ass}'[subbed_v]")
                current_layer = "subbed_v"

        # -------------------------------------------------------------
        # 4. Campaign Frame Overlay (Torn Paper Mask & Header/Watermark)
        # -------------------------------------------------------------
        if frame_overlay_stream_idx is not None:
            framed_layer = "framed_layer"
            filters.append(
                f"[{current_layer}][{frame_overlay_stream_idx}:v]overlay=0:0:format=auto:shortest=1[{framed_layer}]"
            )
            current_layer = framed_layer

        # -------------------------------------------------------------
        # 5. Campaign Watermark Overlay
        # -------------------------------------------------------------
        if watermark_stream_idx is not None:
            wm_in = f"[{watermark_stream_idx}:v]"
            scale_factor = watermark_scale if watermark_scale else 0.28
            target_wm_w = max(100, int(self.width * scale_factor))
            filters.append(f"{wm_in}scale={target_wm_w}:-1[scaled_wm]")

            if watermark_position == "top_safe":
                ox = "(W-w)/2"
                oy = "160"
            elif watermark_position == "top_left":
                ox = "40"
                oy = "160"
            elif watermark_position == "bottom_left":
                ox = "60"
                oy = "H-h-200"
            else:  # Default bottom_safe (centered, above lower UI and clear of captions)
                ox = "(W-w)/2"
                oy = "H-h-200"

            filters.append(
                f"[{current_layer}][scaled_wm]overlay=x='{ox}':y='{oy}':format=auto:eof_action=repeat[wm_layer]"
            )
            current_layer = "wm_layer"

        # -------------------------------------------------------------
        # 4. Multi-Track Audio Mixing (Dialogue + SFX + BGM Ducking)
        # -------------------------------------------------------------
        final_audio_layer = "final_a"
        mix_streams = ["[base_a]"]
        filters.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[base_a]")

        # 4a. Transition stingers & Foley SFX
        if audio_sfx_list:
            used_video_indices = [
                i for i in [
                    frame_overlay_stream_idx,
                    watermark_stream_idx,
                    subject_matte_stream_idx,
                    cyber_grid_backdrop_idx,
                    cyber_grid_mask_before_idx,
                    cyber_grid_mask_after_idx,
                    reference_card_mask_idx,
                ] if i is not None
            ]
            audio_inputs_start = (
                max([0, len(shots)] + used_video_indices) + 1
                if used_video_indices
                else 1 + len(shots)
            )
            for a_idx, sfx_item in enumerate(audio_sfx_list):
                stream_in = f"[{audio_inputs_start + a_idx}:a]"
                stream_out = f"sfx_{a_idx}"
                delay_ms = int(max(0.0, sfx_item["start_time"]) * 1000)
                vol = float(sfx_item.get("volume", 0.40))

                filters.append(
                    f"{stream_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol:.2f},"
                    f"adelay={delay_ms}|{delay_ms}[{stream_out}]"
                )
                mix_streams.append(f"[{stream_out}]")

        # 4b. Background Music (BGM) with Auto-Ducking
        if bgm_stream_idx is not None:
            bgm_in = f"[{bgm_stream_idx}:a]"
            vol_val = max(0.02, min(0.60, bgm_volume))
            if ducking_enabled:
                # Dynamic sidechain compression: ducks BGM volume when speaker talks
                filters.append(
                    f"{bgm_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol_val:.2f}[bgm_pre]"
                )
                filters.append(
                    f"[bgm_pre][base_a]sidechaincompress=threshold=0.07:ratio=5:attack=40:release=350[bgm_ducked]"
                )
                mix_streams.append("[bgm_ducked]")
            else:
                filters.append(
                    f"{bgm_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol_val:.2f}[bgm_ducked]"
                )
                mix_streams.append("[bgm_ducked]")

        # Final audio mix
        total_audio_inputs = len(mix_streams)
        if total_audio_inputs > 1:
            filters.append(
                f"{''.join(mix_streams)}amix=inputs={total_audio_inputs}:duration=first:dropout_transition=0:normalize=0[final_a]"
            )
        else:
            final_audio_layer = "base_a"

        return ";".join(filters), current_layer, final_audio_layer

```

============================================================
FILE: tests/test_editorial_intelligence.py
============================================================

```python
"""Unit and Integration Tests for AI Editorial Intelligence Pipeline."""

import unittest
from typing import Dict, Any, List

from ai_broll_autopilot.services.editorial.types import (
    HookCandidate,
    HookScoreBreakdown,
    EditorialMoment,
    BrollCandidateScore,
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    SfxCueDecision,
    QualityAuditReport,
    NarrativeRole,
    BrollNarrativeRole,
    SentimentCategory,
    PacingCategory,
    SfxEventType,
    ShotType,
    EditorialEditSpecification,
)
from ai_broll_autopilot.services.editorial.hook_engine import HookEngine
from ai_broll_autopilot.services.editorial.moment_analyzer import MomentAnalyzer
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine
from ai_broll_autopilot.services.editorial.broll_intelligence import BrollIntelligence
from ai_broll_autopilot.services.editorial.sound_designer import SoundDesigner
from ai_broll_autopilot.services.editorial.pacing_model import PacingModel
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.feedback_bridge import EditorialFeedbackBridge
from ai_broll_autopilot.services.editorial.pipeline import EditorialIntelligencePipeline
from ai_broll_autopilot.services.diffusion_adapter import DiffusionAdapter
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.niches import niche_registry
from ai_broll_autopilot.styles import style_registry


class TestEditorialIntelligence(unittest.TestCase):
    def setUp(self):
        self.sample_segments = [
            {"start": 0.0, "end": 2.5, "text": "So basically what happened is I was completely broke.", "words": [
                {"word": "So", "start": 0.0, "end": 0.2},
                {"word": "basically", "start": 0.2, "end": 0.6},
                {"word": "what", "start": 0.6, "end": 0.8},
                {"word": "happened", "start": 0.8, "end": 1.2},
                {"word": "is", "start": 1.2, "end": 1.4},
                {"word": "I", "start": 1.4, "end": 1.6},
                {"word": "was", "start": 1.6, "end": 1.8},
                {"word": "completely", "start": 1.8, "end": 2.2},
                {"word": "broke.", "start": 2.2, "end": 2.5},
            ]},
            {"start": 2.5, "end": 6.8, "text": "Nobody told you that 87% of creators fail in their very first year.", "words": []},
            {"start": 6.8, "end": 11.2, "text": "We analyzed over 10 million videos to discover the secret formula.", "words": []},
            {"start": 11.2, "end": 16.0, "text": "Here is the exact step-by-step framework you need to implement today.", "words": []},
            {"start": 16.0, "end": 21.0, "text": "First, never start with a boring greeting like 'Hey guys welcome back'.", "words": []},
            {"start": 21.0, "end": 26.5, "text": "Second, maintain high visual energy and cut whenever the concept shifts.", "words": []},
            {"start": 26.5, "end": 30.0, "text": "Follow these rules and your audience retention will instantly double.", "words": []},
        ]
        self.niche = niche_registry.get_profile("tech")
        self.style = style_registry.get_style("bold_zoom")

    # =========================================================================
    # 1. HOOK ENGINE TESTS
    # =========================================================================
    def test_hook_candidate_generation_and_scoring(self):
        engine = HookEngine()
        candidates = engine.generate_candidates(self.sample_segments, video_duration=30.0)
        self.assertGreater(len(candidates), 0, "Hook engine should generate candidates")

        # Highest scored candidate should be chosen
        best_hook = engine.select_winning_hook(self.sample_segments, video_duration=30.0)
        self.assertIsNotNone(best_hook)
        self.assertIsInstance(best_hook, HookCandidate)
        self.assertGreaterEqual(best_hook.scores.final_score, 0.0)
        self.assertLessEqual(best_hook.scores.final_score, 100.0)
        self.assertIsNotNone(best_hook.retention_purpose)

    def test_hook_preamble_tightener(self):
        engine = HookEngine()
        raw_text = "So basically what happened is I was completely broke."
        tightened, cut = engine.tighten_preamble(raw_text)
        self.assertIn("completely broke", tightened.lower())
        self.assertTrue(len(cut) > 0, "Preamble filler should be identified and trimmed")

    def test_hook_penalizes_greetings(self):
        engine = HookEngine()
        greeting_text = "Hey guys, welcome back to my channel! Today we are talking about coding."
        scores = engine.score_text(greeting_text)
        self.assertGreater(scores.penalties, 0.0, "Greetings must be penalized")
        self.assertLess(scores.final_score, 60.0)

    # =========================================================================
    # 2. MOMENT ANALYZER TESTS
    # =========================================================================
    def test_moment_analyzer_beats_and_sentiment(self):
        analyzer = MomentAnalyzer()
        moments = analyzer.analyze_transcript(self.sample_segments, video_duration=30.0)
        self.assertGreater(len(moments), 0, "Should generate editorial moment beats")

        for m in moments:
            self.assertIsInstance(m, EditorialMoment)
            self.assertGreaterEqual(m.duration, 2.0, "Moments should have valid duration")
            self.assertIsInstance(m.sentiment, SentimentCategory)
            self.assertIsInstance(m.narrative_role, NarrativeRole)
            self.assertGreaterEqual(m.emotional_intensity, 0.0)
            self.assertLessEqual(m.emotional_intensity, 1.0)

    # =========================================================================
    # 3. VISUAL VARIETY ENGINE TESTS
    # =========================================================================
    def test_visual_variety_penalties(self):
        variety = VisualVarietyEngine()
        variety.record_shot(shot_type=ShotType.WIDE, subject_category="person_talking", camera_motion="static")

        # Score identical shot type immediately following
        penalty = variety.calculate_variety_penalty(
            candidate_shot_type=ShotType.WIDE,
            candidate_subject="person_talking",
            candidate_motion="static",
        )
        self.assertGreater(penalty, 0.2, "Repeating identical shot type & subject must incur penalty")

        # Score contrasting shot type (e.g. screen tech with push in)
        contrast_penalty = variety.calculate_variety_penalty(
            candidate_shot_type=ShotType.SCREEN,
            candidate_subject="screen_tech",
            candidate_motion="slow_push",
        )
        self.assertLess(contrast_penalty, penalty, "Contrasting shot should incur lower penalty")

    # =========================================================================
    # 4. CONTEXTUAL B-ROLL & INTENTIONAL A-ROLL
    # =========================================================================
    def test_low_confidence_broll_rejection_for_pure_aroll(self):
        broll_intel = BrollIntelligence()
        variety = VisualVarietyEngine()
        moment = EditorialMoment(
            moment_id="m_01",
            start_time=2.5,
            end_time=6.8,
            duration=4.3,
            text="Nobody told you that 87% of creators fail in their very first year.",
            semantic_topic="creator failure",
            entities=["creators"],
            action="failing",
            sentiment=SentimentCategory.NEGATIVE,
            emotional_intensity=0.85,
            narrative_role=NarrativeRole.CLAIM,
            visual_opportunity=0.8,
            pacing_requirement=PacingCategory.DEEP_EXPLANATION,
        )

        poor_asset = {
            "title": "Sunny tropical beach palm trees",
            "tags": "beach, vacation, sunny, relax, holiday",
            "category": "lifestyle",
            "file_path": "broll/beach.mp4",
        }

        score = broll_intel.score_candidate_asset(
            moment=moment,
            asset=poor_asset,
            target_duration=4.0,
            narrative_role=BrollNarrativeRole.ILLUSTRATE,
            variety_engine=variety,
        )
        self.assertLess(score.confidence, 0.65, "Irrelevant footage must fail confidence threshold (<0.65)")

        decision = broll_intel.evaluate_and_plan_shot(
            moment=moment,
            available_assets=[poor_asset],
            variety_engine=variety,
            is_first_moment=False,
        )
        self.assertIsNone(decision, "Low-confidence assets must be rejected to intentionally retain A-Roll")

    def test_contextual_broll_acceptance_with_narrative_role(self):
        broll_intel = BrollIntelligence()
        variety = VisualVarietyEngine()
        moment = EditorialMoment(
            moment_id="m_02",
            start_time=6.8,
            end_time=11.2,
            duration=4.4,
            text="We analyzed over 10 million videos to discover the secret formula.",
            semantic_topic="video data analytics research",
            entities=["10 million videos", "data"],
            action="analyzing data",
            sentiment=SentimentCategory.TECHNICAL,
            emotional_intensity=0.75,
            narrative_role=NarrativeRole.EXPLANATION,
            visual_opportunity=0.9,
            pacing_requirement=PacingCategory.DEEP_EXPLANATION,
        )

        good_asset = {
            "title": "Data dashboard showing analytics metrics charts",
            "tags": "data, analytics, charts, research, metrics, screen",
            "category": "tech",
            "file_path": "broll/analytics.mp4",
        }

        decision = broll_intel.evaluate_and_plan_shot(
            moment=moment,
            available_assets=[good_asset],
            variety_engine=variety,
            is_first_moment=False,
        )
        self.assertIsNotNone(decision, "Relevant footage should be accepted")
        self.assertGreaterEqual(decision.scores.confidence, 0.65)
        self.assertIn(decision.narrative_role, [
            BrollNarrativeRole.ILLUSTRATE,
            BrollNarrativeRole.REINFORCE,
            BrollNarrativeRole.EXPLAIN,
            BrollNarrativeRole.EMPHASIZE,
        ])
        # Opening face safety: B-roll should start after initial face establishment (>= 1.2s)
        self.assertGreaterEqual(decision.start_time, 1.2)

    # =========================================================================
    # 5. SOUND DESIGNER & DENSITY CONTROL
    # =========================================================================
    def test_sfx_sparsity_and_density_limits(self):
        designer = SoundDesigner()
        moments = [
            EditorialMoment("m1", 0.0, 3.0, 3.0, "intro", sentiment=SentimentCategory.NEUTRAL, narrative_role=NarrativeRole.HOOK),
            EditorialMoment("m2", 3.0, 6.0, 3.0, "statistic 87%", sentiment=SentimentCategory.NEGATIVE, emotional_intensity=0.9, narrative_role=NarrativeRole.STATISTIC),
            EditorialMoment("m3", 6.0, 9.0, 3.0, "reveal secret formula", sentiment=SentimentCategory.POSITIVE, emotional_intensity=0.85, narrative_role=NarrativeRole.REVEAL),
            EditorialMoment("m4", 9.0, 12.0, 3.0, "shock fail", sentiment=SentimentCategory.TENSION, emotional_intensity=0.95, narrative_role=NarrativeRole.CLAIM),
            EditorialMoment("m5", 12.0, 15.0, 3.0, "step 1 framework", sentiment=SentimentCategory.TECHNICAL, narrative_role=NarrativeRole.EXPLANATION),
            EditorialMoment("m6", 15.0, 18.0, 3.0, "step 2 rules", sentiment=SentimentCategory.NEUTRAL, narrative_role=NarrativeRole.EXPLANATION),
        ]

        cues = designer.design_soundtrack(
            moments=moments,
            broll_shots=[],
            captions=[],
            camera_moves=[],
            total_duration=18.0,
        )
        # In an 18s video, density limit (<=6/min = ~1.8 cues) caps to at most 2 cues
        self.assertLessEqual(len(cues), 2, "SFX sparsity control must cap density to prevent acoustic clutter")

        # Spacing check: consecutive SFX must be spaced >= 3.0s apart
        for i in range(len(cues) - 1):
            gap = cues[i+1].timestamp - cues[i].timestamp
            self.assertGreaterEqual(gap, 2.9, f"SFX cues must have >=3.0s spacing, found {gap:.2f}s")

    # =========================================================================
    # 6. QUALITY GATE & AUTO-REPAIRS
    # =========================================================================
    def test_quality_gate_audit_and_auto_repair(self):
        gate = EditorialQualityGate()
        hook = HookCandidate(
            candidate_id="hook_01",
            start_time=0.0,
            end_time=3.0,
            duration=3.0,
            raw_text="So basically what happened is I was completely broke.",
            tightened_text="I was completely broke.",
            retention_purpose="CURIOSITY_GAP",
            retention_reason="Compelling personal stakes",
            scores=HookScoreBreakdown(
                curiosity_gap=90.0,
                emotional_intensity=85.0,
                specificity=80.0,
                standalone_context=85.0,
                strong_claim=75.0,
                surprise_interrupt=80.0,
                narrative_importance=85.0,
                clarity=90.0,
                penalties=0.0,
                final_score=88.0,
            ),
            is_opening=True,
        )

        # Deliberately construct an edit with a cutaway starting before 1.2s (violates opening face rule)
        early_decision = ContextualBrollDecision(
            shot_id="shot_1",
            moment_id="m_01",
            start_time=0.5,
            end_time=2.5,
            duration=2.0,
            narrative_role=BrollNarrativeRole.ILLUSTRATE,
            reason="Illustrate being broke",
            search_query="empty wallet",
            emotional_intent="Serious",
            pacing_category=PacingCategory.HIGH_ENERGY,
            scores=BrollCandidateScore(confidence=0.85, final_score=0.85),
            asset_path="broll/wallet.mp4",
        )

        spec = EditorialEditSpecification(
            spec_id="plan_test_audit",
            title="Audit Test",
            total_duration=30.0,
            hook=hook,
            moments=[
                EditorialMoment("m_01", 0.0, 3.0, 3.0, "broke", sentiment=SentimentCategory.NEGATIVE, emotional_intensity=0.8, narrative_role=NarrativeRole.HOOK),
                EditorialMoment("m_02", 3.0, 30.0, 27.0, "payoff", sentiment=SentimentCategory.POSITIVE, emotional_intensity=0.7, narrative_role=NarrativeRole.PAYOFF),
            ],
            broll_shots=[early_decision],
            captions=[],
            camera_moves=[],
            sfx_cues=[],
            energy_curve=[],
        )

        repaired_spec, report = gate.audit_and_repair(spec)

        self.assertIsInstance(report, QualityAuditReport)
        self.assertGreaterEqual(report.overall_score, 0.70)
        # Quality Gate should have auto-repaired the early start to >= 1.2s
        self.assertGreaterEqual(repaired_spec.broll_shots[0].start_time, 1.2, "Opening face rule must be auto-repaired to >=1.2s")
        self.assertGreater(len(report.repaired_items), 0, "Repairs applied should be documented in audit report")

    # =========================================================================
    # 7. FULL PIPELINE & DIFFUSION STUDIO EXECUTION
    # =========================================================================
    def test_full_pipeline_to_diffusion_studio(self):
        pipeline = EditorialIntelligencePipeline()
        source_media = {
            "path": "inputs/test_speech.mp4",
            "duration": 30.0,
            "title": "test_speech.mp4",
            "width": 1080,
            "height": 1920,
            "fps": 30,
        }

        sample_assets = [
            {"title": "Money bills cash wallet empty", "tags": "money, cash, broke, wallet", "category": "finance", "file_path": "broll/money.mp4"},
            {"title": "Video analytics dashboard charts", "tags": "data, charts, metrics", "category": "tech", "file_path": "broll/data.mp4"},
        ]

        spec, quality_report = pipeline.process(
            source_media=source_media,
            transcript_segments=self.sample_segments,
            video_duration=30.0,
            available_broll_assets=sample_assets,
            niche_profile=self.niche,
            style_profile=self.style,
        )

        self.assertIsNotNone(spec.hook)
        self.assertGreater(len(spec.moments), 0)
        self.assertGreaterEqual(quality_report.overall_score, 0.70)

        # Create EditPlan containing editorial spec and quality report
        edit_plan = EditPlan(
            plan_id="plan_test_pipeline",
            title=f"AI Edit: {spec.hook.tightened_text[:30]}",
            target_duration=30.0,
            source_media=source_media,
            clip_interval={"in_point": 0.0, "out_point": 30.0},
            niche=self.niche.to_dict(),
            style=self.style.to_dict(),
            shots=[
                {
                    "shot_id": s.shot_id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                    "category": s.subject_category,
                    "narrative_role": s.narrative_role.value,
                    "emotional_intent": s.emotional_intent,
                    "confidence": s.scores.confidence,
                    "pacing_category": s.pacing_category.value,
                    "asset_path": s.asset_path,
                }
                for s in spec.broll_shots
            ],
            text_overlays=[],
            subtitles=[],
            zooms=[],
            audio_cues={
                "sfx": [
                    {
                        "id": cue.cue_id,
                        "time": cue.timestamp,
                        "duration": cue.duration,
                        "file": cue.sound_file,
                        "volume": cue.volume,
                        "event_type": cue.event_type.value,
                        "justification": cue.reason,
                    }
                    for cue in spec.sfx_cues
                ]
            },
            editorial_spec=spec.to_dict(),
            quality_report=quality_report.to_dict(),
        )

        # Render with DiffusionAdapter
        adapter = DiffusionAdapter()
        comp = adapter.create_project(edit_plan, base_asset_url="http://127.0.0.1:8000/assets")

        # Validate Diffusion Studio Schema
        self.assertEqual(comp.get("version"), "4.0.0")
        self.assertEqual(comp.get("engine"), "diffusion")
        self.assertIn("composition", comp)
        self.assertEqual(len(comp["composition"]["layers"]), 7)

        # Validate that composition metadata contains editorial spec & quality report
        metadata = comp["composition"]["metadata"]
        self.assertIn("editorial_spec", metadata)
        self.assertIn("quality_report", metadata)
        self.assertEqual(metadata["editorial_spec"]["hook"]["tightened_text"], spec.hook.tightened_text)

        # Validate Layer 7 (SFX) has no uncurated stinger spam
        layer_sfx = next((l for l in comp["composition"]["layers"] if l["id"] == "layer_audio_sfx"), None)
        self.assertIsNotNone(layer_sfx)
        # SFX clips must be <= 3 for a 30s video
        self.assertLessEqual(len(layer_sfx["clips"]), 3)

        # Validate Bidirectional Conversion to OpenReel Schema 1.2.0
        openreel = adapter.to_openreel_project(comp)
        self.assertEqual(openreel.get("version"), "1.2.0")
        self.assertIn("project", openreel)
        self.assertIn("metadata", openreel["project"])
        self.assertIn("editorial_spec", openreel["project"]["metadata"])

    # =========================================================================
    # 8. FEEDBACK LEARNING BRIDGE
    # =========================================================================
    def test_feedback_learning_bridge(self):
        bridge = EditorialFeedbackBridge()
        bridge.record_broll_modification(
            job_id="job_test_123",
            shot_id="shot_1",
            action="KEEP",
            prompt="data analytics chart",
            asset_title="Analytics dashboard",
        )
        bridge.record_broll_modification(
            job_id="job_test_123",
            shot_id="shot_2",
            action="REMOVE",
            prompt="stock finance chart",
            feedback_text="Stay on speaker face here for emotional delivery",
        )
        bridge.record_sfx_modification(
            job_id="job_test_123",
            cue_id="cue_1",
            action="KEEP",
            sound_name="whoosh.mp3",
        )
        bridge.record_hook_override(
            job_id="job_test_123",
            ai_hook="I was completely broke.",
            user_hook="Here is how I lost everything.",
        )


if __name__ == "__main__":
    unittest.main()

```

============================================================
FILE: tests/test_timeline_distribution.py
============================================================

```python
"""Tests for full-timeline uniform B-roll distribution and gap elimination."""

import pytest
from ai_broll_autopilot.services.director import Director
from ai_broll_autopilot.campaigns.presets.default_viral import DEFAULT_VIRAL_CAMPAIGN
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.types import (
    EditorialEditSpecification,
    ContextualBrollDecision,
    HookCandidate,
    HookScoreBreakdown,
    BrollCandidateScore,
    BrollNarrativeRole,
    PacingCategory,
    ShotType,
    SentimentCategory,
)


@pytest.fixture
def mock_director():
    return Director(api_key=None)


@pytest.fixture
def sample_segments():
    return [
        {"start": 0.0, "end": 2.56, "text": "It's nice to be part of like a young growing brand"},
        {"start": 2.56, "end": 3.88, "text": "because there's no rule."},
        {"start": 4.12, "end": 5.32, "text": "So I'm like, what your role could be."},
        {"start": 5.58, "end": 6.94, "text": "You know, like I started as the Amazon guy"},
        {"start": 6.94, "end": 8.4, "text": "and as a chief revenue officer,"},
        {"start": 8.44, "end": 11.98, "text": "I got to manage all the e-commerce and also Amazon TikTok."},
        {"start": 12.58, "end": 13.94, "text": "Shopify, I got to do all the marketing."},
        {"start": 14.48, "end": 15.38, "text": "I got to run analytics,"},
        {"start": 15.96, "end": 17.18, "text": "one of the other ads supply chain."},
        {"start": 17.58, "end": 19.32, "text": "I got to, you know, do innovation."},
        {"start": 19.52, "end": 20.4, "text": "I was tell people couldn't tell you"},
        {"start": 20.4, "end": 21.52, "text": "how much iron can go into product,"},
        {"start": 21.66, "end": 23.46, "text": "but what product we should make next?"},
        {"start": 23.58, "end": 24.96, "text": "I can give good advice on, you know,"},
        {"start": 25.1, "end": 28.16, "text": "and so like, you get to experience a lot and learn a lot."},
    ]


def test_target_shots_scales_beyond_six(mock_director):
    """Verify target_shots is not capped at 6 for longer videos."""
    # For a 60-second video with 45% ratio (27s B-roll)
    target_broll_sec = 60.0 * 0.45
    max_possible = max(3, int(60.0 / 2.8))
    target_shots = max(3, min(max_possible, int(round(target_broll_sec / 2.0))))
    assert target_shots >= 10, f"Target shots for 60s video should be at least 10, got {target_shots}"


def test_tail_gap_elimination(mock_director, sample_segments):
    """Verify that an edit plan with shots clustered only in the first half is repaired across the tail."""
    video_duration = 28.3

    # Clustered shots stopping at 14.5s (leaving 13.8s empty)
    clustered_shots = [
        {"shot_id": "broll_1", "start_time": 0.4, "end_time": 1.6, "duration": 1.2, "search_prompt": "founder talking to camera"},
        {"shot_id": "broll_2", "start_time": 2.0, "end_time": 4.0, "duration": 2.0, "search_prompt": "startup team collaboration"},
        {"shot_id": "broll_3", "start_time": 4.4, "end_time": 6.9, "duration": 2.5, "search_prompt": "founder talking head"},
        {"shot_id": "broll_4", "start_time": 7.3, "end_time": 9.3, "duration": 2.0, "search_prompt": "executive analyzing dashboards"},
        {"shot_id": "broll_5", "start_time": 9.7, "end_time": 12.2, "duration": 2.5, "search_prompt": "entrepreneur speaking"},
        {"shot_id": "broll_6", "start_time": 12.6, "end_time": 14.5, "duration": 1.9, "search_prompt": "ecommerce marketing analytics"},
    ]

    repaired_shots, coverage_pct = mock_director._audit_and_fill_timeline_distribution(
        clean_shots=clustered_shots,
        segments=sample_segments,
        video_duration=video_duration,
        campaign=DEFAULT_VIRAL_CAMPAIGN,
        niche=None,
    )

    # 1. More than 6 shots must be produced
    assert len(repaired_shots) >= 8, f"Expected at least 8 shots to cover 28.3s, got {len(repaired_shots)}"

    # 2. Shots must exist in the second half (> 15.0s)
    second_half_shots = [s for s in repaired_shots if s["start_time"] >= 14.5]
    assert len(second_half_shots) >= 2, f"Expected shots in second half, got {len(second_half_shots)}"

    # 3. Maximum gap between consecutive visual cutaways must be <= 4.2 seconds
    for i in range(len(repaired_shots) - 1):
        gap = repaired_shots[i + 1]["start_time"] - repaired_shots[i]["end_time"]
        assert gap <= 4.2, f"Gap between shot {i+1} and {i+2} is too large: {gap:.2f}s"

    # 4. Final shot must end in the closing section (>= 22.0s)
    last_shot_end = repaired_shots[-1]["end_time"]
    assert last_shot_end >= 22.0, f"Last shot ends too early: {last_shot_end}s"

    # 5. Coverage must be healthy (~40-50%)
    assert 35.0 <= coverage_pct <= 55.0, f"Coverage out of bounds: {coverage_pct}%"


def test_internal_gap_filling(mock_director, sample_segments):
    """Verify that an internal 8-second dead gap is detected and filled."""
    video_duration = 28.3
    shots_with_gap = [
        {"shot_id": "broll_1", "start_time": 1.2, "end_time": 3.0, "duration": 1.8, "search_prompt": "team"},
        # 8-second gap between 3.0s and 11.0s
        {"shot_id": "broll_2", "start_time": 11.0, "end_time": 13.0, "duration": 2.0, "search_prompt": "analytics"},
        {"shot_id": "broll_3", "start_time": 15.0, "end_time": 17.0, "duration": 2.0, "search_prompt": "office"},
        {"shot_id": "broll_4", "start_time": 21.0, "end_time": 23.0, "duration": 2.0, "search_prompt": "prototype"},
    ]

    repaired_shots, coverage = mock_director._audit_and_fill_timeline_distribution(
        clean_shots=shots_with_gap,
        segments=sample_segments,
        video_duration=video_duration,
        campaign=DEFAULT_VIRAL_CAMPAIGN,
        niche=None,
    )

    # An internal shot must have been inserted into the 3.0s - 11.0s gap
    internal_shots = [s for s in repaired_shots if 3.0 < s["start_time"] < 11.0]
    assert len(internal_shots) >= 1, "Internal gap between 3.0s and 11.0s was not filled"


def test_quality_gate_stagnation_audit():
    """Verify Quality Gate audits stagnation gaps down to 4.5s."""
    q_gate = EditorialQualityGate()

    # Spec with a 10s gap (from 5s to 15s)
    mock_hook = HookCandidate(
        candidate_id="h1",
        start_time=0.0,
        end_time=3.0,
        duration=3.0,
        raw_text="Test Hook",
        tightened_text="TEST HOOK",
        retention_purpose="STRONG_CLAIM",
        retention_reason="High curiosity",
        scores=HookScoreBreakdown(final_score=75.0),
    )

    spec = EditorialEditSpecification(
        spec_id="test_spec",
        title="Test",
        total_duration=25.0,
        hook=mock_hook,
        moments=[],
        broll_shots=[
            ContextualBrollDecision(
                shot_id="b1", moment_id="m1", start_time=1.5, end_time=3.5, duration=2.0,
                narrative_role=BrollNarrativeRole.ILLUSTRATE, reason="test",
                search_query="test", emotional_intent="neutral", pacing_category=PacingCategory.NORMAL,
                scores=BrollCandidateScore(0.8, 0.8, 0.8, 0.8, 0.8, 0.8, "ACCEPT"),
                asset_path="b1.mp4", shot_type=ShotType.MEDIUM, subject_category="test", status="matched"
            ),
            # 10s stagnant gap here!
            ContextualBrollDecision(
                shot_id="b2", moment_id="m2", start_time=13.5, end_time=15.5, duration=2.0,
                narrative_role=BrollNarrativeRole.ILLUSTRATE, reason="test",
                search_query="test", emotional_intent="neutral", pacing_category=PacingCategory.NORMAL,
                scores=BrollCandidateScore(0.8, 0.8, 0.8, 0.8, 0.8, 0.8, "ACCEPT"),
                asset_path="b2.mp4", shot_type=ShotType.MEDIUM, subject_category="test", status="matched"
            ),
        ],
        captions=[],
        sfx_cues=[],
        camera_moves=[],
        energy_curve=[],
        metadata={},
    )

    repaired_spec, report = q_gate.audit_and_repair(spec)
    # The 10s stagnation must be repaired by injecting a camera punch-in
    assert len(repaired_spec.camera_moves) >= 1, "Expected camera move to repair 10s stagnation gap"
    punch = repaired_spec.camera_moves[0]
    assert 3.5 <= punch.timestamp <= 13.5, f"Punch-in timestamp {punch.timestamp} not within stagnant interval"

```

## B-ROLL AUDIT FOCUS
- Source duration must not determine editorial hold duration.
- Approved B-roll intervals must never be silently extended downstream.
- Weak candidates must fall back to A-roll.
- Proposition-level relevance must beat broad topic similarity.
- Consider bounded top-N frame/OCR/vision inspection for visible unrelated text.
- Any timing replacement must remain inside the approved interval or receive explicit re-approval.

## REPO-WIDE AUDIT APPENDIX

# GPT-6 REPO-WIDE STOCKPILE AUDIT — MASTER WORK ORDER

This appendix extends the B-roll source audit into a repository-wide engineering audit. Treat the supplied source dump plus the entire repository checkout as one system.

## OBJECTIVE
Find bugs, broken implementations, duplicate/obsolete systems, inconsistent contracts, unsafe assumptions, dead code, incorrect fallbacks, performance traps, hydration/runtime issues, and features that appear implemented in the UI but are incomplete or disconnected in the backend.

Do not blindly rewrite working features. First establish evidence, then make the smallest coherent fix.

## MANDATORY REPO-WIDE PASSES

### 1. Build / import integrity
- Run the project's actual Python test/import path.
- Run frontend typecheck/build/lint commands defined by package.json.
- Find broken imports, circular imports, missing optional dependencies, stale module paths, and code that only works in one working directory.
- Check Python/Node version assumptions against project configuration.

### 2. Duplicate implementations / merge leftovers
Search for:
- duplicate functions/classes with similar names
- old and new versions of the same engine
- parallel B-roll selectors/directors/renderers
- duplicate campaign registration
- duplicate API endpoints
- compatibility shims that are no longer needed
- dead feature flags
- stale branch/merge artifacts
- code paths that implement the same feature differently

When duplicates exist, identify the canonical implementation and explain which one should be removed or redirected.

### 3. Frontend runtime / React / Next.js
Audit every client component for:
- duplicate React keys
- hydration mismatches
- browser-only APIs during SSR
- Date.now()/Math.random()/locale-dependent rendering in initial markup
- unstable list ordering
- invalid HTML nesting
- effects that race or update after unmount
- stale closures
- excessive polling
- duplicated fetches
- state that can diverge from backend truth
- dynamic imports used incorrectly
- missing error/loading/empty states

Known observed issue to verify and fix:
`web/app/page.tsx` renders `{campaigns.map((c) => <option key={c.id}>...)}` and the running app has emitted duplicate-key warnings for `capcut_podcast_pro`. Trace the actual source of duplicate campaign records rather than merely changing the React key to an array index.

Known hydration warning from the running app included extension-injected attributes (`__processed_*`, `bis_register`) on `<body>`. Distinguish browser-extension noise from genuine application hydration defects and do not hide genuine mismatches with suppressHydrationWarning unless justified.

### 4. API / backend correctness
Audit FastAPI routes for:
- missing validation
- path traversal
- unsafe file paths
- unrestricted CORS
- incorrect authentication/authorization assumptions
- race conditions
- background task failures
- leaked file handles/processes
- subprocess shell injection
- unbounded uploads
- missing size/type checks
- swallowed exceptions
- inconsistent HTTP status codes
- duplicate endpoint behavior
- mutable global state
- stale DB state
- filesystem/DB synchronization bugs

Pay particular attention to upload, YouTube import, file streaming, B-roll swap, timeline editing, rendering, OpenReel sync, HDR, diffusion, Google Drive, and job queue endpoints.

### 5. Data model / persistence
Audit SQLite/database/job serialization for:
- schema drift
- fields written but never read
- fields read but not persisted
- incompatible old edit plans
- JSON shape inconsistencies
- partial writes
- concurrent job corruption
- missing transactions
- stale render flags
- revision counters that can go backwards
- OpenReel sync losing fields

### 6. Video pipeline / timeline invariants
Trace the full lifecycle:
input -> transcribe -> moments -> edit director -> B-roll -> memes -> captions -> SFX -> BGM -> timeline -> render -> output -> preview/download.

Check that every stage preserves:
- source duration
- approved intervals
- non-overlap rules
- A-roll fallback
- media bounds
- audio synchronization
- frame-rate assumptions
- aspect ratio
- output path
- render-stale state

No stage may silently mutate an approved editorial decision without recording why.

### 7. FFmpeg / rendering
Search all FFmpeg invocations for:
- unnecessary re-encoding
- accidental CPU encoding where NVENC is available
- repeated full-video renders
- temporary-file leaks
- incorrect pixel formats
- audio drift
- broken stream mapping
- missing `-shortest` where appropriate
- unsafe concat/filter assumptions
- accidental quality loss
- resolution changes
- filters that force expensive CPU paths
- commands that fail only on Windows
- commands that assume bash utilities

Do not optimize blindly. Preserve output correctness first, then identify safe quick-render paths.

### 8. GPU / performance
Audit:
- redundant model loads
- repeated subprocess startup
- sequential work that could safely be parallel
- unnecessary frame extraction
- repeated transcription/embedding calls
- missing caches
- huge intermediate files
- expensive operations performed for candidates that will later be rejected
- CPU/GPU copies
- VRAM spikes
- synchronous API calls inside hot paths

For the user's GTX 1050 Ti, identify safe optimizations that do not require changing quality-critical output defaults.

### 9. AI / retrieval quality
Audit:
- prompts that are too broad
- keyword-only fallbacks
- weak semantic thresholds
- score normalization mismatches
- duplicate retrieval
- hallucinated asset metadata
- candidates accepted without verification
- expensive vision/model calls performed unnecessarily
- inconsistent model configuration
- missing caching
- failures that silently downgrade to generic footage

B-roll must prioritize proposition-level visual support over generic topic similarity.

### 10. Captions / behind-subject / overlays
Audit the actual implementation, not UI labels:
- Is behind-subject truly implemented end-to-end?
- Are masks/detections applied to the final render?
- Do captions preserve word timing?
- Can overlay layers escape their intended bounds?
- Are styles consistent between preview and master render?
- Are settings persisted and reloaded correctly?

### 11. Meme engine
Audit:
- template registration
- duplicate keys
- fallback behavior
- caption injection
- SFX synchronization
- duration handling
- random/deterministic rendering
- asset existence
- failure recovery
- standalone vs shot-targeted meme behavior

Do not weaken the meme engine while fixing unrelated systems.

### 12. SFX / BGM / ducking
Audit:
- event-to-SFX mapping
- duplicate cues
- excessive cartoonish effects
- missing files
- gain normalization
- ducking sidechain behavior
- timing drift
- preview/master mismatch

Prefer subtle snap/whoosh/swipe/click/fade accents unless a deliberate meme/comedic cue is selected.

### 13. OpenReel / NLE / export
Audit serialization compatibility, schema versions, round trips, timing preservation, captions, overlays, cutaways, and whether an OpenReel edit can be reopened and rendered without losing data.

### 14. Security
Search for:
- hardcoded secrets
- tokens/API keys
- unsafe subprocess usage
- path traversal
- arbitrary URL fetching
- SSRF risks
- unrestricted CORS
- missing upload limits
- command injection
- unsafe deserialization
- exposed local filesystem paths
- debug endpoints accidentally exposed

Do not expose or reproduce secret values in the audit. Report only file/path and secret type.

### 15. Tests
Audit coverage and add tests for every confirmed high-risk defect. Prefer regression tests that reproduce the bug before fixing it.

Required categories:
- B-roll relevance
- B-roll duration
- timeline invariants
- campaign registry uniqueness
- API validation
- frontend build/typecheck
- hydration-sensitive rendering
- OpenReel round-trip
- render command construction
- fallback/error behavior

### 16. Dead / obsolete code
Find files/classes/functions that appear unused or superseded. Do not delete merely because they are not referenced by a simple search; verify dynamic imports, registry loading, CLI entry points, workflows, and plugin-style discovery first.

## KNOWN ISSUE TO INVESTIGATE FIRST

The running frontend has reported:
`Encountered two children with the same key, capcut_podcast_pro.`
The offending render is in `web/app/page.tsx` at the campaign `<option>` map.

The campaign backend uses `campaign_registry.list_campaigns()`, so trace registry construction and API serialization. Fix the duplicate data at its source. Do not mask it with `key={`${c.id}-${index}`}`.

## OUTPUT CONTRACT FOR GPT-6

Return a repository-wide engineering audit with:

1. EXECUTIVE SUMMARY
2. VERIFIED BUGS — only evidence-backed defects
3. HIGH-RISK BUGS — security/data-loss/render corruption
4. FUNCTIONAL BUGS
5. PERFORMANCE / RENDERING BOTTLENECKS
6. FRONTEND / HYDRATION ISSUES
7. B-ROLL QUALITY ISSUES
8. DUPLICATE / OBSOLETE IMPLEMENTATIONS
9. ARCHITECTURE / CONTRACT INCONSISTENCIES
10. TEST GAPS
11. SECURITY FINDINGS
12. EXACT FILE + FUNCTION LOCATIONS
13. PATCH PLAN ORDERED BY IMPACT
14. CONCRETE CODE DIFFS
15. REGRESSION TESTS
16. WHAT NOT TO CHANGE
17. POST-PATCH VERIFICATION CHECKLIST

For every finding use:
- Severity: P0/P1/P2/P3
- Confidence: confirmed / likely / needs runtime verification
- File
- Function/class
- Evidence
- Why it breaks
- Minimal fix
- Regression test
- Compatibility risk

## IMPORTANT EXECUTION RULE

GPT-6 is allowed to make changes only after identifying the exact current implementation. Do not replace working architecture with a generic rewrite. Preserve existing features and reconcile conflicting implementations into one canonical path.

The goal is not merely to produce an audit. The goal is to leave Stockpile in a state where the recommended fixes can be implemented safely in one focused engineering session.

## VERIFIED REPO FINDINGS FROM INITIAL SCAN

# VERIFIED REPOSITORY FINDINGS FOR GPT-6

These are evidence-backed observations from the current `main` scan. Treat them as starting evidence, not as an exhaustive audit. GPT-6 must trace each to runtime behavior and inspect adjacent code before patching.

## Finding 1 — Frontend duplicate campaign key warning

Observed runtime error:
`Encountered two children with the same key, capcut_podcast_pro.`

Location reported by the running Next.js app:
`web/app/page.tsx`, campaign `<option>` map.

Relevant implementation:
`campaigns.map((c) => <option key={c.id} value={c.id}>...)`

The backend campaign registry currently registers `capcut_podcast_pro` once and returns `list(self._campaigns.values())`, so the duplicate is NOT explained by an obvious duplicate dictionary registration in `ai_broll_autopilot/campaigns/registry.py`.

Required investigation:
- inspect `/api/campaigns` response at runtime
- trace frontend state population
- inspect any client-side merge/append behavior
- verify whether duplicate API responses can occur across fetches
- fix the source of duplication
- do NOT mask it with an index-based React key

## Finding 2 — CORS configuration is overly permissive

`ai_broll_autopilot/api/app.py` configures FastAPI CORS with:
- `allow_origins=["*"]`
- `allow_credentials=True`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

This is an overly broad production security configuration and must be reviewed against the actual deployment model. GPT-6 should determine the intended frontend/backend origins and replace wildcard access with an explicit allowlist where appropriate, while preserving local development.

## Finding 3 — Repo contains deterministic-rendering guidance that explicitly forbids Math.random, but runtime tooling contains Math.random

The repository's own Remotion/rendering guidance repeatedly states deterministic rendering should avoid `Math.random`. Separately, `.agents/skills/erduo-broll-loop-engineering/scripts/lean-render.mjs` uses `Date.now()` and `Math.random()` to create temporary filenames.

This is NOT automatically a rendering correctness bug because the usage shown is for unique temporary filenames rather than frame output. GPT-6 should distinguish harmless filesystem entropy from render-state randomness and must not remove it merely because a search found the token.

## Finding 4 — Large mixed-responsibility frontend surface needs audit

`web/app/page.tsx` is a very large client component managing jobs, upload/import, campaigns, B-roll swapping, cutaway insertion, memes, subtitles, BGM, HDR, OpenReel, diffusion, feedback, and timeline/editor interactions. It also dynamically imports multiple heavy modals.

This is an architecture/performance risk rather than proof of a bug. GPT-6 should inspect effect dependencies, fetch orchestration, rerender frequency, state ownership, and whether unrelated feature state causes expensive dashboard rerenders.

## Finding 5 — API server contains many global/shared service instances

`ai_broll_autopilot/api/app.py` creates module-level instances including the database, learning engine, orchestrator, HDR task dictionary, and several imported singleton services.

This may be intentional, but GPT-6 should audit concurrency, process-local state, multi-worker behavior, task lifetime, and whether state such as HDR tasks or queue state is lost/repeated when multiple API workers run.

## REQUIRED FOLLOW-UP

For each finding, GPT-6 must:
1. inspect the exact source and call graph;
2. reproduce or logically prove the defect;
3. classify severity and confidence;
4. propose the smallest fix;
5. add a regression test where feasible;
6. verify that the fix does not break existing Stockpile features.
