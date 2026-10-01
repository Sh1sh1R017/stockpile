"""Contextual, Sentiment-Aware B-Roll Editorial Intelligence.

Evaluates B-roll cutaway candidates using multi-metric contextual scoring, aligns emotional sentiment,
assigns narrative justifications, computes short-form editorial durations, and rejects weak/generic
footage in favor of clean A-roll.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_broll_autopilot.config import Config
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

    # A candidate must be genuinely useful; B-roll coverage is never the objective.
    ACCEPTANCE_THRESHOLD = 0.72
    MIN_SEMANTIC_SCORE = 0.58
    MIN_NARRATIVE_SCORE = 0.65

    # Generic/text-heavy stock is only acceptable when the narration specifically calls for it.
    GENERIC_VISUAL_TERMS = {
        "generic stock", "generic b roll", "random b roll", "stock footage",
        "news broadcast", "tv broadcast", "news studio", "powerpoint presentation",
        "business presentation", "generic dashboard", "generic chart", "generic graph",
        "random terminal", "code screen", "coding screen", "stock chart",
    }
    TEXT_HEAVY_TERMS = {
        "presentation", "powerpoint", "news broadcast", "news ticker", "headline montage",
        "text animation", "quote card", "title card", "infographic", "article screenshot",
    }

    def __init__(self, acceptance_threshold: float = ACCEPTANCE_THRESHOLD):
        self.acceptance_threshold = acceptance_threshold

    def evaluate_and_plan_shot(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        is_first_moment: bool = False,
    ) -> Optional[ContextualBrollDecision]:
        """Evaluate whether a moment justifies B-roll and select the most contextually relevant visual."""
        if is_first_moment or moment.start_time < 1.2:
            logger.debug(f"Moment [{moment.moment_id}] is the opening hook: retaining A-roll.")
            return None

        if moment.visual_opportunity < 0.40 and moment.speaker_emphasis >= 0.70:
            logger.info(f"Moment [{moment.moment_id}]: speaker emphasis wins over abstract B-roll.")
            return None

        narrative_role = self._assign_narrative_role(moment)
        reason = self._generate_role_reason(moment, narrative_role)
        target_duration = self._calculate_adaptive_duration(moment)
        shot_start = round(moment.start_time, 2)
        shot_end = round(min(moment.end_time, shot_start + target_duration), 2)
        actual_duration = round(max(0.0, shot_end - shot_start), 2)

        min_duration = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
        if actual_duration < min_duration:
            logger.debug(f"Moment [{moment.moment_id}]: only {actual_duration:.2f}s available; retain A-roll.")
            return None

        search_query = self._build_search_query(moment, narrative_role)

        if not available_assets:
            logger.info(
                f"Moment [{moment.moment_id}]: no candidate assets; retaining A-roll."
            )
            return None

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

        eligible_candidates = [
            (asset, score)
            for asset, score in scored_candidates
            if self._candidate_passes_gate(score)
            and (
                asset.get("file_path")
                or asset.get("asset_path")
                or asset.get("path")
            )
        ]
        if not eligible_candidates:
            best_score = max(
                (score.final_score for _, score in scored_candidates),
                default=0.0,
            )
            logger.info(
                f"Moment [{moment.moment_id}]: no eligible B-roll candidate "
                f"(best score {best_score:.2f}); retaining A-roll."
            )
            return None

        best_asset, best_score = max(
            eligible_candidates,
            key=lambda item: item[1].final_score,
        )
        shot_type = self._infer_shot_type(best_asset)
        subject_category = best_asset.get("category", "general")

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
            asset_path=best_asset.get("file_path") or best_asset.get("asset_path") or best_asset.get("path"),
            asset_name=Path(best_asset.get("file_path") or best_asset.get("asset_path") or best_asset.get("path") or "cutaway.mp4").name,
            shot_type=shot_type,
            subject_category=subject_category,
            status="matched",
        )

        logger.info(
            f"Accepted B-roll [{decision.shot_id}] ({decision.duration:.2f}s): '{best_asset.get('title', 'asset')}' "
            f"score={best_score.final_score:.2f}, semantic={best_score.semantic_match:.2f}, role={narrative_role.value}"
        )
        return decision

    def _candidate_passes_gate(self, score: BrollCandidateScore) -> bool:
        """Apply hard editorial gates before a candidate can enter the timeline."""
        return bool(
            score.decision == "ACCEPT"
            and score.final_score >= self.acceptance_threshold
            and score.semantic_match >= self.MIN_SEMANTIC_SCORE
            and score.narrative_match >= self.MIN_NARRATIVE_SCORE
        )

    def score_candidate_asset(
        self,
        moment: EditorialMoment,
        asset: Dict[str, Any],
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        variety_engine: VisualVarietyEngine,
    ) -> BrollCandidateScore:
        """Calculate contextual score; literal semantic fit dominates generic emotional resonance."""
        title = (asset.get("title") or asset.get("name") or "").lower()
        tags_raw = asset.get("tags") or []
        if isinstance(tags_raw, str):
            tags = [part.strip().lower() for part in re.split(r"[,;|]", tags_raw) if part.strip()]
        else:
            tags = [str(part).strip().lower() for part in tags_raw if part is not None and str(part).strip()]
        tags_str = " ".join(tags)
        prompt = str(asset.get("prompt") or "").lower()
        description = str(asset.get("description") or "").lower()
        asset_text = f"{title} {tags_str} {prompt} {description}"
        moment_text = moment.text.lower()
        def has_term(text: str, term: str) -> bool:
            return re.search(r"(?<!\w)" + re.escape(str(term).lower()) + r"(?!\w)", text) is not None

        # Hard media eligibility: never approve assets that cannot cover the
        # entire editorial interval at their intended playback speed.
        if asset.get("watermarked"):
            return BrollCandidateScore(decision="RETAIN_A_ROLL", final_score=0.0, confidence=0.0,
                                       rejection_reason="Watermarked asset")
        duration_raw = asset.get("duration")
        if duration_raw is None:
            # Catalog/test/import paths are not guaranteed to carry ffprobe
            # metadata. Probe a real local file before rejecting it; the matcher
            # remains the final hard media-eligibility gate.
            candidate_path = asset.get("file_path") or asset.get("asset_path") or asset.get("path")
            if candidate_path:
                try:
                    from ai_broll_autopilot.services.broll_library import extract_media_metadata
                    metadata = extract_media_metadata(Path(str(candidate_path)))
                    probed_duration = metadata.get("duration")
                    if probed_duration is not None and float(probed_duration) > 0:
                        duration_raw = float(probed_duration)
                        asset["duration"] = duration_raw
                        if asset.get("width") is None:
                            asset["width"] = metadata.get("width")
                        if asset.get("height") is None:
                            asset["height"] = metadata.get("height")
                except Exception as exc:
                    logger.debug("Could not probe candidate duration for %s: %s", candidate_path, exc)

        if duration_raw is None:
            return BrollCandidateScore(
                decision="RETAIN_A_ROLL",
                final_score=0.0,
                confidence=0.0,
                rejection_reason="Unknown asset duration",
            )

        speed = max(0.1, float(asset.get("speed") or getattr(Config, "BROLL_SPEED_MULTIPLIER", 1.0)))
        effective_duration = float(duration_raw) / speed
        if effective_duration + 0.05 < target_duration:
            return BrollCandidateScore(decision="RETAIN_A_ROLL", final_score=0.0, confidence=0.0,
                                       rejection_reason="Asset too short for approved B-roll interval")
        width, height = asset.get("width"), asset.get("height")
        if width is not None and height is not None and min(int(width), int(height)) < 720:
            return BrollCandidateScore(decision="RETAIN_A_ROLL", final_score=0.0, confidence=0.0,
                                       rejection_reason="Asset resolution below 720px")

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

        semantic_score = 0.25
        for ent in moment.entities:
            if ent.lower() in asset_text:
                semantic_score += 0.35
                break
        topic_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", moment.semantic_topic.lower()) if w not in {"with", "from", "that", "this"}]
        topic_hits = sum(1 for tw in topic_words if tw in asset_text)
        if topic_hits:
            semantic_score += min(0.30, topic_hits * 0.15)
        moment_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", moment_text))
        asset_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", asset_text))
        overlap = len(moment_words.intersection(asset_words))
        semantic_score += min(0.20, overlap * 0.05)
        semantic_score = min(1.0, max(0.05, semantic_score))

        sentiment_score = 0.55
        mapping = self.SENTIMENT_FOOTAGE_MAPPINGS.get(moment.sentiment, {})
        if any(has_term(asset_text, b) for b in mapping.get("boost", [])):
            sentiment_score += 0.30
        if any(has_term(asset_text, p) for p in mapping.get("penalize", [])):
            sentiment_score -= 0.55
        sentiment_score = min(1.0, max(0.05, sentiment_score))

        action_score = 0.50
        if moment.action != "explaining concept":
            action_terms = [t.strip() for t in moment.action.lower().split(" / ") if t.strip()]
            action_score = 0.95 if any(has_term(asset_text, term) or set(re.findall(r"\\w+", term)).issubset(set(re.findall(r"\\w+", asset_text))) for term in action_terms) else 0.35

        narrative_score = 0.60
        if narrative_role in {BrollNarrativeRole.ILLUSTRATE, BrollNarrativeRole.EXPLAIN, BrollNarrativeRole.REINFORCE} and semantic_score >= 0.70:
            narrative_score = 0.90
        elif narrative_role == BrollNarrativeRole.CONTRAST and sentiment_score >= 0.80:
            narrative_score = 0.88
        elif semantic_score >= 0.80:
            narrative_score = 0.78

        quality_score = float(asset.get("score", 8)) / 10.0
        if asset.get("watermarked", False):
            quality_score = 0.1

        # Reject/penalize metadata that explicitly says the visual is text-heavy unless text is the subject.
        text_heavy_flag = bool(
            asset.get("text_heavy") or asset.get("has_overlay_text") or asset.get("contains_text_overlay")
        )
        generic_hits = sum(1 for term in self.GENERIC_VISUAL_TERMS if term in asset_text)
        text_hits = sum(1 for term in self.TEXT_HEAVY_TERMS if term in asset_text)
        if text_heavy_flag:
            text_hits += 1
        text_permission = bool(getattr(moment, "allows_text_heavy_broll", False))
        if text_hits and not text_permission:
            quality_score *= 0.55
        if generic_hits and semantic_score < 0.72:
            quality_score *= 0.60

        freshness_score = 1.0
        used_count = int(asset.get("use_count", asset.get("usage_count", 0)) or 0)
        if used_count > 0:
            freshness_score = max(0.2, 1.0 - (used_count * 0.3))

        asset_dur = float(asset.get("duration", target_duration) or target_duration)
        duration_fit = 1.0 if asset_dur >= target_duration else max(0.4, asset_dur / max(0.5, target_duration))

        shot_type = self._infer_shot_type(asset)
        subject = asset.get("category", "general")
        variety_factor = variety_engine.evaluate_variety(
            candidate_shot_type=shot_type,
            subject_category=subject,
        )

        weighted_base = (
            semantic_score * 0.40
            + action_score * 0.20
            + narrative_score * 0.15
            + sentiment_score * 0.10
            + quality_score * 0.05
            + freshness_score * 0.05
            + duration_fit * 0.05
        )
        final_score = weighted_base * variety_factor
        confidence = weighted_base

        decision = "ACCEPT" if final_score >= self.acceptance_threshold else "RETAIN_A_ROLL"
        rejection_reason = None
        if semantic_score < self.MIN_SEMANTIC_SCORE:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Visual is not specific enough to the spoken proposition"
        elif narrative_score < self.MIN_NARRATIVE_SCORE:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Visual does not clearly explain or reinforce the narrative beat"
        elif text_hits and not text_permission:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Text-heavy visual requires explicit editorial permission"
        elif generic_hits and semantic_score < 0.72:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Generic stock visual is too weakly related to the spoken idea"
        elif variety_factor < 0.6:
            decision = "RETAIN_A_ROLL"
            rejection_reason = "Repetitive visual choice"
        elif decision != "ACCEPT":
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
            final_score=round(final_score, 4),
            confidence=round(confidence, 4),
            decision=decision,
            rejection_reason=rejection_reason,
        )

    def _assign_narrative_role(self, moment: EditorialMoment) -> BrollNarrativeRole:
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
        if role == BrollNarrativeRole.ILLUSTRATE:
            return f"Visually illustrates spoken concept '{moment.semantic_topic}' to clarify meaning."
        if role == BrollNarrativeRole.REINFORCE:
            return "Reinforces the key claim with evidence-based visual imagery."
        if role == BrollNarrativeRole.CONTRAST:
            return "Creates visual juxtaposition highlighting the spoken contradiction."
        if role == BrollNarrativeRole.EXPLAIN:
            return "Provides explanatory context while the speaker describes complex details."
        if role == BrollNarrativeRole.EMPHASIZE:
            return "Emphasizes the climax of spoken delivery."
        if role == BrollNarrativeRole.REVEAL:
            return "Synchronizes the visual reveal with the spoken turning point."
        return "Resets visual fatigue to sustain viewer engagement."

    def _calculate_adaptive_duration(self, moment: EditorialMoment) -> float:
        """Choose an editorial hold, never a duration based on source asset length."""
        pacing = moment.pacing_requirement
        min_dur = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
        max_dur = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8))
        hero_max = float(getattr(Config, "BROLL_HERO_MAX_DURATION", 2.4))

        if pacing == PacingCategory.HIGH_ENERGY:
            base_dur = 0.75 if moment.information_density < 0.70 else 1.0
        elif pacing == PacingCategory.REFLECTIVE:
            base_dur = 1.55
        elif pacing == PacingCategory.DEEP_EXPLANATION:
            base_dur = 1.65
        else:
            base_dur = 1.35

        if moment.information_density >= 0.85:
            base_dur += 0.20
        elif moment.information_density <= 0.25 and pacing == PacingCategory.HIGH_ENERGY:
            base_dur -= 0.10

        # A hero/reveal may breathe slightly longer, but never turns into a 4-8s hold.
        if moment.narrative_role == NarrativeRole.REVEAL and moment.speaker_emphasis >= 0.75:
            base_dur = min(hero_max, max(base_dur, 1.55))

        upper = min(max_dur, hero_max)
        return round(max(min_dur, min(upper, base_dur, max(min_dur, moment.duration))), 2)

    def _build_search_query(self, moment: EditorialMoment, role: BrollNarrativeRole) -> str:
        entities = " ".join(moment.entities[:2]) if moment.entities else ""
        if entities and len(entities) > 3:
            return f"{entities} {moment.sentiment.value}".strip()
        if moment.action != "explaining concept":
            return f"{moment.action} {moment.sentiment.value}".strip()
        return f"{moment.semantic_topic} {moment.sentiment.value}".strip()

    def _infer_shot_type(self, asset: Dict[str, Any]) -> ShotType:
        text = f"{asset.get('title', '')} {asset.get('prompt', '')}".lower()
        if any(w in text for w in ["close up", "macro", "hands", "fingers", "detail"]):
            return ShotType.DETAIL
        if any(w in text for w in ["wide", "aerial", "skyline", "drone", "landscape"]):
            return ShotType.WIDE
        if any(w in text for w in ["screen", "interface", "monitor", "dashboard", "chart"]):
            return ShotType.SCREEN
        return ShotType.MEDIUM
