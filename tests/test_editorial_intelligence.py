"""Unit and Integration Tests for AI Editorial Intelligence Pipeline."""

import unittest
from typing import Dict, Any, List

from ai_broll_autopilot.services.editorial.types import (
    HookCandidate,
    HookScoreBreakdown,
    EditorialMoment,
    BrollCandidateScore,
    ContextualBrollDecision,
    EditorialCaptionSpec,
    EditorialCameraSpec,
    SfxCueDecision,
    QualityAuditReport,
    NarrativeRole,
    BrollNarrativeRole,
    SentimentCategory,
    PacingCategory,
    SfxEventType,
    ShotType,
    EditorialEditSpecification,
)
from ai_broll_autopilot.services.editorial.hook_engine import HookEngine
from ai_broll_autopilot.services.editorial.moment_analyzer import MomentAnalyzer
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine
from ai_broll_autopilot.services.editorial.broll_intelligence import BrollIntelligence
from ai_broll_autopilot.services.editorial.sound_designer import SoundDesigner
from ai_broll_autopilot.services.editorial.pacing_model import PacingModel
from ai_broll_autopilot.services.editorial.quality_gate import EditorialQualityGate
from ai_broll_autopilot.services.editorial.feedback_bridge import EditorialFeedbackBridge
from ai_broll_autopilot.services.editorial.pipeline import EditorialIntelligencePipeline
from ai_broll_autopilot.services.diffusion_adapter import DiffusionAdapter
from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.niches import niche_registry
from ai_broll_autopilot.styles import style_registry


