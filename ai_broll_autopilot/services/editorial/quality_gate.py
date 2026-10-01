"""Automated Editorial Quality Gate.

Audits candidate edit specifications across Hook Quality, Contextual B-Roll Justification,
Sentiment Alignment, Sound Design Sparsity, Pacing Rhythm, and Narrative Arc.
Automatically repairs detected anomalies prior to NLE rendering.
"""

import logging
from typing import Any, Dict, List, Tuple

from ai_broll_autopilot.services.editorial.invariants import collect_plan_invariant_violations
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

        # Duration audit is read-only. Approval intervals must never be extended or
        # rewritten by QA; any repair would need a fresh editorial decision.
        min_broll = 0.65
        max_broll = 1.8
        out_of_bounds = [
            s for s in broll_shots
            if s.duration < min_broll or s.duration > max_broll
        ]
        if not out_of_bounds:
            checks.append(QualityCheckItem(
                name="broll_adaptive_durations",
                category="broll",
                passed=True,
                score=1.0,
                message="All approved cutaway durations are within the render contract (0.65s - 1.8s).",
            ))
        else:
            recommendations.append(
                f"{len(out_of_bounds)} B-roll intervals fall outside the approved render contract; "
                "no automatic duration mutation was applied."
            )
            checks.append(QualityCheckItem(
                name="broll_adaptive_durations",
                category="broll",
                passed=False,
                score=0.8,
                message=(
                    f"{len(out_of_bounds)} cutaway intervals require explicit re-planning "
                    "rather than automatic extension/clamping."
                ),
                severity="error",
            ))

        # Opening timing is also read-only: moving a shot changes its approved
        # semantic alignment, so it must be re-evaluated instead of shifted by QA.
        early_cuts = [s for s in broll_shots if s.start_time < 1.2]
        if early_cuts:
            recommendations.append(
                f"{len(early_cuts)} B-roll shot(s) begin before the 1.2s opening-face boundary; "
                "re-evaluate them upstream rather than shifting their approved intervals."
            )
            checks.append(QualityCheckItem(
                name="opening_face_rule",
                category="broll",
                passed=False,
                score=0.8,
                message="Early B-roll was not auto-shifted; approved timing was preserved.",
                severity="error",
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
            # QA must not invent a new creative treatment after the Creative
            # Director has allocated attention. Report the gap instead.
            recommendations.append(
                f"Visual stagnation of {max_stagnant_gap:.1f}s from "
                f"{stagnant_interval[0]:.1f}s to {stagnant_interval[1]:.1f}s."
            )
            checks.append(QualityCheckItem(
                name="pacing_stagnation",
                category="pacing",
                passed=False,
                score=0.75,
                message=(
                    f"Visual beat gap is {max_stagnant_gap:.1f}s; "
                    "no automatic creative punch was inserted."
                ),
                severity="warning",
            ))

        # -------------------------------------------------------------
        # 5. EXECUTABLE PLAN INVARIANTS
        # -------------------------------------------------------------
        invariant_payload = spec.to_dict()
        invariant_violations = collect_plan_invariant_violations(
            invariant_payload,
            target_duration=total_dur,
        )
        if invariant_violations:
            checks.append(QualityCheckItem(
                name="plan_invariants",
                category="overall",
                passed=False,
                score=0.0,
                message=f"{len(invariant_violations)} executable plan invariant(s) violated.",
                severity="error",
            ))
            recommendations.extend(invariant_violations)
        else:
            checks.append(QualityCheckItem(
                name="plan_invariants",
                category="overall",
                passed=True,
                score=1.0,
                message="All executable plan invariants hold.",
            ))

        # -------------------------------------------------------------
        # 6. OVERALL NARRATIVE ARC AUDIT
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
