"""Contextual, Sentiment-Aware B-Roll Editorial Intelligence.

Evaluates B-roll cutaway candidates using multi-metric contextual scoring, aligns emotional sentiment,
assigns narrative justifications ('Why is this visual here?'), computes adaptive durations, and
strictly rejects low-confidence filler footage to intentionally preserve strong A-roll delivery.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialMoment,
    NarrativeRole,
    PacingCategory,
    SentimentCategory,
    ShotType,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine

logger = logging.getLogger("autopilot.editorial.broll")


class BrollIntelligence:
    """Contextual and sentiment-aware B-roll decision engine."""

    # Sentiment footage keywords for emotional alignment
    SENTIMENT_FOOTAGE_MAPPINGS = {
        SentimentCategory.NEGATIVE: {
            "boost": ["stressed", "decline", "crash", "red chart", "loss", "head in hands", "empty", "dark", "rain", "frustrated", "error", "fire", "broken"],
            "penalize": ["celebrate", "laughing", "cheering", "beach", "party", "sunny", "fireworks", "champagne", "thumbs up"],
        },
        SentimentCategory.POSITIVE: {
            "boost": ["celebration", "growth", "green chart", "success", "handshake", "smiling", "high five", "trophy", "skyline", "bright", "cheering"],
            "penalize": ["crying", "ruins", "funeral", "depressed", "garbage", "dark alley", "poverty"],
        },
        SentimentCategory.TENSION: {
            "boost": ["suspense", "ticking clock", "shadow", "countdown", "intense eye", "whisper", "boardroom confrontation", "police lights", "running"],
            "penalize": ["relaxing", "spa", "sleeping", "picnic", "lazy"],
        },
        SentimentCategory.REFLECTIVE: {
            "boost": ["looking out window", "sunset", "walking alone", "nature", "silhouette", "slow motion", "coffee cup", "peaceful", "books"],
            "penalize": ["fast action", "explosion", "club", "laser", "sports slam dunk"],
        },
        SentimentCategory.TECHNICAL: {
            "boost": ["code", "software interface", "server room", "diagram", "circuit board", "data visualization", "keyboard typing", "screen ui"],
            "penalize": ["farm", "animals", "comedy", "beach", "forest"],
        },
        SentimentCategory.FUNNY: {
            "boost": ["facepalm", "laughing", "awkward look", "confused", "double take", "comic contrast"],
            "penalize": ["grave", "tragedy", "hospital", "war"],
        },
    }

    # Minimum acceptance threshold: candidates below this score are rejected in favor of A-roll
    ACCEPTANCE_THRESHOLD = 0.65

    def __init__(self, acceptance_threshold: float = 0.65):
        self.acceptance_threshold = acceptance_threshold

    def evaluate_and_plan_shot(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        is_first_moment: bool = False,
    ) -> Optional[ContextualBrollDecision]:
        """Evaluate whether a moment justifies B-roll and select the most contextually relevant visual.

        Returns:
            ContextualBrollDecision if a high-confidence match is found, otherwise None (retains A-roll).
        """
        # RULE 1: Never cover the opening hook face
        if is_first_moment or moment.start_time < 1.2:
            logger.debug(f"Moment [{moment.moment_id}] is the opening hook: intentionally retaining A-roll.")
            return None

        # RULE 2: If visual opportunity is low and speaker emphasis is high, speaker expression is the strongest visual
        if moment.visual_opportunity < 0.40 and moment.speaker_emphasis >= 0.70:
            logger.info(f"Moment [{moment.moment_id}]: High speaker intensity with abstract dialogue -> Intentionally retaining A-roll.")
            return None

        # RULE 3: Assign clear narrative role answering "Why is this visual here?"
        narrative_role = self._assign_narrative_role(moment)
        reason = self._generate_role_reason(moment, narrative_role)

        # RULE 4: Calculate adaptive duration based on pacing requirements and cognitive load
        target_duration = self._calculate_adaptive_duration(moment)
        shot_start = round(moment.start_time, 2)
        shot_end = round(min(moment.end_time, shot_start + target_duration), 2)
        actual_duration = round(shot_end - shot_start, 2)

        if actual_duration < 1.5:
            logger.debug(f"Moment [{moment.moment_id}]: Duration ({actual_duration}s) too brief for quality B-roll cutaway.")
            return None

        # Formulate search query for footage acquisition
        search_query = self._build_search_query(moment, narrative_role)

        # If no library assets are provided, generate recommended editorial shot specification
        if not available_assets:
            variety_engine.record_placed_shot(
                shot_id=f"shot_{moment.moment_id}",
                shot_type=ShotType.MEDIUM,
                subject_category=moment.semantic_topic or "editorial",
                camera_movement="dynamic",
                location="contextual",
                semantic_theme=moment.semantic_topic,
            )
            return ContextualBrollDecision(
                shot_id=f"broll_{moment.moment_id}",
                moment_id=moment.moment_id,
                start_time=shot_start,
                end_time=shot_end,
                duration=actual_duration,
                narrative_role=narrative_role,
                pacing_category=moment.pacing_requirement,
                shot_type=ShotType.MEDIUM,
                subject_category=moment.semantic_topic or "editorial",
                search_query=search_query,
                asset_path=None,
                reason=reason,
                emotional_intent=moment.sentiment.value if hasattr(moment.sentiment, "value") else str(moment.sentiment),
                scores=BrollCandidateScore(
                    semantic_match=0.85,
                    sentiment_match=0.8,
                    narrative_match=0.85,
                    visual_quality=0.8,
                    final_score=0.85,
                    confidence=0.85,
                    decision="ACCEPT",
                ),
            )

        # RULE 5: Score available assets against contextual criteria
        scored_candidates: List[Tuple[Dict[str, Any], BrollCandidateScore]] = []

        for asset in available_assets:
            score = self.score_candidate_asset(
                moment=moment,
                asset=asset,
                target_duration=actual_duration,
                narrative_role=narrative_role,
                variety_engine=variety_engine,
            )
            scored_candidates.append((asset, score))

        # Sort by final score descending
        scored_candidates.sort(key=lambda x: x[1].final_score, reverse=True)

        # RULE 6: Reject low-confidence candidates (DO NOT optimize for B-roll percentage)
        if not scored_candidates or scored_candidates[0][1].final_score < self.acceptance_threshold:
            best_score = scored_candidates[0][1].final_score if scored_candidates else 0.0
            logger.info(
                f"Moment [{moment.moment_id}]: Best B-roll score ({best_score:.2f}) < threshold ({self.acceptance_threshold}). "
                f"Intentionally retaining A-roll over irrelevant filler."
            )
            return None

        best_asset, best_score = scored_candidates[0]
        shot_type = self._infer_shot_type(best_asset)
        subject_category = best_asset.get("category", "general")

        # Record visual variety in history
        variety_engine.record_placed_shot(
            shot_id=f"shot_{moment.moment_id}",
            shot_type=shot_type,
            subject_category=subject_category,
            camera_movement=best_asset.get("camera_movement", "static"),
            location=best_asset.get("location", "indoor"),
            semantic_theme=moment.semantic_topic,
        )

        decision = ContextualBrollDecision(
            shot_id=f"broll_{moment.moment_id}",
            moment_id=moment.moment_id,
            start_time=shot_start,
            end_time=shot_end,
            duration=actual_duration,
            narrative_role=narrative_role,
            reason=reason,
            search_query=search_query,
            emotional_intent=f"Aligns with {moment.sentiment.value} emotional tone ({moment.emotional_intensity:.1f})",
            pacing_category=moment.pacing_requirement,
            scores=best_score,
            asset_path=best_asset.get("file_path") or best_asset.get("asset_path"),
            asset_name=Path(best_asset.get("file_path", "cutaway.mp4")).name,
            shot_type=shot_type,
            subject_category=subject_category,
            status="matched",
        )

        logger.info(
            f"Accepted B-roll [{decision.shot_id}] ({decision.duration:.1f}s): '{best_asset.get('title', 'asset')}' "
            f"Score: {best_score.final_score:.2f} | Role: {narrative_role.value} | Reason: {reason}"
        )
        return decision

    def score_candidate_asset(
        self,
        moment: EditorialMoment,
        asset: Dict[str, Any],
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        variety_engine: VisualVarietyEngine,
    ) -> BrollCandidateScore:
        """Calculate multi-metric contextual score for a candidate footage asset."""
        title = (asset.get("title") or asset.get("name") or "").lower()
        tags_raw = asset.get("tags") or []
        tags_str = " ".join(tags_raw) if isinstance(tags_raw, list) else str(tags_raw)
        prompt = (asset.get("prompt") or tags_str).lower()
        asset_text = f"{title} {prompt}"
        moment_text = moment.text.lower()

        # STEP 0: Disambiguation & Semantic Contradiction Veto Audit
        from ai_broll_autopilot.services.retrieval_engine import retrieval_engine
        detected_domain, active_rules = retrieval_engine._disambiguate_context(moment)
        retrieval_eval = retrieval_engine._evaluate_single_candidate(
            moment=moment,
            asset=asset,
            target_duration=target_duration,
            narrative_role=narrative_role,
            variety_engine=variety_engine,
            detected_domain=detected_domain,
            active_rules=active_rules,
        )
        if retrieval_eval.is_vetoed:
            return retrieval_eval.to_score_breakdown()

        # 1. Semantic Match (0.0 to 1.0)
        semantic_score = 0.35
        # Entity matching
        for ent in moment.entities:
            if ent.lower() in asset_text:
                semantic_score += 0.30
                break
        # Topic keyword matching
        topic_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", moment.semantic_topic.lower()) if w not in ["with", "from"]]
        for tw in topic_words:
            if tw in asset_text:
                semantic_score += 0.20
                break
        # General word overlap
        moment_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", moment_text))
        asset_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", asset_text))
        overlap = len(moment_words.intersection(asset_words))
        semantic_score += min(0.30, overlap * 0.10)
        semantic_score = min(1.0, max(0.1, semantic_score))

        # 2. Sentiment Match (0.0 to 1.0)
        sentiment_score = 0.70
        mapping = self.SENTIMENT_FOOTAGE_MAPPINGS.get(moment.sentiment, {})
        boosts = mapping.get("boost", [])
        penalties = mapping.get("penalize", [])

        if any(b in asset_text for b in boosts):
            sentiment_score += 0.25
        if any(p in asset_text for p in penalties):
            sentiment_score -= 0.50  # Severely penalize emotionally contradictory footage!

        sentiment_score = min(1.0, max(0.1, sentiment_score))

        # 3. Action Match (0.0 to 1.0)
        action_score = 0.50
        if moment.action != "explaining concept":
            action_terms = moment.action.lower().split(" / ")
            if any(term in asset_text for term in action_terms):
                action_score = 0.95
            else:
                action_score = 0.40

        # 4. Narrative Match (0.0 to 1.0)
        narrative_score = 0.75
        if narrative_role in [BrollNarrativeRole.ILLUSTRATE, BrollNarrativeRole.EXPLAIN] and semantic_score >= 0.6:
            narrative_score = 0.90
        elif narrative_role == BrollNarrativeRole.CONTRAST and sentiment_score >= 0.8:
            narrative_score = 0.90

        # 5. Visual Quality (0.0 to 1.0)
        quality_score = float(asset.get("score", 8)) / 10.0
        if asset.get("watermarked", False):
            quality_score = 0.1

        # 6. Freshness (0.0 to 1.0)
        freshness_score = 1.0
        used_count = asset.get("use_count", 0)
        if used_count > 0:
            freshness_score = max(0.2, 1.0 - (used_count * 0.3))

        # 7. Duration Fit (0.0 to 1.0)
        asset_dur = float(asset.get("duration", target_duration))
        if asset_dur >= target_duration:
            duration_fit = 1.0
        elif asset_dur >= target_duration * 0.75:
            duration_fit = 0.80
        else:
            duration_fit = 0.40

        # 8. Visual Variety Penalty
        shot_type = self._infer_shot_type(asset)
        subject = asset.get("category", "general")
        variety_factor = variety_engine.evaluate_variety(
            candidate_shot_type=shot_type,
            subject_category=subject,
        )

        # Composite score
        weighted_base = (
            semantic_score * 0.25
            + sentiment_score * 0.20
            + action_score * 0.15
            + narrative_score * 0.15
            + quality_score * 0.10
            + freshness_score * 0.05
            + duration_fit * 0.10
        )
        final_score = round(weighted_base * variety_factor, 2)
        confidence = round(weighted_base, 2)

        decision = "ACCEPT" if final_score >= self.acceptance_threshold else "RETAIN_A_ROLL"
        rejection_reason = None
        if decision == "RETAIN_A_ROLL":
            if sentiment_score < 0.4:
                rejection_reason = "Emotionally contradictory footage"
            elif semantic_score < 0.4:
                rejection_reason = "Irrelevant keyword mismatch"
            elif variety_factor < 0.6:
                rejection_reason = "Repetitive visual monotony"
            else:
                rejection_reason = "Low composite confidence"

        return BrollCandidateScore(
            semantic_match=semantic_score,
            sentiment_match=sentiment_score,
            action_match=action_score,
            narrative_match=narrative_score,
            visual_quality=quality_score,
            freshness=freshness_score,
            duration_fit=duration_fit,
            variety_penalty=round(1.0 - variety_factor, 2),
            final_score=final_score,
            confidence=confidence,
            decision=decision,
            rejection_reason=rejection_reason,
        )

    def _assign_narrative_role(self, moment: EditorialMoment) -> BrollNarrativeRole:
        """Assign explicit editorial narrative justification."""
        if moment.narrative_role == NarrativeRole.CONTRAST:
            return BrollNarrativeRole.CONTRAST
        if moment.narrative_role in [NarrativeRole.EXPLANATION, NarrativeRole.EXAMPLE]:
            return BrollNarrativeRole.EXPLAIN
        if moment.narrative_role in [NarrativeRole.CLAIM, NarrativeRole.STATISTIC]:
            return BrollNarrativeRole.REINFORCE
        if moment.narrative_role == NarrativeRole.REVEAL:
            return BrollNarrativeRole.REVEAL
        if moment.speaker_emphasis >= 0.75:
            return BrollNarrativeRole.EMPHASIZE
        return BrollNarrativeRole.ILLUSTRATE

    def _generate_role_reason(self, moment: EditorialMoment, role: BrollNarrativeRole) -> str:
        """Formulate a human-editor rationale answering 'Why is this visual here?'."""
        if role == BrollNarrativeRole.ILLUSTRATE:
            return f"Visually illustrates spoken concept '{moment.semantic_topic}' to clarify meaning."
        if role == BrollNarrativeRole.REINFORCE:
            return f"Reinforces key claim with evidence-based visual imagery."
        if role == BrollNarrativeRole.CONTRAST:
            return f"Creates visual juxtaposition highlighting the spoken contradiction."
        if role == BrollNarrativeRole.EXPLAIN:
            return f"Provides explanatory context while speaker describes complex details."
        if role == BrollNarrativeRole.EMPHASIZE:
            return f"Emphasizes climax of spoken delivery."
        if role == BrollNarrativeRole.REVEAL:
            return f"Synchronizes visual reveal with spoken turning point."
        return "Resets visual fatigue to sustain viewer engagement."

    def _calculate_adaptive_duration(self, moment: EditorialMoment) -> float:
        """Determine duration (3-5s default, 2-3s high-energy, 6-8s reflective) adapted to cognitive load."""
        pacing = moment.pacing_requirement

        if pacing == PacingCategory.HIGH_ENERGY:
            base_dur = 2.6
        elif pacing == PacingCategory.REFLECTIVE:
            base_dur = 6.5
        elif pacing == PacingCategory.DEEP_EXPLANATION:
            base_dur = 4.8
        else:
            base_dur = 3.6  # Default short-form sweet spot (3.0s - 5.0s)

        # Adjust for speech information density: high density needs +0.5s for viewer to comprehend
        if moment.information_density >= 0.70:
            base_dur += 0.6
        elif moment.information_density <= 0.30 and pacing == PacingCategory.HIGH_ENERGY:
            base_dur -= 0.4

        # Clamp between 1.8s and 8.0s, and don't exceed moment duration + 1.0s
        clamped = max(1.8, min(8.0, min(base_dur, moment.duration + 0.8)))
        return round(clamped, 2)

    def _build_search_query(self, moment: EditorialMoment, role: BrollNarrativeRole) -> str:
        """Construct a clean, targeted search query representing the core visual metaphor."""
        entities = " ".join(moment.entities[:2]) if moment.entities else ""
        if entities and len(entities) > 3:
            return f"{entities} {moment.sentiment.value}".strip()
        if moment.action != "explaining concept":
            return f"{moment.action} {moment.sentiment.value}".strip()
        return f"{moment.semantic_topic} {moment.sentiment.value}".strip()

    def _infer_shot_type(self, asset: Dict[str, Any]) -> ShotType:
        """Infer shot framing from asset metadata."""
        text = f"{asset.get('title', '')} {asset.get('prompt', '')}".lower()
        if any(w in text for w in ["close up", "macro", "hands", "fingers", "detail"]):
            return ShotType.DETAIL
        if any(w in text for w in ["wide", "aerial", "skyline", "drone", "landscape"]):
            return ShotType.WIDE
        if any(w in text for w in ["screen", "interface", "monitor", "dashboard", "chart"]):
            return ShotType.SCREEN
        return ShotType.MEDIUM
