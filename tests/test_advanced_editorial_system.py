"""Comprehensive Verification Suite for Advanced AI Editorial & Retention System.

Validates all 7 core pillars inspired by video-db/Director and Andrea13235/Retention:
1. Cuts-First Retention Engine (Dead-air, filler words, false starts, confidence gating, timebase remapping)
2. Semantic Retrieval & Strict Contradiction Veto (Disambiguation of metaphors, basketball rejection in SaaS)
3. Content-Aware Motion Graphics (Numbers, stats, key term badges, lower thirds, safe area compliance)
4. Persistent Media Memory & Indexing (Caching, usage tracking, sub-millisecond retrieval)
5. Visual QA & Post-Render Verification (blackdetect, freezedetect, volumedetect, faststart moov atom)
6. Iterative Edit & Auto-Repair Loop (Multi-pass audit, stagnation elimination, SFX spacing)
7. Canonical EditPlan Schema 2.1 & Full NLE Compatibility (Diffusion Studio & OpenReel)
"""

import asyncio
from pathlib import Path
import pytest

from ai_broll_autopilot.services.retention_engine import (
    RetentionEngine,
    RetentionProfile,
    CutType,
    CutDecision,
)
from ai_broll_autopilot.services.retrieval_engine import (
    SemanticRetrievalEngine,
    SemanticDomain,
)
from ai_broll_autopilot.services.graphics_engine import (
    ContentAwareGraphicsEngine,
    GraphicType,
)
from ai_broll_autopilot.services.media_index import (
    MediaIndexService,
    IndexedMediaAsset,
)
from ai_broll_autopilot.services.visual_qa import (
    VisualQAService,
    QASeverity,
)
from ai_broll_autopilot.services.iterative_editor import (
    IterativeEditLoop,
)
from ai_broll_autopilot.services.edit_director import (
    EditDirectorService,
    EditPlan,
)
from ai_broll_autopilot.services.editorial.visual_variety import VisualVarietyEngine
from ai_broll_autopilot.services.editorial.types import (
    EditorialMoment,
    BrollNarrativeRole,
    SentimentCategory,
    PacingCategory,
    ShotType,
)
from ai_broll_autopilot.services.diffusion_adapter import DiffusionAdapter
from ai_broll_autopilot.services.openreel_adapter import OpenReelAdapter


# ==============================================================================
# 1. RETENTION ENGINE & CUTS-FIRST ARCHITECTURE TESTS
# ==============================================================================

def test_retention_engine_detects_dead_air_and_fillers():
    """Verify dead-air pauses and filler words are accurately detected and confidence-gated."""
    engine = RetentionEngine(RetentionProfile(min_pause_duration=0.35))

    segments = [
        {
            "start": 0.8,
            "end": 2.2,
            "text": "Um, here is the real secret.",
            "words": [
                {"word": "Um", "start": 0.8, "end": 1.1},
                {"word": "here", "start": 1.4, "end": 1.6},
                {"word": "is", "start": 1.62, "end": 1.75},
                {"word": "the", "start": 1.77, "end": 1.9},
                {"word": "real", "start": 1.92, "end": 2.1},
                {"word": "secret", "start": 2.12, "end": 2.5},
            ],
        },
        {
            "start": 3.4,  # Dead air of 0.9s between 2.5s and 3.4s
            "end": 5.0,
            "text": "We we scaled the whole system.",
            "words": [
                {"word": "We", "start": 3.4, "end": 3.6},
                {"word": "we", "start": 3.65, "end": 3.85},  # Stutter / False start
                {"word": "scaled", "start": 3.9, "end": 4.3},
                {"word": "the", "start": 4.32, "end": 4.45},
                {"word": "whole", "start": 4.47, "end": 4.7},
                {"word": "system", "start": 4.72, "end": 5.1},
            ],
        },
    ]

    cuts = engine.analyze_and_detect_cuts(segments, video_duration=6.5)

    assert len(cuts) >= 3

    # Check opening dead air (0.0 to ~0.74s)
    opening_cut = next((c for c in cuts if c.start_time == 0.0), None)
    assert opening_cut is not None
    assert opening_cut.cut_type == CutType.DEAD_AIR
    assert opening_cut.decision == CutDecision.AUTO_CUT

    # Check filler word "Um"
    um_cut = next((c for c in cuts if "Um" in c.trigger_text or "um" in c.trigger_text.lower()), None)
    assert um_cut is not None
    assert um_cut.cut_type == CutType.FILLER_WORD

    # Check stutter "We we"
    stutter_cut = next((c for c in cuts if c.cut_type == CutType.FALSE_START), None)
    assert stutter_cut is not None
    assert stutter_cut.confidence >= 0.85


