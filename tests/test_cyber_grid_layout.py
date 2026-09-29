"""Tests for CapCut Before & After Cyber Grid Layout and Style Engine."""

import pytest
from pathlib import Path
from ai_broll_autopilot.services.cyber_grid_engine import CyberGridEngine
from ai_broll_autopilot.services.subtitle_engine import SubtitleEngine
from ai_broll_autopilot.services.timeline import TimelineEngine
from ai_broll_autopilot.campaigns.registry import campaign_registry


def test_cyber_grid_engine_asset_generation(tmp_path):
    """Verify procedural generation of cyber grid backdrop and rounded masks."""
    engine = CyberGridEngine(templates_dir=tmp_path)
    bg_p, mb_p, ma_p = engine.ensure_assets()

    assert bg_p.exists()
    assert mb_p.exists()
    assert ma_p.exists()
    assert bg_p.stat().st_size > 1000
    assert mb_p.stat().st_size > 100
    assert ma_p.stat().st_size > 100


def test_cyber_grid_subtitles_layout_and_styling(tmp_path):
    """Verify ASS subtitles generated for cyber grid are centered inside AFTER card."""
    engine = SubtitleEngine()
    transcript = [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Check out this crazy edit",
            "words": [
                {"word": "Check", "start": 0.0, "end": 0.6},
                {"word": "out", "start": 0.6, "end": 1.2},
                {"word": "this", "start": 1.2, "end": 1.8},
                {"word": "crazy", "start": 1.8, "end": 2.2},
                {"word": "edit", "start": 2.2, "end": 2.5},
            ]
        }
    ]

    ass_path = tmp_path / "cyber_subs.ass"
    engine.generate_ass_file(
        transcript,
        ass_path,
        style_preset="capcut_cyber",
        layout_mode="before_after_cyber_grid"
    )

    assert ass_path.exists()
    content = ass_path.read_text(encoding="utf-8")

    # MarginL: 440, MarginR: 40, MarginV: 780 for AFTER card window
    assert "440,40,780" in content
    # CapCut cyber neon cyan and golden amber colors in ASS
    assert "&H00FFFF00&" in content or "&H0000A5FF&" in content


def test_cyber_grid_timeline_filtergraph():
    """Verify TimelineEngine builds dual-card compositing graph with cyber grid backdrop."""
    timeline = TimelineEngine()

    shots = [
        {
            "asset_path": "sample_broll.mp4",
            "start_time": 1.0,
            "end_time": 2.5,
            "speed": 1.0
        }
    ]

    filtergraph, v_out, a_out = timeline.build_filtergraph(
        shots=shots,
        layout_mode="before_after_cyber_grid",
        cyber_grid_backdrop_idx=2,
        cyber_grid_mask_before_idx=3,
        cyber_grid_mask_after_idx=4,
    )

    # Must contain split for before/after, scaling, alphamerge, and backdrop overlay
    assert "split=2[v_raw][v_proc]" in filtergraph
    assert "scale=352:600" in filtergraph
    assert "scale=600*1.40:1060*1.40" in filtergraph
    assert "alphamerge" in filtergraph
    assert "overlay=64:550" in filtergraph
    assert "overlay=440:320" in filtergraph
    assert "cyber_comp" in filtergraph


def test_capcut_podcast_campaign_registered():
    """Verify capcut_podcast_pro campaign is registered and accessible."""
    campaign = campaign_registry.get_campaign("capcut_podcast_pro")
    assert campaign is not None
    assert campaign.id == "capcut_podcast_pro"
    assert campaign.layout_mode == "before_after_cyber_grid"
    assert campaign.subtitle_style == "capcut_cyber"

    # Alias check
    alias_campaign = campaign_registry.get_campaign("capcut_cyber")
    assert alias_campaign.id == "capcut_podcast_pro"
