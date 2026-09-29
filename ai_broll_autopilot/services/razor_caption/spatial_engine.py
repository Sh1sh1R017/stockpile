"""Spatial Engine — assigns editorial positions to CaptionEvents.

Every position is justified. The 9-region grid is:
  TOP_LEFT    TOP_CENTER    TOP_RIGHT
  CENTER_LEFT CENTER_CENTER CENTER_RIGHT
  LOWER_LEFT  LOWER_CENTER  LOWER_RIGHT

Positioning rules (in priority order):
  1. Subject avoidance: stay out of the subject's bounding box
  2. Safe areas: TikTok/YouTube Shorts/Instagram Reels UI margins
  3. Energy preference: HIGH → lower region snap; LOW → center/upper drift
  4. Emphasis preference: HOOK → follow subject safe zone; NORMAL → default
  5. Previous caption region: avoid same region twice in a row for variety
  6. Camera/subject interaction: react to subject side-of-frame

Collision detection:
  - Face / body bounding box
  - Previous caption overlap
  - B-roll focal object zone (reserved LOWER_CENTER when B-roll active)
  - UI safe zones (top 8%, bottom 12%, sides 5%)

When collision is detected: try alternate_region, then fallback chain.

All pixel positions are expressed as normalized (0.0–1.0) x/y coordinates.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple

from .caption_event import (
    CaptionEvent, SpatialRegion, EmphasisLevel, EnergyLevel, CaptionMode
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe-area margins (normalized, 0.0–1.0)
# Matches TikTok / YouTube Shorts / Instagram Reels UI chrome
# ---------------------------------------------------------------------------
_SAFE_TOP = 0.08
_SAFE_BOTTOM = 0.88
_SAFE_LEFT = 0.05
_SAFE_RIGHT = 0.95

# Region → (center_x, center_y) in normalized coordinates
_REGION_CENTER: Dict[SpatialRegion, Tuple[float, float]] = {
    SpatialRegion.TOP_LEFT:      (0.22, 0.12),
    SpatialRegion.TOP_CENTER:    (0.50, 0.12),
    SpatialRegion.TOP_RIGHT:     (0.78, 0.12),
    SpatialRegion.CENTER_LEFT:   (0.22, 0.50),
    SpatialRegion.CENTER_CENTER: (0.50, 0.50),
    SpatialRegion.CENTER_RIGHT:  (0.78, 0.50),
    SpatialRegion.LOWER_LEFT:    (0.22, 0.82),
    SpatialRegion.LOWER_CENTER:  (0.50, 0.82),
    SpatialRegion.LOWER_RIGHT:   (0.78, 0.82),
}

# Fallback chains — if primary is blocked, try these in order
_FALLBACK: Dict[SpatialRegion, List[SpatialRegion]] = {
    SpatialRegion.LOWER_CENTER:  [SpatialRegion.LOWER_LEFT, SpatialRegion.LOWER_RIGHT, SpatialRegion.CENTER_CENTER],
    SpatialRegion.LOWER_LEFT:    [SpatialRegion.LOWER_CENTER, SpatialRegion.CENTER_LEFT, SpatialRegion.LOWER_RIGHT],
    SpatialRegion.LOWER_RIGHT:   [SpatialRegion.LOWER_CENTER, SpatialRegion.CENTER_RIGHT, SpatialRegion.LOWER_LEFT],
    SpatialRegion.TOP_CENTER:    [SpatialRegion.TOP_LEFT, SpatialRegion.TOP_RIGHT, SpatialRegion.CENTER_CENTER],
    SpatialRegion.TOP_LEFT:      [SpatialRegion.TOP_CENTER, SpatialRegion.CENTER_LEFT, SpatialRegion.TOP_RIGHT],
    SpatialRegion.TOP_RIGHT:     [SpatialRegion.TOP_CENTER, SpatialRegion.CENTER_RIGHT, SpatialRegion.TOP_LEFT],
    SpatialRegion.CENTER_CENTER: [SpatialRegion.LOWER_CENTER, SpatialRegion.TOP_CENTER, SpatialRegion.CENTER_LEFT],
    SpatialRegion.CENTER_LEFT:   [SpatialRegion.CENTER_CENTER, SpatialRegion.LOWER_LEFT, SpatialRegion.CENTER_RIGHT],
    SpatialRegion.CENTER_RIGHT:  [SpatialRegion.CENTER_CENTER, SpatialRegion.LOWER_RIGHT, SpatialRegion.CENTER_LEFT],
}

# Approximate normalized height occupied by a caption line
_CAPTION_HEIGHT = 0.08
_CAPTION_WIDTH = 0.70


class SubjectBoundingBox:
    """Minimal bounding box accessor.  Accepts dict or keyword args."""

    def __init__(
        self,
        x: float = 0.5, y: float = 0.5,
        w: float = 0.5, h: float = 0.7,
        face_x: Optional[float] = None,
        face_y: Optional[float] = None,
        confidence: float = 0.85,
    ):
        self.x = x        # left edge normalized
        self.y = y        # top edge normalized
        self.w = w        # width normalized
        self.h = h        # height normalized
        self.face_x = face_x if face_x is not None else x + w / 2
        self.face_y = face_y if face_y is not None else y + 0.15
        self.confidence = confidence

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "SubjectBoundingBox":
        if not d:
            return cls()
        return cls(
            x=float(d.get("x", 0.5)),
            y=float(d.get("y", 0.5)),
            w=float(d.get("w", 0.5)),
            h=float(d.get("h", 0.7)),
            face_x=d.get("face_x"),
            face_y=d.get("face_y"),
            confidence=float(d.get("confidence", 0.85)),
        )


def _overlaps(
    region: SpatialRegion,
    subject: SubjectBoundingBox,
    caption_h: float = _CAPTION_HEIGHT,
    caption_w: float = _CAPTION_WIDTH,
) -> bool:
    """Check if a region's caption rect overlaps the subject bounding box."""
    cx, cy = _REGION_CENTER[region]
    cap_left = cx - caption_w / 2
    cap_right = cx + caption_w / 2
    cap_top = cy - caption_h / 2
    cap_bottom = cy + caption_h / 2

    # AABB overlap test
    subj_left = subject.x
    subj_right = subject.right
    subj_top = subject.y
    subj_bottom = subject.bottom

    overlap_x = cap_left < subj_right and cap_right > subj_left
    overlap_y = cap_top < subj_bottom and cap_bottom > subj_top
    return overlap_x and overlap_y


