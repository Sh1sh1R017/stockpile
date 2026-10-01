"""Hierarchical Semantic B-Roll Retrieval & Contradiction Filtering Engine.

Provides deep contextual matching, homonym/metaphor disambiguation, and strict veto rules
inspired by video-db/Director and Andrea13235/Retention:
- Disambiguates metaphors (e.g. 'running a startup' vs physical sprinting; 'pitching VCs' vs baseball).
- Multi-metric candidate evaluation (semantic, topic, entity, action, emotional, temporal, visual quality).
- Strict Semantic Contradiction Filter: detects topic domain mismatches (e.g. basketball footage in tech SaaS videos).
- Strict Veto Rules: immediately disqualifies contradictory candidates (veto_score >= 0.65).
- Clean Fallback to A-Roll: when confidence < 0.65, intentionally preserves speaker A-roll.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ai_broll_autopilot.services.editorial.types import (
    BrollCandidateScore,
    BrollNarrativeRole,
    ContextualBrollDecision,
    EditorialMoment,
    PacingCategory,
    SentimentCategory,
    ShotType,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine

logger = logging.getLogger("autopilot.retrieval")


class SemanticDomain(str, Enum):
    """Broad conceptual domain classifications for disambiguation."""
    TECH_SOFTWARE = "tech_software"
    BUSINESS_FINANCE = "business_finance"
    SPORTS_ATHLETICS = "sports_athletics"
    HEALTH_MEDICAL = "health_medical"
    LEGAL_GOVERNMENT = "legal_government"
    ENTERTAINMENT_ARTS = "entertainment_arts"
    EDUCATION_SCIENCE = "education_science"
    LIFESTYLE_TRAVEL = "lifestyle_travel"
    GENERAL = "general"


@dataclass
class DisambiguationRule:
    """Homonym or metaphorical phrase disambiguation definition."""
    term: str
    context_keywords: List[str]
    inferred_domain: SemanticDomain
    veto_domains: List[SemanticDomain]
    veto_keywords: List[str]
    rationale: str


@dataclass
class CandidateEvaluationResult:
    """Detailed multi-metric evaluation breakdown for a candidate B-roll asset."""
    asset_id: str
    asset_name: str
    asset_path: str
    semantic_match: float
    topic_coherence: float
    action_match: float
    visual_quality: float
    sentiment_resonance: float
    duration_fit: float
    freshness: float
    variety_penalty: float
    contradiction_score: float
    final_score: float
    confidence: float
    is_vetoed: bool = False
    veto_reason: Optional[str] = None

    def to_score_breakdown(self) -> BrollCandidateScore:
        decision = "ACCEPT" if (not self.is_vetoed and self.final_score >= 0.65) else (
            "REJECT" if self.is_vetoed else "RETAIN_A_ROLL"
        )
        return BrollCandidateScore(
            semantic_match=round(self.semantic_match, 3),
            sentiment_match=round(self.sentiment_resonance, 3),
            action_match=round(self.action_match, 3),
            narrative_match=round(self.topic_coherence, 3),
            visual_quality=round(self.visual_quality, 3),
            freshness=round(self.freshness, 3),
            duration_fit=round(self.duration_fit, 3),
            variety_penalty=round(self.variety_penalty, 3),
            final_score=round(self.final_score, 3),
            confidence=round(self.confidence, 3),
            decision=decision,
            rejection_reason=self.veto_reason,
        )


class SemanticRetrievalEngine:
    """Hierarchical semantic retrieval engine with disambiguation and strict veto gating."""

    # Disambiguation definitions for common metaphorical traps
    DISAMBIGUATION_RULES = [
        DisambiguationRule(
            term="running",
            context_keywords=["company", "startup", "business", "software", "code", "app", "tests", "pipeline", "servers", "operations", "cro", "ceo"],
            inferred_domain=SemanticDomain.TECH_SOFTWARE,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["sprint", "marathon", "track", "sneakers", "jogging", "athletics", "basketball", "gym", "treadmill"],
            rationale="Dialogue refers to running an enterprise/software, not physical athletics.",
        ),
        DisambiguationRule(
            term="pitch",
            context_keywords=["investor", "vc", "seed", "fundraise", "deck", "valuation", "venture", "angel", "startup"],
            inferred_domain=SemanticDomain.BUSINESS_FINANCE,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["baseball", "mound", "catcher", "batter", "strike", "cricket", "pitcher"],
            rationale="Dialogue refers to a venture capital pitch, not baseball/cricket.",
        ),
        DisambiguationRule(
            term="court",
            context_keywords=["lawyer", "judge", "trial", "legal", "lawsuit", "verdict", "supreme court", "attorney", "litigation"],
            inferred_domain=SemanticDomain.LEGAL_GOVERNMENT,
            veto_domains=[SemanticDomain.SPORTS_ATHLETICS],
            veto_keywords=["basketball", "dunk", "hoop", "tennis", "nba", "referee", "foul", "court side"],
            rationale="Dialogue refers to a court of law, not a basketball/tennis court.",
        ),
        DisambiguationRule(
            term="apple",
            context_keywords=["iphone", "mac", "tim cook", "steve jobs", "ios", "silicon", "cupertino", "tech", "app store"],
            inferred_domain=SemanticDomain.TECH_SOFTWARE,
            veto_domains=[SemanticDomain.LIFESTYLE_TRAVEL],
            veto_keywords=["orchard", "fruit", "grocery", "pie", "cider", "harvest", "tree"],
            rationale="Dialogue refers to Apple Inc. technology, not fruit farming.",
        ),
        DisambiguationRule(
            term="dunk",
            context_keywords=["basketball", "nba", "points", "hoop", "slam", "rebound", "collin sexton", "trae", "lebron", "score"],
            inferred_domain=SemanticDomain.SPORTS_ATHLETICS,
            veto_domains=[SemanticDomain.BUSINESS_FINANCE, SemanticDomain.TECH_SOFTWARE],
            veto_keywords=["donuts", "coffee", "cookies", "biscuit", "dunking tea"],
            rationale="Dialogue refers to a basketball slam dunk.",
        ),
    ]

    # Domain keyword signatures
    DOMAIN_SIGNATURES = {
        SemanticDomain.TECH_SOFTWARE: {
            "keywords": ["ai", "software", "code", "cloud", "saas", "api", "database", "developer", "machine learning", "neural", "platform", "algorithm", "backend", "frontend", "server", "model", "python", "javascript"],
            "forbidden_visuals": ["basketball", "football", "boxing", "dunk", "slam dunk", "touchdown", "tennis", "soccer", "marathon"],
        },
        SemanticDomain.BUSINESS_FINANCE: {
            "keywords": ["revenue", "cro", "sales", "arr", "ebitda", "profit", "margins", "fundraising", "valuation", "investors", "growth", "equity", "enterprise", "market", "customer", "b2b"],
            "forbidden_visuals": ["slam dunk", "boxing ring", "football field", "court dunk", "hockey rink"],
        },
        SemanticDomain.SPORTS_ATHLETICS: {
            "keywords": ["dunk", "points", "game", "championship", "hoop", "rebound", "nba", "defense", "offense", "quarter", "coach", "playoff", "athlete", "score"],
            "forbidden_visuals": ["software dashboard", "code editor", "server rack", "excel spreadsheet", "powerpoint"],
        },
    }

    def __init__(self, acceptance_threshold: float = 0.65, contradiction_veto_threshold: float = 0.60):
        self.acceptance_threshold = acceptance_threshold
        self.contradiction_veto_threshold = contradiction_veto_threshold

    def retrieve_and_rank_candidates(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        target_duration: float,
        narrative_role: BrollNarrativeRole,
    ) -> List[CandidateEvaluationResult]:
        """Rank and evaluate all candidate B-roll assets with strict contradiction veto rules."""
        results: List[CandidateEvaluationResult] = []

        # 1. Infer primary domain & active disambiguation rules for this moment
        detected_domain, active_rules = self._disambiguate_context(moment)

        for asset in available_assets:
            evaluation = self._evaluate_single_candidate(
                moment=moment,
                asset=asset,
                target_duration=target_duration,
                narrative_role=narrative_role,
                variety_engine=variety_engine,
                detected_domain=detected_domain,
                active_rules=active_rules,
            )
            results.append(evaluation)

        # Sort: un-vetoed first, then descending final_score
        results.sort(key=lambda x: (not x.is_vetoed, x.final_score), reverse=True)
        return results

    def select_best_decision(
        self,
        moment: EditorialMoment,
        available_assets: List[Dict[str, Any]],
        variety_engine: VisualVarietyEngine,
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        shot_start: float,
        shot_end: float,
    ) -> Optional[ContextualBrollDecision]:
        """Select the best B-roll candidate, or return None to intentionally retain A-roll."""
        ranked = self.retrieve_and_rank_candidates(
            moment=moment,
            available_assets=available_assets,
            variety_engine=variety_engine,
            target_duration=target_duration,
            narrative_role=narrative_role,
        )

        if not ranked:
            return None

        best = ranked[0]

        # Check veto or below acceptance threshold
        if best.is_vetoed:
            logger.info(
                f"Moment [{moment.moment_id}]: Top candidate '{best.asset_name}' VETOED: {best.veto_reason}. "
                f"Intentionally retaining A-roll."
            )
            return None

        if best.final_score < self.acceptance_threshold:
            logger.info(
                f"Moment [{moment.moment_id}]: Best candidate '{best.asset_name}' score ({best.final_score:.2f}) "
                f"< threshold ({self.acceptance_threshold}). Retaining A-roll over weak visual."
            )
            return None

        # Best candidate passed all gates
        shot_type = ShotType.MEDIUM
        raw_type = best.asset_path.lower()
        if "close" in raw_type or "cu" in raw_type:
            shot_type = ShotType.CLOSE_UP
        elif "wide" in raw_type:
            shot_type = ShotType.WIDE
        elif "screen" in raw_type or "ui" in raw_type:
            shot_type = ShotType.SCREEN

        variety_engine.record_placed_shot(
            shot_id=f"shot_{moment.moment_id}",
            shot_type=shot_type,
            subject_category=moment.semantic_topic or "general",
            camera_movement="dynamic",
            location="indoor",
            semantic_theme=moment.semantic_topic,
        )

        return ContextualBrollDecision(
            shot_id=f"broll_{moment.moment_id}",
            moment_id=moment.moment_id,
            start_time=shot_start,
            end_time=shot_end,
            duration=round(shot_end - shot_start, 2),
            narrative_role=narrative_role,
            reason=f"Contextual match for '{moment.text[:40]}' ({best.asset_name})",
            search_query=best.asset_name,
            emotional_intent=moment.sentiment.value,
            pacing_category=moment.pacing_requirement,
            scores=best.to_score_breakdown(),
            asset_path=best.asset_path,
            asset_name=best.asset_name,
            shot_type=shot_type,
            subject_category=moment.semantic_topic or "general",
            status="matched",
        )

    def _disambiguate_context(self, moment: EditorialMoment) -> Tuple[SemanticDomain, List[DisambiguationRule]]:
        """Identify if any homonyms or metaphorical phrases exist in the moment text."""
        text_lower = moment.text.lower()
        active_rules = []

        for rule in self.DISAMBIGUATION_RULES:
            if re.search(r"(?<!\w)" + re.escape(rule.term.lower()) + r"(?!\w)", text_lower):
                # Check if any context keywords confirm the rule
                hits = sum(1 for kw in rule.context_keywords if re.search(r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)", text_lower))
                if hits > 0:
                    active_rules.append(rule)

        # Inferred domain based on signatures
        domain_scores = {d: 0 for d in SemanticDomain}
        for d, sig in self.DOMAIN_SIGNATURES.items():
            for kw in sig["keywords"]:
                if re.search(r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)", text_lower):
                    domain_scores[d] += 1

        best_domain = max(domain_scores.items(), key=lambda x: x[1])
        inferred = best_domain[0] if best_domain[1] > 0 else SemanticDomain.GENERAL

        return inferred, active_rules

    def _evaluate_single_candidate(
        self,
        moment: EditorialMoment,
        asset: Dict[str, Any],
        target_duration: float,
        narrative_role: BrollNarrativeRole,
        variety_engine: VisualVarietyEngine,
        detected_domain: SemanticDomain,
        active_rules: List[DisambiguationRule],
    ) -> CandidateEvaluationResult:
        """Score a single candidate asset against contextual criteria and contradiction rules."""
        asset_id = str(asset.get("id", asset.get("asset_id", "asset_unknown")))
        asset_name = str(asset.get("title") or asset.get("name") or "Unknown Visual")
        asset_path = asset.get("file_path") or asset.get("asset_path") or asset.get("path") or ""
        raw_tags = asset.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [part.strip().lower() for part in re.split(r"[,;|]", raw_tags) if part.strip()]
        else:
            tags = [str(t).strip().lower() for t in raw_tags if t is not None and str(t).strip()]
        category = str(asset.get("category", "") or "").lower()
        description = str(asset.get("description", "") or "").lower()
        prompt = str(asset.get("prompt", "") or "").lower()

        combined_asset_text = f"{asset_name.lower()} {category} {' '.join(tags)} {prompt} {description}"
        moment_text_lower = moment.text.lower()

        # -------------------------------------------------------------
        # STEP 1: CONTRADICTION & VETO AUDIT
        # -------------------------------------------------------------
        contradiction_score = 0.0
        is_vetoed = False
        veto_reason = None

        # Check Active Disambiguation Rules
        for rule in active_rules:
            # Check if candidate contains veto keywords for this disambiguated term
            for veto_kw in rule.veto_keywords:
                if re.search(r"(?<!\w)" + re.escape(veto_kw.lower()) + r"(?!\w)", combined_asset_text):
                    is_vetoed = True
                    contradiction_score = 1.0
                    veto_reason = f"Metaphor contradiction: '{rule.term}' refers to {rule.inferred_domain.value}. Vetoed due to athlete/sports visual '{veto_kw}'."
                    break
            if is_vetoed:
                break

        # Check Inferred Domain Signature Forbidden Visuals
        if not is_vetoed and detected_domain in self.DOMAIN_SIGNATURES:
            forbidden = self.DOMAIN_SIGNATURES[detected_domain]["forbidden_visuals"]
            for f_kw in forbidden:
                if re.search(r"(?<!\w)" + re.escape(f_kw.lower()) + r"(?!\w)", combined_asset_text):
                    is_vetoed = True
                    contradiction_score = 0.95
                    veto_reason = f"Domain contradiction: Content is {detected_domain.value}. Disallowed visual '{f_kw}' detected."
                    break

        # Negative keyword audit (e.g. somber reflective dialogue vs beach party)
        if not is_vetoed:
            if moment.sentiment == SentimentCategory.NEGATIVE:
                party_cues = ["beach", "party", "cheering", "fireworks", "celebration"]
                if any(re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", combined_asset_text) for p in party_cues):
                    contradiction_score = 0.80
                    is_vetoed = True
                    veto_reason = "Emotional contradiction: Somber/serious dialogue paired with celebratory visual."

        # -------------------------------------------------------------
        # STEP 2: MULTI-METRIC CONTEXTUAL SCORING
        # -------------------------------------------------------------
        # 1. Semantic Match (word overlap & keyword presence)
        moment_tokens = set(re.findall(r"\w+", moment_text_lower))
        asset_tokens = set(re.findall(r"\w+", combined_asset_text))
        overlap = len(moment_tokens.intersection(asset_tokens))
        semantic_match = min(1.0, overlap / max(1, len(moment_tokens) * 0.35))

        # 2. Topic Coherence
        topic_coherence = 0.5
        if moment.semantic_topic and moment.semantic_topic.lower() in combined_asset_text:
            topic_coherence = 0.95
        elif category and category in moment_text_lower:
            topic_coherence = 0.85

        # 3. Action Match
        action_match = 0.5
        if moment.action and moment.action.lower() in combined_asset_text:
            action_match = 0.90

        # 4. Sentiment Resonance
        sentiment_resonance = 0.6
        if moment.sentiment == SentimentCategory.TECHNICAL:
            tech_indicators = ["code", "software", "screen", "server", "data", "chart"]
            if any(t in combined_asset_text for t in tech_indicators):
                sentiment_resonance = 0.95
        elif moment.sentiment == SentimentCategory.POSITIVE:
            pos_indicators = ["success", "growth", "handshake", "smile", "skyline", "trophy"]
            if any(p in combined_asset_text for p in pos_indicators):
                sentiment_resonance = 0.90

        # 5. Visual Quality & Resolution
        visual_quality = 0.85
        width = asset.get("width", 1920)
        height = asset.get("height", 1080)
        if width is not None and height is not None and (width < 1280 or height < 720):
            visual_quality = 0.40
        if asset.get("watermarked"):
            return CandidateEvaluationResult(asset_id=asset_id, asset_name=asset_name, asset_path=asset_path, semantic_match=0.0, topic_coherence=0.0, action_match=0.0, visual_quality=0.0, sentiment_resonance=0.0, duration_fit=0.0, freshness=0.0, variety_penalty=0.0, contradiction_score=1.0, final_score=0.0, confidence=0.0, is_vetoed=True, veto_reason="Watermarked asset")

        # 6. Duration Fit
        asset_duration_raw = asset.get("duration")
        if asset_duration_raw is None:
            return CandidateEvaluationResult(asset_id=asset_id, asset_name=asset_name, asset_path=asset_path, semantic_match=0.0, topic_coherence=0.0, action_match=0.0, visual_quality=0.0, sentiment_resonance=0.0, duration_fit=0.0, freshness=0.0, variety_penalty=0.0, contradiction_score=1.0, final_score=0.0, confidence=0.0, is_vetoed=True, veto_reason="Unknown asset duration")
        speed = max(0.1, float(asset.get("speed") or 1.0))
        asset_duration = float(asset_duration_raw) / speed
        if asset_duration + 0.05 < target_duration:
            duration_fit = max(0.2, asset_duration / max(1.0, target_duration))
        else:
            duration_fit = 1.0

        # 7. Freshness (usage penalty)
        usage_count = int(asset.get("usage_count", 0))
        freshness = max(0.2, 1.0 - (usage_count * 0.25))

        # 8. Visual Variety Penalty
        shot_type = ShotType.MEDIUM
        variety_penalty = variety_engine.calculate_variety_penalty(
            candidate_shot_type=shot_type,
            candidate_subject=category,
            candidate_motion=asset.get("camera_movement", "dynamic"),
        )

        # -------------------------------------------------------------
        # STEP 3: COMPUTE FINAL WEIGHTED SCORE
        # -------------------------------------------------------------
        if is_vetoed:
            final_score = 0.0
            confidence = 0.0
        else:
            weighted = (
                0.30 * semantic_match
                + 0.15 * topic_coherence
                + 0.15 * action_match
                + 0.15 * visual_quality
                + 0.10 * sentiment_resonance
                + 0.08 * duration_fit
                + 0.07 * freshness
                - (0.35 * variety_penalty)
                - (0.50 * contradiction_score)
            )
            final_score = max(0.0, min(1.0, weighted))
            confidence = final_score

        return CandidateEvaluationResult(
            asset_id=asset_id,
            asset_name=asset_name,
            asset_path=asset_path,
            semantic_match=semantic_match,
            topic_coherence=topic_coherence,
            action_match=action_match,
            visual_quality=visual_quality,
            sentiment_resonance=sentiment_resonance,
            duration_fit=duration_fit,
            freshness=freshness,
            variety_penalty=variety_penalty,
            contradiction_score=contradiction_score,
            final_score=final_score,
            confidence=confidence,
            is_vetoed=is_vetoed,
            veto_reason=veto_reason,
        )


# Singleton instance
retrieval_engine = SemanticRetrievalEngine()