class TestEditorialIntelligence(unittest.TestCase):
    def setUp(self):
        self.sample_segments = [
            {"start": 0.0, "end": 2.5, "text": "So basically what happened is I was completely broke.", "words": [
                {"word": "So", "start": 0.0, "end": 0.2},
                {"word": "basically", "start": 0.2, "end": 0.6},
                {"word": "what", "start": 0.6, "end": 0.8},
                {"word": "happened", "start": 0.8, "end": 1.2},
                {"word": "is", "start": 1.2, "end": 1.4},
                {"word": "I", "start": 1.4, "end": 1.6},
                {"word": "was", "start": 1.6, "end": 1.8},
                {"word": "completely", "start": 1.8, "end": 2.2},
                {"word": "broke.", "start": 2.2, "end": 2.5},
            ]},
            {"start": 2.5, "end": 6.8, "text": "Nobody told you that 87% of creators fail in their very first year.", "words": []},
            {"start": 6.8, "end": 11.2, "text": "We analyzed over 10 million videos to discover the secret formula.", "words": []},
            {"start": 11.2, "end": 16.0, "text": "Here is the exact step-by-step framework you need to implement today.", "words": []},
            {"start": 16.0, "end": 21.0, "text": "First, never start with a boring greeting like 'Hey guys welcome back'.", "words": []},
            {"start": 21.0, "end": 26.5, "text": "Second, maintain high visual energy and cut whenever the concept shifts.", "words": []},
            {"start": 26.5, "end": 30.0, "text": "Follow these rules and your audience retention will instantly double.", "words": []},
        ]
        self.niche = niche_registry.get_profile("tech")
        self.style = style_registry.get_style("bold_zoom")

    # =========================================================================
    # 1. HOOK ENGINE TESTS
    # =========================================================================
    def test_hook_candidate_generation_and_scoring(self):
        engine = HookEngine()
        candidates = engine.generate_candidates(self.sample_segments, video_duration=30.0)
        self.assertGreater(len(candidates), 0, "Hook engine should generate candidates")

        # Highest scored candidate should be chosen
        best_hook = engine.select_winning_hook(self.sample_segments, video_duration=30.0)
        self.assertIsNotNone(best_hook)
        self.assertIsInstance(best_hook, HookCandidate)
        self.assertGreaterEqual(best_hook.scores.final_score, 0.0)
        self.assertLessEqual(best_hook.scores.final_score, 100.0)
        self.assertIsNotNone(best_hook.retention_purpose)

    def test_hook_preamble_tightener(self):
        engine = HookEngine()
        raw_text = "So basically what happened is I was completely broke."
        tightened, cut = engine.tighten_preamble(raw_text)
        self.assertIn("completely broke", tightened.lower())
        self.assertTrue(len(cut) > 0, "Preamble filler should be identified and trimmed")

    def test_hook_penalizes_greetings(self):
        engine = HookEngine()
        greeting_text = "Hey guys, welcome back to my channel! Today we are talking about coding."
        scores = engine.score_text(greeting_text)
        self.assertGreater(scores.penalties, 0.0, "Greetings must be penalized")
        self.assertLess(scores.final_score, 60.0)

    # =========================================================================
    # 2. MOMENT ANALYZER TESTS
    # =========================================================================
    def test_moment_analyzer_beats_and_sentiment(self):
        analyzer = MomentAnalyzer()
        moments = analyzer.analyze_transcript(self.sample_segments, video_duration=30.0)
        self.assertGreater(len(moments), 0, "Should generate editorial moment beats")

        for m in moments:
            self.assertIsInstance(m, EditorialMoment)
            self.assertGreaterEqual(m.duration, 2.0, "Moments should have valid duration")
            self.assertIsInstance(m.sentiment, SentimentCategory)
            self.assertIsInstance(m.narrative_role, NarrativeRole)
            self.assertGreaterEqual(m.emotional_intensity, 0.0)
            self.assertLessEqual(m.emotional_intensity, 1.0)

    # =========================================================================
    # 3. VISUAL VARIETY ENGINE TESTS
    # =========================================================================
    def test_visual_variety_penalties(self):
        variety = VisualVarietyEngine()
        variety.record_placed_shot(
            shot_id="shot_1",
            shot_type=ShotType.WIDE,
            subject_category="person_talking",
            camera_movement="static",
            location="indoor",
        )

        # Score identical shot type immediately following
        penalty = variety.calculate_variety_penalty(
            candidate_shot_type=ShotType.WIDE,
            candidate_subject="person_talking",
            candidate_motion="static",
        )
        self.assertGreater(penalty, 0.2, "Repeating identical shot type & subject must incur penalty")

        # Score contrasting shot type (e.g. screen tech with push in)
        contrast_penalty = variety.calculate_variety_penalty(
            candidate_shot_type=ShotType.SCREEN,
            candidate_subject="screen_tech",
            candidate_motion="slow_push",
        )
        self.assertLess(contrast_penalty, penalty, "Contrasting shot should incur lower penalty")

    # =========================================================================
    # 4. CONTEXTUAL B-ROLL & INTENTIONAL A-ROLL
    # =========================================================================
    def test_low_confidence_broll_rejection_for_pure_aroll(self):
        broll_intel = BrollIntelligence()
        variety = VisualVarietyEngine()
        moment = EditorialMoment(
            moment_id="m_01",
            start_time=2.5,
            end_time=6.8,
            duration=4.3,
            text="Nobody told you that 87% of creators fail in their very first year.",
            semantic_topic="creator failure",
            entities=["creators"],
            action="failing",
            sentiment=SentimentCategory.NEGATIVE,
            emotional_intensity=0.85,
            narrative_role=NarrativeRole.CLAIM,
            visual_opportunity=0.8,
            pacing_requirement=PacingCategory.DEEP_EXPLANATION,
        )

        poor_asset = {
            "title": "Sunny tropical beach palm trees",
            "tags": "beach, vacation, sunny, relax, holiday",
            "category": "lifestyle",
            "file_path": "broll/beach.mp4",
        }

        score = broll_intel.score_candidate_asset(
            moment=moment,
            asset=poor_asset,
            target_duration=4.0,
            narrative_role=BrollNarrativeRole.ILLUSTRATE,
            variety_engine=variety,
        )
        self.assertLess(score.confidence, 0.65, "Irrelevant footage must fail confidence threshold (<0.65)")

        decision = broll_intel.evaluate_and_plan_shot(
            moment=moment,
            available_assets=[poor_asset],
            variety_engine=variety,
            is_first_moment=False,
        )
        self.assertIsNone(decision, "Low-confidence assets must be rejected to intentionally retain A-Roll")

    def test_contextual_broll_acceptance_with_narrative_role(self):
        broll_intel = BrollIntelligence()
        variety = VisualVarietyEngine()
        moment = EditorialMoment(
            moment_id="m_02",
            start_time=6.8,
            end_time=11.2,
            duration=4.4,
            text="We analyzed over 10 million videos to discover the secret formula.",
            semantic_topic="video data analytics research",
            entities=["10 million videos", "data"],
            action="analyzing data",
            sentiment=SentimentCategory.TECHNICAL,
            emotional_intensity=0.75,
            narrative_role=NarrativeRole.EXPLANATION,
            visual_opportunity=0.9,
            pacing_requirement=PacingCategory.DEEP_EXPLANATION,
        )

        good_asset = {
            "title": "Data dashboard showing analytics metrics charts",
            "tags": "data, analytics, charts, research, metrics, screen",
            "category": "tech",
            "file_path": "broll/analytics.mp4",
        }

        decision = broll_intel.evaluate_and_plan_shot(
            moment=moment,
            available_assets=[good_asset],
            variety_engine=variety,
            is_first_moment=False,
        )
        self.assertIsNotNone(decision, "Relevant footage should be accepted")
        self.assertGreaterEqual(decision.scores.confidence, 0.65)
        self.assertIn(decision.narrative_role, [
            BrollNarrativeRole.ILLUSTRATE,
            BrollNarrativeRole.REINFORCE,
            BrollNarrativeRole.EXPLAIN,
            BrollNarrativeRole.EMPHASIZE,
        ])
        # Opening face safety: B-roll should start after initial face establishment (>= 1.2s)
        self.assertGreaterEqual(decision.start_time, 1.2)

    # =========================================================================
    # 5. SOUND DESIGNER & DENSITY CONTROL
    # =========================================================================
    def test_sfx_sparsity_and_density_limits(self):
        designer = SoundDesigner()
        moments = [
            EditorialMoment("m1", 0.0, 3.0, 3.0, "intro", sentiment=SentimentCategory.NEUTRAL, narrative_role=NarrativeRole.HOOK),
            EditorialMoment("m2", 3.0, 6.0, 3.0, "statistic 87%", sentiment=SentimentCategory.NEGATIVE, emotional_intensity=0.9, narrative_role=NarrativeRole.STATISTIC),
            EditorialMoment("m3", 6.0, 9.0, 3.0, "reveal secret formula", sentiment=SentimentCategory.POSITIVE, emotional_intensity=0.85, narrative_role=NarrativeRole.REVEAL),
            EditorialMoment("m4", 9.0, 12.0, 3.0, "shock fail", sentiment=SentimentCategory.TENSION, emotional_intensity=0.95, narrative_role=NarrativeRole.CLAIM),
            EditorialMoment("m5", 12.0, 15.0, 3.0, "step 1 framework", sentiment=SentimentCategory.TECHNICAL, narrative_role=NarrativeRole.EXPLANATION),
            EditorialMoment("m6", 15.0, 18.0, 3.0, "step 2 rules", sentiment=SentimentCategory.NEUTRAL, narrative_role=NarrativeRole.EXPLANATION),
        ]

        cues = designer.design_soundscape(
            moments=moments,
            broll_shots=[],
            captions=[],
            camera_moves=[],
            video_duration=18.0,
        )
        # In an 18s video, density limit (<=6/min = ~1.8 cues) caps to at most 2 cues
        self.assertLessEqual(len(cues), 2, "SFX sparsity control must cap density to prevent acoustic clutter")

        # Spacing check: consecutive SFX must be spaced >= 3.0s apart
        for i in range(len(cues) - 1):
            gap = cues[i+1].timestamp - cues[i].timestamp
            self.assertGreaterEqual(gap, 2.9, f"SFX cues must have >=3.0s spacing, found {gap:.2f}s")

    # =========================================================================
    # 6. QUALITY GATE & AUTO-REPAIRS
    # =========================================================================
    def test_quality_gate_audit_and_auto_repair(self):
        gate = EditorialQualityGate()
        hook = HookCandidate(
            candidate_id="hook_01",
            start_time=0.0,
            end_time=3.0,
            duration=3.0,
            raw_text="So basically what happened is I was completely broke.",
            tightened_text="I was completely broke.",
            retention_purpose="CURIOSITY_GAP",
            retention_reason="Compelling personal stakes",
            scores=HookScoreBreakdown(
                curiosity_gap=90.0,
                emotional_intensity=85.0,
                specificity=80.0,
                standalone_context=85.0,
                strong_claim=75.0,
                surprise_interrupt=80.0,
                narrative_importance=85.0,
                clarity=90.0,
                penalties=0.0,
                final_score=88.0,
            ),
            is_opening=True,
        )

        # Deliberately construct an edit with a cutaway starting before 1.2s (violates opening face rule)
        early_decision = ContextualBrollDecision(
            shot_id="shot_1",
            moment_id="m_01",
            start_time=0.5,
            end_time=2.5,
            duration=2.0,
            narrative_role=BrollNarrativeRole.ILLUSTRATE,
            reason="Illustrate being broke",
            search_query="empty wallet",
            emotional_intent="Serious",
            pacing_category=PacingCategory.HIGH_ENERGY,
            scores=BrollCandidateScore(confidence=0.85, final_score=0.85),
            asset_path="broll/wallet.mp4",
        )

        spec = EditorialEditSpecification(
            spec_id="plan_test_audit",
            title="Audit Test",
            total_duration=30.0,
            hook=hook,
            moments=[
                EditorialMoment("m_01", 0.0, 3.0, 3.0, "broke", sentiment=SentimentCategory.NEGATIVE, emotional_intensity=0.8, narrative_role=NarrativeRole.HOOK),
                EditorialMoment("m_02", 3.0, 30.0, 27.0, "payoff", sentiment=SentimentCategory.POSITIVE, emotional_intensity=0.7, narrative_role=NarrativeRole.PAYOFF),
            ],
            broll_shots=[early_decision],
            captions=[],
            camera_moves=[],
            sfx_cues=[],
            energy_curve=[],
        )

        repaired_spec, report = gate.audit_and_repair(spec)

        self.assertIsInstance(report, QualityAuditReport)
        self.assertGreaterEqual(report.overall_score, 0.70)
        # Quality Gate must report the violation, but never retime an approved shot.
        self.assertEqual(repaired_spec.broll_shots[0].start_time, 0.5)
        opening_check = next(c for c in report.checks if c.name == "opening_face_rule")
        self.assertFalse(opening_check.passed)
        self.assertEqual(opening_check.severity, "error")

    # =========================================================================
    # 7. FULL PIPELINE & DIFFUSION STUDIO EXECUTION
    # =========================================================================
    def test_full_pipeline_to_diffusion_studio(self):
        pipeline = EditorialIntelligencePipeline()
        source_media = {
            "path": "inputs/test_speech.mp4",
            "duration": 30.0,
            "title": "test_speech.mp4",
            "width": 1080,
            "height": 1920,
            "fps": 30,
        }

        sample_assets = [
            {"title": "Money bills cash wallet empty", "tags": "money, cash, broke, wallet", "category": "finance", "file_path": "broll/money.mp4"},
            {"title": "Video analytics dashboard charts", "tags": "data, charts, metrics", "category": "tech", "file_path": "broll/data.mp4"},
        ]

        spec, quality_report = pipeline.process(
            source_media=source_media,
            transcript_segments=self.sample_segments,
            video_duration=30.0,
            available_broll_assets=sample_assets,
            niche_profile=self.niche,
            style_profile=self.style,
        )

        self.assertIsNotNone(spec.hook)
        self.assertGreater(len(spec.moments), 0)
        self.assertGreaterEqual(quality_report.overall_score, 0.70)

        # Create EditPlan containing editorial spec and quality report
        edit_plan = EditPlan(
            plan_id="plan_test_pipeline",
            title=f"AI Edit: {spec.hook.tightened_text[:30]}",
            target_duration=30.0,
            source_media=source_media,
            clip_interval={"in_point": 0.0, "out_point": 30.0},
            niche=self.niche.to_dict(),
            style=self.style.to_dict(),
            shots=[
                {
                    "shot_id": s.shot_id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                    "category": s.subject_category,
                    "narrative_role": s.narrative_role.value,
                    "emotional_intent": s.emotional_intent,
                    "confidence": s.scores.confidence,
                    "pacing_category": s.pacing_category.value,
                    "asset_path": s.asset_path,
                }
                for s in spec.broll_shots
            ],
            text_overlays=[],
            subtitles=[],
            zooms=[],
            audio_cues={
                "sfx": [
                    {
                        "id": cue.cue_id,
                        "time": cue.timestamp,
                        "duration": cue.duration,
                        "file": cue.sound_file,
                        "volume": cue.volume,
                        "event_type": cue.event_type.value,
                        "justification": cue.reason,
                    }
                    for cue in spec.sfx_cues
                ]
            },
            editorial_spec=spec.to_dict(),
            quality_report=quality_report.to_dict(),
        )

        # Render with DiffusionAdapter
        adapter = DiffusionAdapter()
        comp = adapter.create_project(edit_plan, base_asset_url="http://127.0.0.1:8000/assets")

        # Validate Diffusion Studio Schema
        self.assertEqual(comp.get("version"), "4.0.0")
        self.assertEqual(comp.get("engine"), "diffusion")
        self.assertIn("composition", comp)
        self.assertEqual(len(comp["composition"]["layers"]), 7)

        # Validate that composition metadata contains editorial spec & quality report
        metadata = comp["composition"]["metadata"]
        self.assertIn("editorial_spec", metadata)
        self.assertIn("quality_report", metadata)
        self.assertEqual(metadata["editorial_spec"]["hook"]["tightened_text"], spec.hook.tightened_text)

        # Validate Layer 7 (SFX) has no uncurated stinger spam
        layer_sfx = next((l for l in comp["composition"]["layers"] if l["id"] == "layer_audio_sfx"), None)
        self.assertIsNotNone(layer_sfx)
        # SFX clips must be <= 3 for a 30s video
        self.assertLessEqual(len(layer_sfx["clips"]), 3)

        # Validate Bidirectional Conversion to OpenReel Schema 1.2.0
        openreel = adapter.to_openreel_project(comp)
        self.assertEqual(openreel.get("version"), "1.2.0")
        self.assertIn("project", openreel)
        self.assertIn("metadata", openreel["project"])
        self.assertIn("editorial_spec", openreel["project"]["metadata"])

    # =========================================================================
    # 8. FEEDBACK LEARNING BRIDGE
    # =========================================================================
    def test_feedback_learning_bridge(self):
        bridge = EditorialFeedbackBridge()
        bridge.record_broll_modification(
            job_id="job_test_123",
            shot_id="shot_1",
            action="KEEP",
            prompt="data analytics chart",
            asset_title="Analytics dashboard",
        )
        bridge.record_broll_modification(
            job_id="job_test_123",
            shot_id="shot_2",
            action="REMOVE",
            prompt="stock finance chart",
            feedback_text="Stay on speaker face here for emotional delivery",
        )
        bridge.record_sfx_modification(
            job_id="job_test_123",
            cue_id="cue_1",
            action="KEEP",
            sound_name="whoosh.mp3",
        )
        bridge.record_hook_override(
            job_id="job_test_123",
            ai_hook="I was completely broke.",
            user_hook="Here is how I lost everything.",
        )


if __name__ == "__main__":
    unittest.main()
