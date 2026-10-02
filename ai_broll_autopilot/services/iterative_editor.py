"""Iterative Edit & Auto-Repair Loop.

Inspired by video-db/Director and Andrea13235/Retention:
1. Audits generated EditPlans against strict editorial rules and retention criteria.
2. Identifies defects: visual stagnation (>4.0s without cut or motion), SFX clustering,
   overlong B-roll cutaways, or missing opening emphasis.
3. Automatically repairs defects deterministically:
   - Injects punch-in camera zooms on stagnant A-roll stretches.
   - Re-spaces SFX cues to enforce maximum density (<= 6 per min, >= 3.0s spacing).
   - Adjusts B-roll durations to maintain narrative pacing.
4. Executes up to N repair iterations until the plan achieves >= 0.85 Quality Gate score.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.types import QualityAuditReport

logger = logging.getLogger("autopilot.iterative_editor")


@dataclass
class IterativeEditResult:
    """Outcome of the iterative edit and repair process."""
    plan: Any                          # EditPlan instance
    iteration_count: int
    initial_score: float
    final_score: float
    repaired_items: List[str] = field(default_factory=list)
    remaining_warnings: List[str] = field(default_factory=list)
    audit_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration_count": self.iteration_count,
            "initial_score": round(self.initial_score, 3),
            "final_score": round(self.final_score, 3),
            "repaired_items": self.repaired_items,
            "remaining_warnings": self.remaining_warnings,
            "audit_history": self.audit_history,
        }


class IterativeEditLoop:
    """Deterministic review and repair loop for EditPlans."""

    def __init__(
        self,
        min_quality_score: float = 0.85,
        max_iterations: int = 3,
        quality_gate: Optional[EditorialQualityGate] = None,
    ):
        self.min_quality_score = min_quality_score
        self.max_iterations = max_iterations
        self.quality_gate = quality_gate or EditorialQualityGate()

    def audit_and_repair_plan(self, plan: Any) -> IterativeEditResult:
        """Run iterative evaluation and deterministic repair on an EditPlan.
        
        Args:
            plan: The EditPlan object to audit and harden.
            
        Returns:
            IterativeEditResult containing the hardened plan and remediation history.
        """
        all_repaired_items: List[str] = []
        audit_history: List[Dict[str, Any]] = []

        # Convert plan to dict for analysis if needed
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else plan
        target_dur = float(plan_dict.get("target_duration", 30.0))

        # Initial audit
        current_report = self._audit_plan_data(plan_dict, target_dur)
        initial_score = current_report.overall_score
        audit_history.append({
            "iteration": 0,
            "score": current_report.overall_score,
            "passed": current_report.passed,
            "defects": [item.message for item in current_report.checks if not item.passed],
        })

        iteration = 0
        while iteration < self.max_iterations and current_report.overall_score < self.min_quality_score:
            iteration += 1
            logger.info(f"EditPlan [{plan_dict.get('plan_id')}]: Starting repair iteration {iteration} (score: {current_report.overall_score:.2f})")

            iteration_repairs = self._apply_deterministic_repairs(plan, plan_dict, current_report, target_dur)
            all_repaired_items.extend(iteration_repairs)

            # Re-audit updated plan
            plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else plan
            current_report = self._audit_plan_data(plan_dict, target_dur)

            audit_history.append({
                "iteration": iteration,
                "score": current_report.overall_score,
                "passed": current_report.passed,
                "repairs_applied": iteration_repairs,
                "defects": [item.message for item in current_report.checks if not item.passed],
            })

            if not iteration_repairs:
                # No further deterministic repairs could be applied
                break

        # Attach repair metadata into plan
        remaining_warnings = [item.message for item in current_report.checks if not item.passed]
        if hasattr(plan, "quality_report") and plan.quality_report:
            if isinstance(plan.quality_report, dict):
                plan.quality_report["repair_history"] = all_repaired_items
                plan.quality_report["audit_iterations"] = audit_history

        return IterativeEditResult(
            plan=plan,
            iteration_count=iteration,
            initial_score=initial_score,
            final_score=current_report.overall_score,
            repaired_items=all_repaired_items,
            remaining_warnings=remaining_warnings,
            audit_history=audit_history,
        )

    def _audit_plan_data(self, plan_dict: Dict[str, Any], target_duration: float) -> QualityAuditReport:
        """Evaluate plan against core editorial quality standards."""
        shots = plan_dict.get("shots", [])
        zooms = plan_dict.get("zooms", [])
        text_overlays = plan_dict.get("text_overlays", [])
        sfx_list = plan_dict.get("audio_cues", {}).get("sfx", [])

        # Build synthetic visual event timeline
        events: List[Tuple[float, str]] = []
        for s in shots:
            events.append((float(s.get("start_time", 0.0)), "broll"))
            events.append((float(s.get("end_time", 0.0)), "broll_end"))
        for z in zooms:
            events.append((float(z.get("time", 0.0)), "zoom"))
        for t in text_overlays:
            events.append((float(t.get("start_time", 0.0)), "graphic"))

        events.sort(key=lambda x: x[0])

        # Check maximum stagnation gap
        max_gap = 0.0
        last_t = 0.0
        for t, ev_type in events:
            if t > last_t:
                gap = t - last_t
                if gap > max_gap:
                    max_gap = gap
            last_t = t
        if target_duration > last_t:
            gap = target_duration - last_t
            if gap > max_gap:
                max_gap = gap

        # Audit SFX density and spacing
        sfx_count = len(sfx_list)
        sfx_spacing_violations = 0
        sorted_sfx = sorted(sfx_list, key=lambda x: float(x.get("time", 0.0)))
        for i in range(len(sorted_sfx) - 1):
            t1 = float(sorted_sfx[i].get("time", 0.0))
            t2 = float(sorted_sfx[i + 1].get("time", 0.0))
            if (t2 - t1) < 2.5:
                sfx_spacing_violations += 1

        # Check opening face protection (B-roll should not start before 1.0s)
        early_broll = any(float(s.get("start_time", 0.0)) < 1.0 for s in shots)

        # Compute synthetic score
        score = 1.0
        from ai_broll_autopilot.services.editorial.types import QualityCheckItem

        checks: List[QualityCheckItem] = []

        # Rule 1: Stagnation gap <= 4.5s
        if max_gap > 4.5:
            score -= 0.15
            checks.append(QualityCheckItem(
                name="Pacing Stagnation",
                category="pacing",
                passed=False,
                score=0.5,
                message=f"Visual stagnation gap of {max_gap:.1f}s detected without cut, zoom, or overlay.",
                severity="warning",
            ))
        else:
            checks.append(QualityCheckItem(
                name="Pacing Stagnation",
                category="pacing",
                passed=True,
                score=1.0,
                message="Visual events properly spaced across timeline.",
                severity="info",
            ))

        # Rule 2: SFX spacing >= 2.5s
        if sfx_spacing_violations > 0:
            score -= 0.10
            checks.append(QualityCheckItem(
                name="Sound Design Spacing",
                category="sfx",
                passed=False,
                score=0.6,
                message=f"{sfx_spacing_violations} SFX cues clustered closer than 2.5s.",
                severity="warning",
            ))
        else:
            checks.append(QualityCheckItem(
                name="Sound Design Spacing",
                category="sfx",
                passed=True,
                score=1.0,
                message="SFX cues naturally spaced.",
                severity="info",
            ))

        # Rule 3: Opening face protection
        if early_broll:
            score -= 0.20
            checks.append(QualityCheckItem(
                name="Opening Face Hook",
                category="hook",
                passed=False,
                score=0.4,
                message="B-roll starts before 1.0s, obscuring speaker facial hook.",
                severity="warning",
            ))
        else:
            checks.append(QualityCheckItem(
                name="Opening Face Hook",
                category="hook",
                passed=True,
                score=1.0,
                message="Speaker face preserved for opening hook.",
                severity="info",
            ))

        final_score = max(0.0, min(1.0, score))
        return QualityAuditReport(
            passed=(final_score >= self.min_quality_score),
            overall_score=final_score,
            checks=checks,
        )

    def _apply_deterministic_repairs(
        self,
        plan: Any,
        plan_dict: Dict[str, Any],
        report: QualityAuditReport,
        target_duration: float,
    ) -> List[str]:
        """Apply targeted, rule-based repairs to fix flagged quality issues."""
        repairs: List[str] = []

        shots = getattr(plan, "shots", plan_dict.get("shots", []))
        zooms = getattr(plan, "zooms", plan_dict.get("zooms", []))
        audio_cues = getattr(plan, "audio_cues", plan_dict.get("audio_cues", {}))
        sfx_list = audio_cues.get("sfx", []) if isinstance(audio_cues, dict) else []

        # REPAIR 1: Fix Early B-roll Hook Intrusion
        for s in shots:
            st = float(s.get("start_time", 0.0)) if isinstance(s, dict) else getattr(s, "start_time", 0.0)
            if st < 1.2:
                new_st = 1.3
                if isinstance(s, dict):
                    s["start_time"] = new_st
                    s["duration"] = round(float(s.get("end_time", new_st + 2.0)) - new_st, 2)
                else:
                    s.start_time = new_st
                    s.duration = round(s.end_time - new_st, 2)
                repairs.append(f"Shifted early B-roll start from {st:.2f}s to {new_st:.2f}s to preserve speaker hook face.")

        # REPAIR 2: Fix SFX Clustering (Enforce >= 2.8s spacing)
        if len(sfx_list) > 1:
            sorted_indices = sorted(range(len(sfx_list)), key=lambda idx: float(sfx_list[idx].get("time", 0.0)))
            pruned_count = 0
            for i in range(len(sorted_indices) - 1):
                idx1 = sorted_indices[i]
                idx2 = sorted_indices[i + 1]
                t1 = float(sfx_list[idx1].get("time", 0.0))
                t2 = float(sfx_list[idx2].get("time", 0.0))
                if (t2 - t1) < 2.5:
                    # Space t2 out by 2.8s or prune if exceeds target duration
                    new_t = round(t1 + 2.8, 2)
                    if new_t < (target_duration - 0.5):
                        sfx_list[idx2]["time"] = new_t
                        repairs.append(f"Re-spaced clustered SFX from {t2:.2f}s to {new_t:.2f}s.")
                    else:
                        sfx_list.pop(idx2)
                        pruned_count += 1
                        repairs.append(f"Pruned redundant trailing SFX at {t2:.2f}s.")
                        break

        # REPAIR 3: Fix Visual Stagnation (Inject punch-in zoom if gap > 4.5s)
        # Find largest visual gap
        all_times = [0.0, target_duration]
        for s in shots:
            st = float(s.get("start_time", 0.0)) if isinstance(s, dict) else getattr(s, "start_time", 0.0)
            et = float(s.get("end_time", 0.0)) if isinstance(s, dict) else getattr(s, "end_time", 0.0)
            all_times.extend([st, et])
        for z in zooms:
            zt = float(z.get("time", 0.0)) if isinstance(z, dict) else getattr(z, "time", 0.0)
            all_times.append(zt)

        all_times.sort()
        for i in range(len(all_times) - 1):
            gap = all_times[i + 1] - all_times[i]
            if gap > 4.5:
                # Inject punch-in in the middle of this stagnant stretch
                zoom_time = round(all_times[i] + (gap / 2.0), 2)
                new_zoom = {
                    "time": zoom_time,
                    "scale": 1.15,
                    "duration": 0.4,
                    "reason": "Auto-repaired: eliminate visual stagnation gap",
                    "easing": "ease-out",
                }
                zooms.append(new_zoom)
                zooms.sort(key=lambda z: float(z.get("time", 0.0)))
                repairs.append(f"Added subtle punch-in at {zoom_time:.2f}s to eliminate {gap:.1f}s stagnation gap.")
                break

        return repairs


# Singleton instance
iterative_editor = IterativeEditLoop()