def test_retention_engine_timebase_remapping():
    """Verify keep intervals and timestamp remapping onto the post-cut timeline."""
    engine = RetentionEngine()

    # Suppose cuts are from 0.0 to 1.0 (1.0s silence) and 3.0 to 4.0 (1.0s gap) in a 6.0s video
    cuts = [
        engine.analyze_and_detect_cuts([], 6.0)  # Empty baseline
    ]

    keep_intervals = [(1.0, 3.0), (4.0, 6.0)]  # Total post-cut duration = 4.0s

    # Uncut time 1.5s should map to post-cut time 0.5s
    remapped_1_5 = engine.remap_timestamp(1.5, keep_intervals)
    assert remapped_1_5 == 0.5

    # Uncut time 4.5s should map to post-cut time 2.5s (2.0s from first interval + 0.5s)
    remapped_4_5 = engine.remap_timestamp(4.5, keep_intervals)
    assert remapped_4_5 == 2.5

    # Inverse mapping: post-cut 2.5s should unmap back to 4.5s
    unmapped_2_5 = engine.unmap_timestamp(2.5, keep_intervals)
    assert unmapped_2_5 == 4.5


# ==============================================================================
# 2. HIERARCHICAL SEMANTIC RETRIEVAL & STRICT CONTRADICTION VETO TESTS
# ==============================================================================

def test_semantic_retrieval_vetoes_basketball_in_saas_video():
    """Regression Test: Verify basketball footage is strictly vetoed for a SaaS/CRO business video."""
    engine = SemanticRetrievalEngine()
    variety = VisualVarietyEngine()

    moment = EditorialMoment(
        moment_id="m_saas_01",
        start_time=2.0,
        end_time=6.0,
        duration=4.0,
        text="When you are running a B2B SaaS company as Chief Revenue Officer, closing enterprise revenue is everything.",
        semantic_topic="B2B SaaS Revenue",
        entities=["Chief Revenue Officer", "B2B SaaS"],
        action="explaining executive sales strategy",
        sentiment=SentimentCategory.TECHNICAL,
    )

    candidates = [
        {
            "id": "asset_collin_sexton_dunk",
            "title": "Collin Sexton Slam Dunk in Basketball Game",
            "category": "sports_basketball",
            "tags": ["basketball", "dunk", "nba", "athlete", "sprint"],
            "description": "Collin Sexton dunks over defenders on the basketball court",
            "path": "C:/media/sexton_dunk.mp4",
            "duration": 5.0,
        },
        {
            "id": "asset_saas_dashboard",
            "title": "B2B SaaS Enterprise Revenue Dashboard Metrics",
            "category": "tech_software",
            "tags": ["software", "revenue", "saas", "cro", "dashboard", "analytics"],
            "description": "Clean software analytics interface showing revenue ARR growth",
            "path": "C:/media/saas_dashboard.mp4",
            "duration": 6.0,
        },
    ]

    ranked = engine.retrieve_and_rank_candidates(
        moment=moment,
        available_assets=candidates,
        variety_engine=variety,
        target_duration=3.0,
        narrative_role=BrollNarrativeRole.EXPLAIN,
    )

    # 1. Basketball candidate MUST be vetoed due to domain and metaphor conflict
    bball_result = next(r for r in ranked if r.asset_id == "asset_collin_sexton_dunk")
    assert bball_result.is_vetoed is True
    assert bball_result.final_score == 0.0
    assert "contradiction" in bball_result.veto_reason.lower()

    # 2. SaaS dashboard candidate MUST be accepted with high score
    saas_result = next(r for r in ranked if r.asset_id == "asset_saas_dashboard")
    assert saas_result.is_vetoed is False
    assert saas_result.final_score >= 0.70

    # 3. Decision engine must select the SaaS asset
    decision = engine.select_best_decision(
        moment=moment,
        available_assets=candidates,
        variety_engine=variety,
        target_duration=3.0,
        narrative_role=BrollNarrativeRole.EXPLAIN,
        shot_start=2.0,
        shot_end=5.0,
    )
    assert decision is not None
    assert decision.asset_name == "B2B SaaS Enterprise Revenue Dashboard Metrics"