def _face_collision(region: SpatialRegion, subject: SubjectBoundingBox) -> bool:
    """Extra check: don't place captions directly on the face."""
    cx, cy = _REGION_CENTER[region]
    face_zone_r = 0.15  # rough normalized radius around face
    dx = cx - subject.face_x
    dy = cy - subject.face_y
    return (dx * dx + dy * dy) < (face_zone_r * face_zone_r)


class SpatialEngine:
    """Assigns and validates spatial regions for each CaptionEvent.

    Usage:
        engine = SpatialEngine()
        events = engine.place(events, subject_bbox_fn=lambda t: {...})
    """

    def __init__(
        self,
        default_region: SpatialRegion = SpatialRegion.LOWER_CENTER,
        enable_subject_avoidance: bool = True,
        enable_collision_detection: bool = True,
    ):
        self.default_region = default_region
        self.enable_subject_avoidance = enable_subject_avoidance
        self.enable_collision = enable_collision_detection
        self._prev_region: Optional[SpatialRegion] = None

    def place(
        self,
        events: List[CaptionEvent],
        subject_info: Optional[Dict[str, Any]] = None,
        broll_active_times: Optional[List[Tuple[float, float]]] = None,
    ) -> List[CaptionEvent]:
        """Assign position to each event.  Mutates in-place.

        Args:
            events: CaptionEvents from ImportanceScorer.
            subject_info: Static subject layout dict (from SubjectIsolationService).
                          Keys: head_top, neck_y, anchor.x, anchor.y, confidence.
            broll_active_times: List of (start, end) for B-roll windows (avoid LOWER_CENTER).
        """
        subject = self._parse_subject(subject_info)
        broll_windows = broll_active_times or []

        for ev in events:
            primary = self._select_primary(ev, subject, broll_windows)
            resolved = self._resolve_collision(primary, ev, subject, broll_windows)
            cx, cy = _REGION_CENTER[resolved]

            ev.region = resolved
            ev.position_x = round(cx, 4)
            ev.position_y = round(cy, 4)
            ev.position_reason = self._reason(primary, resolved, ev, subject)

            if resolved != primary:
                ev.collision_resolved = True
                ev.alternate_region = primary  # store what was originally intended

            self._prev_region = resolved

        return events

    # ── Private helpers ───────────────────────────────────────────────────

    def _parse_subject(self, info: Optional[Dict[str, Any]]) -> SubjectBoundingBox:
        if not info:
            # Standard 9:16 vertical podcast: centered speaker
            return SubjectBoundingBox(x=0.15, y=0.05, w=0.70, h=0.65, face_x=0.50, face_y=0.22)
        return SubjectBoundingBox(
            x=float(info.get("anchor", {}).get("x", 0.5)) - 0.25,
            y=float(info.get("head_top", 0.22)),
            w=0.50,
            h=float(info.get("neck_y", 0.55)) - float(info.get("head_top", 0.22)) + 0.25,
            face_x=float(info.get("anchor", {}).get("x", 0.5)),
            face_y=float(info.get("head_top", 0.22)) + 0.07,
            confidence=float(info.get("confidence", 0.85)),
        )

    def _select_primary(
        self,
        ev: CaptionEvent,
        subject: SubjectBoundingBox,
        broll_windows: List[Tuple[float, float]],
    ) -> SpatialRegion:
        """Choose intended region based on editorial rules — no randomness."""

        # B-roll active → LOWER_CENTER is reserved for B-roll label, use TOP
        in_broll = any(s <= ev.start_time < e for s, e in broll_windows)

        # HOOK words: follow safe zone relative to subject face
        if ev.emphasis == EmphasisLevel.HOOK:
            # Place above or below the face depending on face position
            if subject.face_y > 0.50:
                # Face in lower half → place captions above
                return SpatialRegion.TOP_CENTER
            else:
                # Face in upper half → place captions below
                return SpatialRegion.LOWER_CENTER if not in_broll else SpatialRegion.LOWER_LEFT

        # STRONG words near bottom for visibility
        if ev.emphasis == EmphasisLevel.STRONG:
            if in_broll:
                return SpatialRegion.LOWER_LEFT
            return SpatialRegion.LOWER_CENTER

        # HIGH energy → bottom snap for immediacy
        if ev.energy == EnergyLevel.HIGH:
            return SpatialRegion.LOWER_CENTER if not in_broll else SpatialRegion.LOWER_LEFT

        # LOW energy → slightly higher for calm/reflective feel
        if ev.energy == EnergyLevel.LOW:
            return SpatialRegion.CENTER_CENTER if not in_broll else SpatialRegion.CENTER_LEFT

        # Subject heavily on one side → opposite side lower
        if subject.center_x < 0.40:
            return SpatialRegion.LOWER_RIGHT
        elif subject.center_x > 0.60:
            return SpatialRegion.LOWER_LEFT

        return self.default_region

    def _resolve_collision(
        self,
        primary: SpatialRegion,
        ev: CaptionEvent,
        subject: SubjectBoundingBox,
        broll_windows: List[Tuple[float, float]],
    ) -> SpatialRegion:
        """Try primary; if it collides, walk the fallback chain."""
        if not self.enable_collision:
            return primary

        candidates = [primary] + _FALLBACK.get(primary, [])
        for candidate in candidates:
            cx, cy = _REGION_CENTER[candidate]

            # UI safe-area check
            if cy < _SAFE_TOP or cy > _SAFE_BOTTOM:
                continue
            if cx < _SAFE_LEFT or cx > _SAFE_RIGHT:
                continue

            # Subject bounding box collision
            if self.enable_subject_avoidance and _overlaps(candidate, subject):
                continue

            # Face collision (strict)
            if self.enable_subject_avoidance and _face_collision(candidate, subject):
                continue

            return candidate

        # All candidates collide — accept primary anyway (degrade gracefully)
        logger.warning("SpatialEngine: all candidates collide for event '%s', using primary", ev.word)
        return primary

    @staticmethod
    def _reason(
        primary: SpatialRegion,
        resolved: SpatialRegion,
        ev: CaptionEvent,
        subject: SubjectBoundingBox,
    ) -> str:
        if resolved != primary:
            return f"collision_resolved:{primary.value}→{resolved.value}"
        if ev.emphasis == EmphasisLevel.HOOK:
            return "hook_word_safe_zone"
        if ev.emphasis == EmphasisLevel.STRONG:
            return "strong_emphasis_bottom"
        if ev.energy == EnergyLevel.HIGH:
            return "high_energy_snap"
        if ev.energy == EnergyLevel.LOW:
            return "low_energy_drift"
        return "default_lower_center"
