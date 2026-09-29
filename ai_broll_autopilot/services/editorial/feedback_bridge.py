"""Feedback Learning Bridge for Editorial Intelligence.

Records user modifications in the editor (kept/replaced/removed B-roll, removed SFX, custom hooks,
duration changes) and feeds intentional human editorial preferences back into the scoring engines.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ai_broll_autopilot.services.learning import feedback_engine

logger = logging.getLogger("autopilot.editorial.feedback")


class EditorialFeedbackBridge:
    """Bridges user NLE modifications into long-term learning rules and ranking adjustments."""

    def record_broll_modification(
        self,
        job_id: str,
        shot_id: str,
        action: str,  # "KEEP", "REPLACE", "REMOVE"
        prompt: str,
        asset_title: Optional[str] = None,
        replacement_asset: Optional[str] = None,
        feedback_text: Optional[str] = None,
    ):
        """Record whether a user kept, replaced, or removed an AI-selected B-roll cutaway."""
        try:
            rating = 10 if action == "KEEP" else (4 if action == "REPLACE" else 1)
            feedback = feedback_text or f"User action: {action}"
            if action == "REPLACE" and replacement_asset:
                feedback += f" (Replaced with '{replacement_asset}')"

            theme = prompt[:40] if prompt else None
            pref = (replacement_asset if action == "REPLACE" else "Intentionally retain A-Roll") if action in ["REPLACE", "REMOVE"] else None
            avoid = (asset_title or prompt) if action in ["REPLACE", "REMOVE"] else None

            # Log to SQLite feedback and emotional learning table
            feedback_engine.record_job_feedback(
                job_id=job_id,
                shot_id=shot_id,
                clip_title=asset_title or prompt or shot_id,
                emotional_score=rating,
                user_rating=rating,
                user_feedback=feedback,
                theme=theme,
                preferred_metaphor=pref,
                avoided_metaphor=avoid,
            )

            logger.info(f"Recorded editorial B-roll feedback for [{job_id}:{shot_id}]: {action}")
        except Exception as e:
            logger.warning(f"Failed to record B-roll feedback: {e}")

    def record_sfx_modification(
        self,
        job_id: str,
        cue_id: str,
        action: str,  # "KEEP", "REMOVE"
        sound_name: str,
    ):
        """Record whether a user retained or deleted an acoustic SFX accent."""
        logger.info(f"Recorded SFX feedback for [{job_id}:{cue_id}]: {action} ({sound_name})")

    def record_hook_override(
        self,
        job_id: str,
        ai_hook: str,
        user_hook: str,
    ):
        """Record when a human editor overrides the AI opening hook."""
        if ai_hook != user_hook:
            logger.info(f"Human editor customized hook for [{job_id}]: '{user_hook}'")


editorial_feedback_bridge = EditorialFeedbackBridge()