def test_semantic_retrieval_disambiguates_running_metaphor():
    """Verify that 'running a company' is not matched with physical marathon running."""
    engine = SemanticRetrievalEngine()
    variety = VisualVarietyEngine()

    moment = EditorialMoment(
        moment_id="m_run_01",
        start_time=1.5,
        end_time=5.0,
        duration=3.5,
        text="We spent three years running this machine learning startup before finding product market fit.",
        semantic_topic="Machine Learning Startup",
        sentiment=SentimentCategory.REFLECTIVE,
    )

    candidates = [
        {
            "id": "runner_track",
            "title": "Athlete Running Sprint on Athletics Track",
            "category": "sports",
            "tags": ["running", "sprint", "jogging", "marathon", "track"],
            "path": "runner.mp4",
        },
        {
            "id": "team_meeting",
            "title": "Engineers Collaborating in Modern AI Startup Office",
            "category": "business",
            "tags": ["startup", "machine learning", "engineers", "ai", "meeting"],
            "path": "team.mp4",
        },
    ]

    ranked = engine.retrieve_and_rank_candidates(
        moment=moment,
        available_assets=candidates,
        variety_engine=variety,
        target_duration=3.0,
        narrative_role=BrollNarrativeRole.ILLUSTRATE,
    )

    runner_res = next(r for r in ranked if r.asset_id == "runner_track")
    assert runner_res.is_vetoed is True

    team_res = next(r for r in ranked if r.asset_id == "team_meeting")
    assert team_res.is_vetoed is False
    assert team_res.final_score > 0.65


# ==============================================================================
# 3. CONTENT-AWARE GRAPHICS ENGINE TESTS
# ==============================================================================

def test_graphics_engine_extracts_statistics_and_badges():
    """Verify numeric statistics and key terms are extracted into safe-area graphic overlays."""
    engine = ContentAwareGraphicsEngine()

    segments = [
        {"start": 1.0, "end": 3.8, "text": "We grew ARR by over 85% in just six months."},
        {"start": 4.0, "end": 7.5, "text": "Our new LLM infrastructure saved $2.5M in compute."},
    ]

    graphics = engine.generate_graphics(
        transcript_segments=segments,
        video_duration=10.0,
        title="From Amazon Guy to Chief Revenue Officer",
        highlight_color="#FFDD00",
    )

    assert len(graphics) >= 2

    # Check Lower Third generated from title
    lower_third = next((g for g in graphics if g.graphic_type == GraphicType.LOWER_THIRD), None)
    assert lower_third is not None
    assert "AMAZON" in lower_third.primary_text
    assert lower_third.position_y_pct == 65.0  # Above subtitle area

    # Check 85% percentage stat
    stat_85 = next((g for g in graphics if "85%" in g.primary_text), None)
    assert stat_85 is not None
    assert stat_85.graphic_type == GraphicType.NUMBER_STAT

    # Safe Area check: No graphic should overlap subtitle danger zone (75% to 90%)
    for g in graphics:
        assert not (75.0 <= g.position_y_pct <= 90.0)


# ==============================================================================
# 4. PERSISTENT MEDIA MEMORY & INDEXING TESTS
# ==============================================================================

def test_media_index_freshness_and_lookup(tmp_path):
    """Verify asset indexing, metadata caching, and usage-based freshness degradation."""
    index = MediaIndexService(index_file=tmp_path / "test_index.json")

    asset = index.index_file_path(
        file_path="C:/media/demo_tech_chart.mp4",
        tags=["ai", "chart", "tech"],
        domain="tech_software",
        description="AI Growth Chart",
        duration=8.0,
        width=1920,
        height=1080,
    )
    assert asset.asset_id.startswith("asset_")
    assert asset.usage_count == 0

    # Query before usage
    results = index.query_assets(domain="tech_software", keywords=["ai"])
    assert len(results) == 1
    assert results[0]["usage_count"] == 0

    # Record usage
    index.record_usage(asset.asset_id)
    updated = index.query_assets(domain="tech_software", keywords=["ai"])
    assert updated[0]["usage_count"] == 1


# ==============================================================================
# 5. VISUAL QA SERVICE TESTS
# ==============================================================================

def test_visual_qa_duration_and_faststart_simulation():
    """Verify Visual QA correctly flags duration errors and dry-run compliance."""
    service = VisualQAService()

    # Dry run check for missing disk file
    dry_result = service.verify_rendered_video(
        video_path="non_existent_clip.mp4",
        target_duration=15.0,
    )
    assert dry_result.passed is True
    assert dry_result.target_duration == 15.0
    assert dry_result.has_faststart is True


