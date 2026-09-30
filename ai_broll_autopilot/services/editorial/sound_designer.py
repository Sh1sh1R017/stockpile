"""Semantically Relatable and Density-Controlled Sound Design Engine.

Classifies editorial events, matches emotionally compatible sound effects, enforces strict
density limits per minute to prevent SFX spam, and temporally synchronizes SFX cues with
visual timeline events (captions, punch-in zooms, B-roll entrances, and major reveals).
"""

import logging
from typing import Any, Dict, List, Optional

from ai_broll_autopilot.services.editorial.types import (
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    EditorialMoment,
    NarrativeRole,
    SentimentCategory,
    SfxCueDecision,
    SfxEventType,
)

logger = logging.getLogger("autopilot.editorial.sound")


class SoundDesigner:
    """Intelligent Sound Design and Timeline Audio Synchronization Engine."""

    # Built-in sound asset library categorized by editorial event type
    SFX_CATALOG = {
        SfxEventType.REVEAL: {
            "name": "Subtle Cinematic Impact",
            "file": "impact_subtle_01.wav",
            "duration": 0.8,
            "default_vol": 0.55,
        },
        SfxEventType.SHOCK: {
            "name": "Dramatic Heavy Impact",
            "file": "impact_heavy_braam.wav",
            "duration": 1.2,
            "default_vol": 0.65,
        },
        SfxEventType.STATISTIC: {
            "name": "Clean Data Accent Ping",
            "file": "accent_statistic_ping.wav",
            "duration": 0.5,
            "default_vol": 0.40,
        },
        SfxEventType.SUCCESS: {
            "name": "Positive Uplift Chime",
            "file": "success_warm_chime.wav",
            "duration": 0.7,
            "default_vol": 0.45,
        },
        SfxEventType.FAILURE: {
            "name": "Subtle Sub Bass Drop",
            "file": "sub_drop_soft.wav",
            "duration": 0.9,
            "default_vol": 0.50,
        },
        SfxEventType.QUESTION: {
            "name": "Tension Atmosphere Riser",
            "file": "riser_tension_subtle.wav",
            "duration": 1.0,
            "default_vol": 0.35,
        },
        SfxEventType.TEXT_POPUP: {
            "name": "Crisp Interface Pop",
            "file": "pop_crisp_click.wav",
            "duration": 0.3,
            "default_vol": 0.38,
        },
        SfxEventType.FAST_TRANSITION: {
            "name": "Smooth Air Whoosh",
            "file": "whoosh_clean_air.wav",
            "duration": 0.4,
            "default_vol": 0.35,
        },
        SfxEventType.EMOTIONAL_MOMENT: {
            "name": "Cinematic Texture Swell",
            "file": "cinematic_pad_swell.wav",
            "duration": 1.5,
            "default_vol": 0.40,
        },
        SfxEventType.COMEDIC_MOMENT: {
            "name": "Light Comedic Plink",
            "file": "comedic_wood_plink.wav",
            "duration": 0.4,
            "default_vol": 0.45,
        },
    }

    # Density constraints
    MAX_SFX_PER_MINUTE = 6.0       # Max ~3 per 30-second short
    MIN_SPACING_SECONDS = 3.0      # At least 3 seconds between SFX hits

    def __init__(self, max_sfx_per_minute: float = 6.0, min_spacing_seconds: float = 3.0):
        self.max_sfx_per_minute = max_sfx_per_minute
        self.min_spacing_seconds = min_spacing_seconds

    def design_soundscape(
        self,
        moments: List[EditorialMoment],
        captions: List[EditorialCaptionSpec],
        camera_moves: List[EditorialCameraSpec],
        broll_shots: List[ContextualBrollDecision],
        video_duration: float = 60.0,
        **kwargs,
    ) -> List[SfxCueDecision]:
        """Generate a sparse, semantically motivated, and visually synchronized soundscape."""
        dur = kwargs.get("total_duration", video_duration)
        editorial_intents = kwargs.get("edit_intents") or []

        def intent_for(moment: EditorialMoment):
            for intent in editorial_intents:
                start = float(getattr(intent, "start_time", 0.0))
                end = float(getattr(intent, "end_time", start))
                if start <= moment.start_time < max(end, start + 0.01):
                    return intent
            return min(
                editorial_intents,
                key=lambda i: abs(float(getattr(i, "start_time", 0.0)) - moment.start_time),
                default=None,
            )

        def allows_sfx(moment: EditorialMoment) -> bool:
            intent = intent_for(moment)
            if intent is None:
                return True
            return (
                float(getattr(intent, "sfx_opportunity", 0.0) or 0.0) >= 0.52
                and str(getattr(intent, "treatment", "normal")) != "quiet"
            )

        candidate_cues: List[SfxCueDecision] = []
        max_allowed_sfx = max(2, int(round((dur / 60.0) * self.max_sfx_per_minute)))

        # -------------------------------------------------------------
        # 1. CANDIDATE: Opening Hook / Title Card Entrance
        # -------------------------------------------------------------
        if captions:
            first_caption = captions[0]
            if first_caption.start_time <= 2.0:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.TEXT_POPUP,
                        timestamp=first_caption.start_time,
                        reason="Hook title card popup accentuates opening thesis.",
                        synced_with="caption",
                        target_id=first_caption.caption_id,
                        priority=100,  # Highest priority
                    )
                )

        # -------------------------------------------------------------
        # 2. CANDIDATE: Significant Spoken Moments (Reveals, Stats, Failures)
        # -------------------------------------------------------------
        for m in moments:
            if not allows_sfx(m):
                continue
            if m.narrative_role == NarrativeRole.STATISTIC and m.entities:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.STATISTIC,
                        timestamp=round(m.start_time + 0.15, 2),
                        reason=f"Restrained statistical accent for key data: '{m.entities[0]}'.",
                        synced_with="statistic",
                        target_id=m.moment_id,
                        priority=90,
                    )
                )
            elif m.narrative_role == NarrativeRole.REVEAL:
                event_type = SfxEventType.SHOCK if m.emotional_intensity >= 0.8 else SfxEventType.REVEAL
                candidate_cues.append(
                    self._create_cue(
                        event_type=event_type,
                        timestamp=round(m.start_time, 2),
                        reason=f"Subtle impact emphasizes major narrative reveal in moment '{m.semantic_topic}'.",
                        synced_with="reveal",
                        target_id=m.moment_id,
                        priority=95,
                    )
                )
            elif m.sentiment == SentimentCategory.NEGATIVE and m.emotional_intensity >= 0.75:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.FAILURE,
                        timestamp=round(m.start_time, 2),
                        reason=f"Sub bass drop underscores severe failure/loss context.",
                        synced_with="reveal",
                        target_id=m.moment_id,
                        priority=80,
                    )
                )
            elif m.sentiment == SentimentCategory.FUNNY:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.COMEDIC_MOMENT,
                        timestamp=round(m.start_time, 2),
                        reason=f"Comedic accent synchronizes with punchline delivery.",
                        synced_with="reveal",
                        target_id=m.moment_id,
                        priority=75,
                    )
                )

        # -------------------------------------------------------------
        # 3. CANDIDATE: Emphatic Camera Punch-In Keyframes
        # -------------------------------------------------------------
        for cam in camera_moves:
            if cam.scale >= 1.20 and cam.timestamp > 2.0:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.TEXT_POPUP,
                        timestamp=cam.timestamp,
                        reason="Acoustic pop accentuates visual punch-in zoom keyframe.",
                        synced_with="punch_in",
                        target_id=cam.camera_id,
                        priority=70,
                    )
                )

        # -------------------------------------------------------------
        # 4. CANDIDATE: Selected High-Energy B-Roll Entrances
        # -------------------------------------------------------------
        # Only add transition whoosh to at most 1-2 major B-roll cuts, NOT every cut!
        for broll in broll_shots:
            if broll.scores.final_score >= 0.85 and broll.start_time > 2.5:
                candidate_cues.append(
                    self._create_cue(
                        event_type=SfxEventType.FAST_TRANSITION,
                        timestamp=broll.start_time,
                        reason=f"Subtle air whoosh leads into high-impact cutaway '{broll.search_query}'.",
                        synced_with="broll_entrance",
                        target_id=broll.shot_id,
                        priority=60,
                    )
                )

        # -------------------------------------------------------------
        # 5. DENSITY FILTERING & SPACING ENFORCEMENT (Eliminates SFX Spam)
        # -------------------------------------------------------------
        # Sort candidates by timestamp
        candidate_cues.sort(key=lambda c: c.timestamp)

        accepted_cues: List[SfxCueDecision] = []
        last_sfx_time = -999.0

        for cue in candidate_cues:
            if len(accepted_cues) >= max_allowed_sfx:
                break
            if cue.timestamp - last_sfx_time >= self.MIN_SPACING_SECONDS:
                accepted_cues.append(cue)
                last_sfx_time = cue.timestamp
            else:
                logger.debug(f"Rejected SFX cue [{cue.cue_id}] at {cue.timestamp:.2f}s due to spacing constraint.")

        logger.info(
            f"SoundDesigner planned {len(accepted_cues)} synchronized SFX cues for {video_duration:.1f}s video "
            f"(Density: {len(accepted_cues)/(video_duration/60.0):.1f}/min, Max: {self.max_sfx_per_minute}/min)."
        )
        return accepted_cues

    def _create_cue(
        self,
        event_type: SfxEventType,
        timestamp: float,
        reason: str,
        synced_with: str,
        target_id: Optional[str] = None,
        priority: int = 50,
    ) -> SfxCueDecision:
        """Construct a validated SfxCueDecision instance."""
        catalog_entry = self.SFX_CATALOG[event_type]
        cue_id = f"sfx_{event_type.value.lower()}_{int(timestamp * 100):05d}"

        return SfxCueDecision(
            cue_id=cue_id,
            event_type=event_type,
            timestamp=round(timestamp, 2),
            duration=catalog_entry["duration"],
            sound_name=catalog_entry["name"],
            sound_file=catalog_entry["file"],
            volume=catalog_entry["default_vol"],
            reason=reason,
            emotional_compatibility=0.92,
            synced_with=synced_with,  # type: ignore
            target_id=target_id,
        )

    # Convenience alias
    design_soundtrack = design_soundscape

