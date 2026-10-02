"""Editorial Retention and Pacing Model.

Constructs macro-level energy curves (Hook -> Setup -> Emphasis -> Explanation -> Climax -> Payoff -> CTA),
balances narrative rhythm and contrast, and controls viewer cognitive processing load to eliminate
sensory overload and visual clutter.
"""

import logging
from typing import Any, Dict, List, Tuple

from ai_broll_autopilot.services.editorial.types import (
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    EditorialMoment,
    NarrativeRole,
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
            # Midpoint point for smooth interpolation
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
        """Balance simultaneous visual events to prevent sensory overload and cognitive clutter."""
        pruned_camera: List[EditorialCameraSpec] = []
        pruned_sfx: List[SfxCueDecision] = list(sfx_cues)
        balanced_broll: List[ContextualBrollDecision] = list(broll_shots)

        # 1. Prevent camera punch-in on top of an active B-roll cutaway
        # (A punch-in is for the speaker's face; doing a digital zoom on stock B-roll looks chaotic)
        for cam in camera_moves:
            collides_with_broll = any(
                b.start_time <= cam.timestamp <= b.end_time for b in balanced_broll
            )
            if collides_with_broll:
                logger.debug(f"Descheduled camera punch-in at {cam.timestamp:.2f}s: overlaps with B-roll cutaway.")
            else:
                pruned_camera.append(cam)

        # 2. Prevent consecutive cutaways with 0 gap (butt cuts between different stock footage)
        # In vertical shorts, returning briefly to the speaker's face maintains personal connection
        for i in range(len(balanced_broll) - 1):
            curr_b = balanced_broll[i]
            next_b = balanced_broll[i + 1]
            gap = next_b.start_time - curr_b.end_time
            if 0.0 <= gap < 1.2:
                # Trim first clip slightly to allow speaker face to breathe
                curr_b.end_time = max(curr_b.start_time + 1.5, curr_b.end_time - 1.0)
                curr_b.duration = round(curr_b.end_time - curr_b.start_time, 2)
                logger.debug(f"Inserted A-roll breath gap between [{curr_b.shot_id}] and [{next_b.shot_id}].")

        # 3. Prevent simultaneous caption entrance, punch-in, and B-roll cut all firing on the exact same millisecond
        # unless it is an intentional hook or climax reveal
        for b in balanced_broll:
            for cap in captions:
                if abs(b.start_time - cap.start_time) < 0.15 and b.start_time > 2.0:
                    # Offset caption entrance slightly (150ms) to allow viewer to register visual first
                    cap.start_time = round(b.start_time + 0.20, 2)

        return balanced_broll, pruned_camera, pruned_sfx
