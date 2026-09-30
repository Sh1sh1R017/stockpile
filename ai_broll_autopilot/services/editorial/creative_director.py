"""Creative Director: turns editorial moments into coordinated edit intent.

This layer is deliberately deterministic and provider-agnostic. It does not render
anything; it decides how much visual/audio attention each moment deserves so the
caption, B-roll, meme, SFX, and camera systems can share one editorial language.
"""

from typing import Any, Dict, List, Tuple

from ai_broll_autopilot.services.editorial.types import (
    EditIntent,
    EditorialMoment,
    NarrativeRole,
    SentimentCategory,
)


class CreativeDirector:
    """Master attention allocator for the editorial pipeline."""

    CHAOS_REGEN_PER_SEC = 0.22
    CHAOS_COSTS = {"kinetic": 0.20, "impact": 0.48, "absurd": 0.82}

    _HIGH_SIGNAL_WORDS = {
        "never", "always", "literally", "insane", "crazy", "chaos", "worst",
        "best", "secret", "truth", "actually", "shocking", "ridiculous",
        "fired", "failed", "win", "won", "lost", "hate", "love",
    }

    _MEME_WORDS = {
        "bro", "wtf", "fuck", "shit", "damn", "crazy", "insane", "stupid",
        "ridiculous", "embarrassing", "awkward", "oops", "mistake",
    }

    def analyze_moment(self, moment: EditorialMoment, is_hook: bool = False) -> EditIntent:
        text = (moment.text or "").strip().lower()
        tokens = {t.strip(".,!?;:()[]{}\"'") for t in text.split() if t.strip()}
        lexical_signal = min(1.0, len(tokens & self._HIGH_SIGNAL_WORDS) / 2.0)
        meme_signal = min(1.0, len(tokens & self._MEME_WORDS) / 2.0)

        role_signal = {
            NarrativeRole.HOOK: 1.0,
            NarrativeRole.PAYOFF: 0.95,
            NarrativeRole.REVEAL: 0.9,
            NarrativeRole.CONTRAST: 0.82,
            NarrativeRole.REACTION: 0.78,
            NarrativeRole.CLAIM: 0.68,
            NarrativeRole.STORY: 0.55,
            NarrativeRole.EXAMPLE: 0.48,
            NarrativeRole.EXPLANATION: 0.38,
            NarrativeRole.SETUP: 0.32,
            NarrativeRole.STATISTIC: 0.72,
            NarrativeRole.CTA: 0.42,
        }.get(moment.narrative_role, 0.5)

        emotional = max(moment.emotional_intensity, moment.energy_level)
        semantic = max(moment.information_density, role_signal)
        visual = moment.visual_opportunity
        hook = 1.0 if is_hook or moment.narrative_role == NarrativeRole.HOOK else 0.0

        comedy = 1.0 if moment.sentiment == SentimentCategory.FUNNY else 0.0
        meme = min(1.0, 0.45 * meme_signal + 0.35 * comedy + 0.20 * emotional)

        chaos = (
            0.22 * semantic
            + 0.20 * emotional
            + 0.18 * hook
            + 0.16 * moment.speaker_emphasis
            + 0.10 * visual
            + 0.08 * lexical_signal
            + 0.06 * meme
        )
        chaos = max(0.0, min(1.0, chaos))

        # Deliberate quietness: important for contrast and recovery between punches.
        quietness = max(
            0.0,
            min(
                1.0,
                1.0
                - (0.48 * chaos)
                - (0.22 * moment.speaker_emphasis)
                - (0.15 * emotional)
                + (0.20 if moment.sentiment == SentimentCategory.REFLECTIVE else 0.0),
            ),
        )

        if chaos >= 0.82:
            treatment = "absurd"
        elif chaos >= 0.64:
            treatment = "impact"
        elif chaos >= 0.45:
            treatment = "kinetic"
        elif quietness >= 0.62:
            treatment = "quiet"
        else:
            treatment = "normal"

        broll_pressure = max(
            0.0,
            min(
                1.0,
                0.52 * visual
                + 0.22 * semantic
                + 0.16 * (1.0 - min(1.0, moment.speaker_emphasis))
                + 0.10 * emotional,
            ),
        )

        caption_energy = max(
            0.0,
            min(1.0, 0.40 * chaos + 0.30 * moment.speaker_emphasis + 0.30 * semantic),
        )

        sfx_opportunity = max(
            0.0,
            min(1.0, 0.55 * chaos + 0.25 * emotional + 0.20 * moment.speaker_emphasis),
        )

        reason_parts = [
            f"role={moment.narrative_role.value.lower()}",
            f"emotion={emotional:.2f}",
            f"visual={visual:.2f}",
        ]
        if lexical_signal:
            reason_parts.append(f"lexical_signal={lexical_signal:.2f}")
        if meme:
            reason_parts.append(f"meme={meme:.2f}")

        return EditIntent(
            semantic_importance=semantic,
            emotional_importance=emotional,
            hook_relevance=hook,
            speaker_emphasis=moment.speaker_emphasis,
            visual_opportunity=visual,
            meme_opportunity=meme,
            caption_energy=caption_energy,
            broll_pressure=broll_pressure,
            sfx_opportunity=sfx_opportunity,
            chaos_score=chaos,
            quietness_score=quietness,
            treatment=treatment,
            reason=", ".join(reason_parts),
        )

    def analyze(self, moments: List[EditorialMoment], hook_moment_id: str = "") -> List[EditIntent]:
        """Score moments and ration expensive treatments across the timeline."""
        intents: List[EditIntent] = []
        budget = 1.0
        previous_time = moments[0].start_time if moments else 0.0

        for moment in moments:
            intent = self.analyze_moment(
                moment,
                is_hook=(moment.moment_id == hook_moment_id),
            )
            elapsed = max(0.0, float(moment.start_time) - float(previous_time))
            budget = min(1.0, budget + elapsed * self.CHAOS_REGEN_PER_SEC)

            desired = intent.treatment if intent.treatment in {"quiet", "normal", "kinetic", "impact", "absurd"} else "normal"
            if desired == "absurd" and budget < self.CHAOS_COSTS["absurd"]:
                desired = "impact" if budget >= self.CHAOS_COSTS["impact"] else "kinetic" if budget >= self.CHAOS_COSTS["kinetic"] else "normal"
            elif desired == "impact" and budget < self.CHAOS_COSTS["impact"]:
                desired = "kinetic" if budget >= self.CHAOS_COSTS["kinetic"] else "normal"
            elif desired == "kinetic" and budget < self.CHAOS_COSTS["kinetic"]:
                desired = "normal"

            budget = max(0.0, budget - self.CHAOS_COSTS.get(desired, 0.0))
            intent.start_time = float(moment.start_time)
            intent.end_time = float(moment.end_time)
            intent.treatment = desired
            intent.chaos_tier = desired
            intent.chaos_budget_remaining = budget
            intents.append(intent)
            previous_time = moment.start_time

        return intents

    @staticmethod
    def choose_camera(moments: List[EditorialMoment], intents: List[EditIntent]) -> List[Tuple[EditorialMoment, EditIntent]]:
        """Return moments that earned a camera punch without keyword-trigger spam."""
        return [
            (moment, intent)
            for moment, intent in zip(moments, intents)
            if intent.treatment in {"impact", "absurd"}
            and intent.speaker_emphasis >= 0.62
        ]


creative_director = CreativeDirector()