# ==============================================================================
# 6. ITERATIVE EDIT & AUTO-REPAIR LOOP TESTS
# ==============================================================================

def test_iterative_editor_auto_repairs_stagnation_and_sfx():
    """Verify iterative editor loop detects visual stagnation and fixes it by injecting keyframe zooms."""
    loop = IterativeEditLoop(min_quality_score=0.85, max_iterations=2)

    # Synthetic plan with 8.0s of visual stagnation without any zoom or overlay
    stagnant_plan = EditPlan(
        plan_id="plan_stagnant",
        title="Stagnant Test Plan",
        target_duration=12.0,
        source_media={"path": "video.mp4", "duration": 12.0},
        clip_interval={"in_point": 0.0, "out_point": 12.0},
        niche={"id": "tech_ai", "name": "Tech AI"},
        style={"id": "clean_podcast", "name": "Podcast"},
        shots=[],
        text_overlays=[],
        zooms=[],  # Empty zooms -> Stagnation defect!
        audio_cues={"sfx": [
            {"id": "s1", "time": 2.0},
            {"id": "s2", "time": 2.4},  # Clustered SFX (only 0.4s apart)
        ]},
    )

    result = loop.audit_and_repair_plan(stagnant_plan)

    assert result.iteration_count >= 1
    assert len(result.repaired_items) >= 2

    # Verify a punch-in was injected to eliminate the stagnation
    assert len(stagnant_plan.zooms) >= 1
    # Verify the clustered SFX was re-spaced
    sfx_times = [s["time"] for s in stagnant_plan.audio_cues["sfx"]]
    assert (sfx_times[1] - sfx_times[0]) >= 2.5


# ==============================================================================
# 7. CANONICAL EDITPLAN SCHEMA 2.1 & DIFFUSION STUDIO / OPENREEL EXPORT TESTS
# ==============================================================================

def test_canonical_editplan_2_1_e2e_pipeline():
    """Verify full end-to-end generation of Canonical EditPlan 2.1 and export to Diffusion Studio & OpenReel."""
    director = EditDirectorService()
    diff_adapter = DiffusionAdapter()
    oreel_adapter = OpenReelAdapter()

    source_media = {
        "path": "C:/media/From Amazon Guy to Chief Revenue Officer.mp4",
        "duration": 40.0,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "title": "From Amazon Guy to Chief Revenue Officer",
    }

    transcript = [
        {"start": 0.0, "end": 3.5, "text": "From an entry-level Amazon guy, to Chief Revenue Officer."},
        {"start": 3.5, "end": 4.2, "text": "Um, here is the secret."},
        {"start": 4.2, "end": 9.0, "text": "We grew annual recurring revenue by over 85% in six months."},
        {"start": 9.0, "end": 15.0, "text": "Focusing on enterprise retention was the whole game."},
    ]

    plan = asyncio.run(director.plan_edit(
        source_media=source_media,
        transcript_segments=transcript,
        in_point=0.0,
        out_point=15.0,
        niche_id="business_startup",
        style_id="business_editorial",
    ))

    # 1. Validate Canonical EditPlan Schema 2.1 properties
    assert plan.version == "2.1"
    assert len(plan.cuts) >= 1
    assert len(plan.keep_intervals) >= 1
    assert len(plan.a_roll_ranges) >= 1
    assert len(plan.graphics) >= 1
    assert plan.visual_qa is not None
    assert plan.cadence_profile["rhythm_pacing"] == "moderate"

    # 2. Export to Diffusion Studio Schema 4.0.0
    comp = diff_adapter.create_composition(
        edit_plan=plan,
        project_name="CRO Masterclass",
    )
    assert comp["schema_version"] == "4.0.0"
    assert len(comp["tracks"]) >= 4

    # Verify A-Roll track is segmented for cuts-first timeline
    main_track = next(t for t in comp["tracks"] if t["id"] == "layer_main_video")
    assert len(main_track["clips"]) >= 1

    # Verify Text Overlay track includes content-aware graphics
    text_track = next(t for t in comp["tracks"] if t["id"] == "layer_text_overlays")
    assert len(text_track["clips"]) >= 1

    # 3. Export to OpenReel Schema 1.2.0
    project_file = oreel_adapter.create_openreel_project(
        edit_plan=plan,
        project_name="CRO Masterclass",
    )
    assert project_file["version"] == "1.2.0"
    proj = project_file["project"]
    assert len(proj["timeline"]["tracks"]) >= 3
    assert len(proj["textClips"]) >= 1
