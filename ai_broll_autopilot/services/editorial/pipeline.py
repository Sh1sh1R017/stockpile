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
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine

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
        # STEP 3: CONTEXTUAL, SENTIMENT-AWARE B-ROLL SELECTION
        # -------------------------------------------------------------
        broll_decisions: List[ContextualBrollDecision] = []

        for idx, moment in enumerate(moments):
            decision = self.broll_intelligence.evaluate_and_plan_shot(
                moment=moment,
                available_assets=assets,
                variety_engine=self.variety_engine,
                is_first_moment=(idx == 0),
            )
            if decision:
                broll_decisions.append(decision)

        # -------------------------------------------------------------
        # STEP 4: KINETIC TEXT OVERLAYS & HOOK CARD
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
                behind_subject=True,
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
        # STEP 5: CAMERA PUNCH-IN ZOOMS
        # -------------------------------------------------------------
        camera_moves: List[EditorialCameraSpec] = []
        for m in moments:
            # Emphatic statement or climactic reveal warrants a punch-in zoom
            if m.speaker_emphasis >= 0.70 or m.narrative_role in [NarrativeRole.CLAIM, NarrativeRole.REVEAL]:
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
        # STEP 6: SOUND DESIGN & SYNCHRONIZATION
        # -------------------------------------------------------------
        sfx_cues = self.sound_designer.design_soundscape(
            moments=moments,
            captions=captions,
            camera_moves=camera_moves,
            broll_shots=broll_decisions,
            video_duration=target_duration,
        )

        # -------------------------------------------------------------
        # STEP 7: PACING & COGNITIVE PROCESSING LOAD BALANCING
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
        # STEP 8: ASSEMBLE MASTER EDIT SPECIFICATION
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
            metadata={
                "generator": "Stockpile Editorial Intelligence Pipeline",
                "version": "2.0.0",
                "source_media": source_media,
                "hook_candidates_count": len(hook_candidates),
                "broll_count": len(broll_decisions),
                "sfx_count": len(sfx_cues),
                "niche": getattr(niche_profile, "name", "generic"),
                "style": getattr(style_profile, "name", "clean_podcast"),
            },
        )

        # -------------------------------------------------------------
        # STEP 9: QUALITY GATE AUDIT & AUTO-REPAIR
        # -------------------------------------------------------------
        repaired_spec, quality_report = self.quality_gate.audit_and_repair(spec)

        logger.info(
            f"Editorial Pipeline generated spec [{spec_id}] "
            f"({len(repaired_spec.broll_shots)} B-roll, {len(repaired_spec.sfx_cues)} SFX, "
            f"{len(repaired_spec.camera_moves)} Zooms). Quality Score: {quality_report.overall_score:.2f}."
        )
        return repaired_spec, quality_report


editorial_pipeline = EditorialIntelligencePipeline()
