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
            cam_start = float(cam.timestamp)
            cam_end = cam_start + max(0.0, float(cam.duration))
            collides_with_broll = any(
                cam_start < float(b.end_time) and cam_end > float(b.start_time)
                for b in balanced_broll
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
                    old_end = previous.end_time
                    previous.end_time = proposed_end
                    previous.duration = round(previous.end_time - previous.start_time, 2)
                    previous.adjustment_log.append({
                        "stage": "pacing",
                        "reason": "trimmed_overlap",
                        "previous_end_time": round(float(old_end), 3),
                        "new_end_time": round(float(proposed_end), 3),
                    })
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

        kept_ids = {b.shot_id for b in balanced_broll}
        pruned_sfx = [
            cue for cue in sfx_cues
            if not getattr(cue, "target_id", None)
            or getattr(cue, "target_id", None) in kept_ids
        ]

        # Remove cues that now fall inside a dropped B-roll interval.
        kept_intervals = [(b.start_time, b.end_time) for b in balanced_broll]
        original_intervals = [(b.start_time, b.end_time, b.shot_id) for b in broll_shots]
        dropped_intervals = [
            (st, et) for st, et, sid in original_intervals if sid not in kept_ids
        ]
        pruned_sfx = [
            cue for cue in pruned_sfx
            if not any(st <= float(getattr(cue, "timestamp", getattr(cue, "start_time", -1))) < et
                       for st, et in dropped_intervals)
        ]

        # Stagger captions slightly after a B-roll entrance so the visual can register first.
        for b in balanced_broll:
            for cap in captions:
                if abs(b.start_time - cap.start_time) < 0.15 and b.start_time > 2.0:
                    cap.start_time = round(b.start_time + 0.20, 2)

        return balanced_broll, pruned_camera, pruned_sfx
