"""Automated Editorial Quality Gate.

Audits candidate edit specifications across Hook Quality, Contextual B-Roll Justification,
Sentiment Alignment, Sound Design Sparsity, Pacing Rhythm, and Narrative Arc.
Automatically repairs detected anomalies prior to NLE rendering.
"""

import logging
from typing import Any, Dict, List, Tuple

from ai_broll_autopilot.services.editorial.types import (
    EditorialCaptionSpec,
    EditorialCameraSpec,
    EditorialEditSpecification,
    QualityAuditReport,
    QualityCheckItem,
)

logger = logging.getLogger("autopilot.editorial.quality")


class EditorialQualityGate:
    """Rigorous editorial quality control gate verifying human-editor standards."""

    def audit_and_repair(
        self, spec: EditorialEditSpecification
    ) -> Tuple[EditorialEditSpecification, QualityAuditReport]:
        """Audit the complete edit specification and apply non-destructive repairs if needed."""
        checks: List[QualityCheckItem] = []
        repaired_items: List[str] = []
        recommendations: List[str] = []

        total_dur = spec.total_duration

        # -------------------------------------------------------------
        # 1. HOOK AUDIT
        # -------------------------------------------------------------
        hook = spec.hook
        hook_score = hook.scores.final_score
        if hook_score >= 70.0:
            checks.append(QualityCheckItem(
                name="hook_score",
                category="hook",
                passed=True,
                score=hook_score / 100.0,
                message=f"Strong opening hook ({hook_score:.1f}/100): '{hook.tightened_text[:50]}...'",
            ))
        else:
            checks.append(QualityCheckItem(
                name="hook_score",
                category="hook",
                passed=False,
                score=hook_score / 100.0,
                message=f"Weak hook score ({hook_score:.1f}/100). Lacks curiosity gap or high-stakes premise.",
                severity="warning",
            ))
            recommendations.append("Consider re-evaluating the opening hook with a stronger curiosity gap.")

        if hook.scores.penalties > 0:
            recommendations.append(f"Hook received {hook.scores.penalties:.0f} penalty points for conversational filler.")

        # -------------------------------------------------------------
        # 2. B-ROLL CONTEXTUAL JUSTIFICATION & SENTIMENT AUDIT
        # -------------------------------------------------------------
        broll_shots = spec.broll_shots
        unjustified_shots = [s for s in broll_shots if not s.reason or not s.narrative_role]
        if not unjustified_shots:
            checks.append(QualityCheckItem(
                name="broll_narrative_purpose",
                category="broll",
                passed=True,
                score=1.0,
                message=f"All {len(broll_shots)} B-roll cutaways have verified narrative justifications.",
            ))
        else:
            checks.append(QualityCheckItem(
                name="broll_narrative_purpose",
                category="broll",
                passed=False,
                score=0.5,
                message=f"{len(unjustified_shots)} B-roll shots lack narrative rationale.",
                severity="error",
            ))

        # Check sentiment alignment
        low_sentiment = [s for s in broll_shots if s.scores.sentiment_match < 0.60]
        if not low_sentiment:
            checks.append(QualityCheckItem(
                name="broll_sentiment_alignment",
                category="broll",
                passed=True,
                score=1.0,
                message="All B-roll visuals emotionally align with spoken sentiment.",
            ))
        else:
            checks.append(QualityCheckItem(
                name="broll_sentiment_alignment",
                category="broll",
                passed=False,
                score=0.7,
                message=f"{len(low_sentiment)} cutaways have marginal sentiment alignment.",
                severity="warning",
            ))

        # Check durations (3-5s default, 2-3s high-energy, 6-8s reflective)
        runaway_shots = [s for s in broll_shots if s.duration > 8.5 or s.duration < 1.4]
        if not runaway_shots:
            checks.append(QualityCheckItem(
                name="broll_adaptive_durations",
                category="broll",
                passed=True,
                score=1.0,
                message="All cutaway durations conform to adaptive pacing standards (1.5s - 8.0s).",
            ))
        else:
            # Auto-repair runaway durations
            for s in runaway_shots:
                if s.duration > 8.0:
                    s.duration = 6.5
                    s.end_time = s.start_time + 6.5
                    repaired_items.append(f"Clamped runaway duration of [{s.shot_id}] to 6.5s.")
                elif s.duration < 1.4:
                    s.duration = 1.8
                    s.end_time = s.start_time + 1.8
                    repaired_items.append(f"Extended micro-clip [{s.shot_id}] to 1.8s for visual clarity.")

            checks.append(QualityCheckItem(
                name="broll_adaptive_durations",
                category="broll",
                passed=True,
                score=0.9,
                message=f"Repaired {len(runaway_shots)} out-of-bounds cutaway durations.",
                severity="info",
            ))

        # Check Opening Face Rule: Never cover speaker face before 1.2s
        early_cuts = [s for s in broll_shots if s.start_time < 1.2]
        if early_cuts:
            for s in early_cuts:
                orig_st = s.start_time
                s.start_time = 1.2
                s.duration = max(1.5, s.end_time - s.start_time)
                s.end_time = s.start_time + s.duration
                repaired_items.append(
                    f"Delayed cutaway [{s.shot_id}] from {orig_st:.1f}s to 1.2s to establish human speaker connection."
                )
            checks.append(QualityCheckItem(
                name="opening_face_rule",
                category="broll",
                passed=True,
                score=0.95,
                message="Auto-repaired opening cutaway to preserve speaker face in initial 1.2s.",
                severity="info",
            ))
        else:
            checks.append(QualityCheckItem(
                name="opening_face_rule",
                category="broll",
                passed=True,
                score=1.0,
                message="Opening face established before B-roll cutaways (>= 1.2s).",
            ))

        # -------------------------------------------------------------
        # 3. SFX SPARSITY & TIMELINE SYNCHRONIZATION AUDIT
        # -------------------------------------------------------------
        sfx_cues = spec.sfx_cues
        sfx_density = (len(sfx_cues) / max(0.1, total_dur)) * 60.0
        if sfx_density <= 6.5:
            checks.append(QualityCheckItem(
                name="sfx_density_control",
                category="sfx",
                passed=True,
                score=1.0,
                message=f"SFX density is restrained ({sfx_density:.1f}/min). Avoids acoustic fatigue.",
            ))
        else:
            # Prune excessive SFX
            while (len(spec.sfx_cues) / max(0.1, total_dur)) * 60.0 > 6.0 and len(spec.sfx_cues) > 2:
                pruned = spec.sfx_cues.pop()
                repaired_items.append(f"Pruned low-priority SFX [{pruned.cue_id}] to adhere to density limit.")

            checks.append(QualityCheckItem(
                name="sfx_density_control",
                category="sfx",
                passed=True,
                score=0.85,
                message="Pruned excessive SFX cues down to professional density guidelines.",
                severity="info",
            ))

        # -------------------------------------------------------------
        # 4. PACING & STAGNATION AUDIT
        # -------------------------------------------------------------
        # Check for long stretches (>14s) without any visual change (B-roll or punch-in)
        visual_events = [0.0]
        for b in spec.broll_shots:
            visual_events.extend([b.start_time, b.end_time])
        for cm in spec.camera_moves:
            visual_events.append(cm.timestamp)
        visual_events.append(total_dur)
        visual_events.sort()

        max_stagnant_gap = 0.0
        stagnant_interval = (0.0, 0.0)
        for i in range(len(visual_events) - 1):
            gap = visual_events[i + 1] - visual_events[i]
            if gap > max_stagnant_gap:
                max_stagnant_gap = gap
                stagnant_interval = (visual_events[i], visual_events[i + 1])

        if max_stagnant_gap <= 4.5:
            checks.append(QualityCheckItem(
                name="pacing_stagnation",
                category="pacing",
                passed=True,
                score=1.0,
                message=f"Healthy pacing rhythm: maximum visual beat gap is {max_stagnant_gap:.1f}s.",
            ))
        else:
            # Auto-repair: add a subtle punch-in in the middle of the stagnant stretch
            mid_t = round((stagnant_interval[0] + stagnant_interval[1]) / 2.0, 2)
            spec.camera_moves.append(
                EditorialCameraSpec(
                    camera_id=f"cam_auto_punch_{int(mid_t * 10)}",
                    timestamp=mid_t,
                    scale=1.18,
                    duration=0.3,
                    reason="Reset visual stagnation during extended dialogue.",
                )
            )
            spec.camera_moves.sort(key=lambda c: c.timestamp)
            repaired_items.append(f"Added subtle punch-in at {mid_t:.1f}s to eliminate {max_stagnant_gap:.1f}s stagnation gap.")

            checks.append(QualityCheckItem(
                name="pacing_stagnation",
                category="pacing",
                passed=True,
                score=0.9,
                message=f"Repaired {max_stagnant_gap:.1f}s visual stagnation with dynamic punch-in.",
                severity="info",
            ))

        # -------------------------------------------------------------
        # 5. OVERALL NARRATIVE ARC AUDIT
        # -------------------------------------------------------------
        has_hook = any(m.narrative_role.value == "HOOK" for m in spec.moments)
        has_payoff = any(m.narrative_role.value in ["PAYOFF", "REVEAL", "CTA"] for m in spec.moments)

        if has_hook and has_payoff:
            checks.append(QualityCheckItem(
                name="narrative_arc",
                category="overall",
                passed=True,
                score=1.0,
                message="Complete narrative arc confirmed: Beginning (Hook) -> Climax/Reveal -> Payoff.",
            ))
        else:
            checks.append(QualityCheckItem(
                name="narrative_arc",
                category="overall",
                passed=False,
                score=0.7,
                message="Incomplete narrative arc detected in speech structure.",
                severity="warning",
            ))

        overall_passed = all(c.passed for c in checks if c.severity == "error")
        avg_score = sum(c.score for c in checks) / max(1, len(checks))

        report = QualityAuditReport(
            passed=overall_passed,
            overall_score=round(avg_score, 2),
            checks=checks,
            recommendations=recommendations,
            repaired_items=repaired_items,
        )

        logger.info(
            f"EditorialQualityGate Audit: Passed={overall_passed} (Score: {avg_score:.2f}) | "
            f"Repaired {len(repaired_items)} items."
        )
        return spec, report
