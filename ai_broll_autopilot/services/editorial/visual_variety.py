"""Visual Variety Engine for Editorial Cutaways.

Tracks historical visual attributes of recent timeline cuts (shot types, subjects, camera movement,
locations, and framing) to penalize repetitive footage sequences and enforce controlled visual diversity.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai_broll_autopilot.services.editorial.types import ShotType

logger = logging.getLogger("autopilot.editorial.variety")


@dataclass
class VisualShotFingerprint:
    """Historical snapshot of a placed visual cutaway."""
    shot_id: str
    shot_type: ShotType
    camera_movement: str   # 'static', 'pan', 'slow_push', 'dolly', 'handheld', 'aerial'
    subject_category: str  # 'person_action', 'screen_tech', 'office_work', 'landscape', 'data_chart', 'detail_macro'
    location: str          # 'indoor', 'outdoor', 'studio', 'abstract'
    color_tone: str        # 'warm', 'cool', 'dark', 'bright'
    semantic_theme: str    # e.g., 'real_estate', 'finance', 'basketball', 'podcast'


class VisualVarietyEngine:
    """Monitors sequence flow to eliminate visual monotony and repetitive B-roll."""

    # Dynamic transition recommendations: given previous shot type, what provides optimal visual contrast?
    CONTRAST_ROTATION = {
        ShotType.MEDIUM: [ShotType.DETAIL, ShotType.WIDE, ShotType.SCREEN, ShotType.CLOSE_UP],
        ShotType.WIDE: [ShotType.CLOSE_UP, ShotType.DETAIL, ShotType.MEDIUM],
        ShotType.CLOSE_UP: [ShotType.WIDE, ShotType.EXTREME_WIDE, ShotType.SCREEN],
        ShotType.DETAIL: [ShotType.WIDE, ShotType.MEDIUM, ShotType.SCREEN],
        ShotType.SCREEN: [ShotType.MEDIUM, ShotType.CLOSE_UP, ShotType.WIDE],
        ShotType.GRAPHIC: [ShotType.CLOSE_UP, ShotType.WIDE, ShotType.MEDIUM],
        ShotType.EXTREME_WIDE: [ShotType.CLOSE_UP, ShotType.DETAIL, ShotType.MEDIUM],
    }

    def __init__(self, history_size: int = 4):
        self.history: deque[VisualShotFingerprint] = deque(maxlen=history_size)

    def reset(self):
        """Reset the history for a new project/timeline."""
        self.history.clear()

    def evaluate_variety(
        self,
        candidate_shot_type: ShotType,
        subject_category: str,
        camera_movement: str = "static",
        location: str = "indoor",
        semantic_theme: str = "general",
    ) -> float:
        """Calculate variety score (0.0 to 1.0).

        Returns:
            Score from 0.0 (severely repetitive) to 1.0 (fresh, well-contrasted visual change).
        """
        if not self.history:
            return 1.0  # First cutaway is inherently fresh

        recent = self.history[-1]
        penalty = 0.0
        bonus = 0.0

        # 1. Shot Type Repetition Penalty
        if candidate_shot_type == recent.shot_type:
            penalty += 0.35
            logger.debug(f"Variety penalty: consecutive identical shot type '{candidate_shot_type.value}'")
        elif candidate_shot_type in self.CONTRAST_ROTATION.get(recent.shot_type, []):
            bonus += 0.15

        # 2. Subject Category Repetition Penalty (e.g. office -> office -> office)
        if subject_category.lower() == recent.subject_category.lower() and subject_category != "general":
            penalty += 0.40
            logger.debug(f"Variety penalty: consecutive identical subject category '{subject_category}'")

        # Check for 2 out of last 3 having the same subject
        past_subjects = [h.subject_category.lower() for h in self.history]
        if past_subjects.count(subject_category.lower()) >= 2 and subject_category != "general":
            penalty += 0.25

        # 3. Camera Movement Monotony
        if camera_movement == recent.camera_movement and camera_movement != "static":
            penalty += 0.15

        # 4. Location Contrast Bonus (indoor -> outdoor or vice versa)
        if location != recent.location and location not in ["abstract", "studio"]:
            bonus += 0.10

        variety_score = max(0.1, min(1.0, 1.0 - penalty + bonus))
        return round(variety_score, 2)

    def record_placed_shot(
        self,
        shot_id: str = "shot",
        shot_type: ShotType = ShotType.MEDIUM,
        subject_category: str = "general",
        camera_movement: str = "static",
        location: str = "indoor",
        color_tone: str = "warm",
        semantic_theme: str = "general",
    ):
        """Append an accepted B-roll shot to the variety memory."""
        self.history.append(
            VisualShotFingerprint(
                shot_id=shot_id,
                shot_type=shot_type,
                camera_movement=camera_movement,
                subject_category=subject_category,
                location=location,
                color_tone=color_tone,
                semantic_theme=semantic_theme,
            )
        )

    def record_shot(
        self,
        shot_type: ShotType = ShotType.MEDIUM,
        subject_category: str = "general",
        camera_motion: str = "static",
        **kwargs,
    ):
        """Convenience alias for recording historical visual."""
        self.record_placed_shot(
            shot_id=kwargs.get("shot_id", "shot"),
            shot_type=shot_type,
            subject_category=subject_category,
            camera_movement=camera_motion,
            location=kwargs.get("location", "indoor"),
            color_tone=kwargs.get("color_tone", "warm"),
            semantic_theme=kwargs.get("semantic_theme", "general"),
        )

    def calculate_variety_penalty(
        self,
        candidate_shot_type: ShotType,
        candidate_subject: str,
        candidate_motion: str = "static",
    ) -> float:
        """Calculate repetition penalty (0.0 = completely fresh, 1.0 = highly repetitive)."""
        score = self.evaluate_variety(candidate_shot_type, candidate_subject, candidate_motion)
        return round(max(0.0, 1.0 - score), 2)

    def get_preferred_next_shot_types(self) -> List[ShotType]:
        """Get recommended next shot types to maximize viewer engagement."""
        if not self.history:
            return [ShotType.DETAIL, ShotType.WIDE, ShotType.SCREEN]
        last_type = self.history[-1].shot_type
        return self.CONTRAST_ROTATION.get(last_type, [ShotType.MEDIUM, ShotType.WIDE])
