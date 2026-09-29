"""AI Editorial Intelligence Package for Stockpile & Diffusion Studio."""

from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialCameraSpec,
    EditorialCaptionSpec,
    EditorialEditSpecification,
    EditorialMoment,
    HookCandidate,
    HookScoreBreakdown,
    NarrativeRole,
    PacingCategory,
    QualityAuditReport,
    QualityCheckItem,
    SentimentCategory,
    SfxCueDecision,
    SfxEventType,
    ShotType,
)
from ai_broll_autopilot.services.editorial.hook_engine import HookEngine
from ai_broll_autopilot.services.editorial.moment_analyzer import MomentAnalyzer
from ai_broll_autopilot.services.editorial.broll_intelligence import BrollIntelligence
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine
from ai_broll_autopilot.services.editorial.sound_designer import SoundDesigner
from ai_broll_autopilot.services.editorial.pacing_model import PacingModel
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.feedback_bridge import (
    EditorialFeedbackBridge,
    editorial_feedback_bridge,
)
from ai_broll_autopilot.services.editorial.pipeline import (
    EditorialIntelligencePipeline,
    editorial_pipeline,
)

__all__ = [
    "HookEngine",
    "MomentAnalyzer",
    "BrollIntelligence",
    "VisualVarietyEngine",
    "SoundDesigner",
    "PacingModel",
    "EditorialQualityGate",
    "EditorialFeedbackBridge",
    "editorial_feedback_bridge",
    "EditorialIntelligencePipeline",
    "editorial_pipeline",
    "HookCandidate",
    "HookScoreBreakdown",
    "EditorialMoment",
    "BrollCandidateScore",
    "ContextualBrollDecision",
    "EditorialCaptionSpec",
    "EditorialCameraSpec",
    "SfxCueDecision",
    "EditorialEditSpecification",
    "QualityAuditReport",
    "QualityCheckItem",
    "NarrativeRole",
    "BrollNarrativeRole",
    "SentimentCategory",
    "PacingCategory",
    "SfxEventType",
    "ShotType",
]
