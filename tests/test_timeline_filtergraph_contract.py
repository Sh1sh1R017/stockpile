"""Regression tests for deterministic FFmpeg filtergraph contracts."""

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.timeline import TimelineEngine


def test_broll_input_index_survives_filtered_non_asset_shots():
    graph, _, _ = TimelineEngine().build_filtergraph(
        shots=[
            {"shot_id": "placeholder", "start_time": 1.0, "end_time": 1.8},
            {
                "shot_id": "real",
                "_input_idx": 2,
                "asset_path": "real.mp4",
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
                "transition": {"type_in": "cut", "duration_in": 0.0},
            },
        ],
    )
    assert "[2:v]" in graph
    assert "[1:v]" not in graph


def test_reference_mask_uses_only_real_broll_input_indices():
    graph, _, _ = TimelineEngine().build_filtergraph(
        shots=[
            {"shot_id": "placeholder"},
            {
                "shot_id": "real",
                "_input_idx": 2,
                "asset_path": "real.mp4",
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
            },
        ],
        reference_style=True,
        reference_card_mask_idx=5,
        output_duration=10.0,
    )
    assert "split=2[ref_mask_0][ref_mask_2]" in graph
    assert "[ref_mask_1]" not in graph


def test_zero_duration_slide_is_rendered_as_a_cut_not_a_division_by_zero():
    graph, _, _ = TimelineEngine().build_filtergraph(
        shots=[
            {
                "asset_path": "real.mp4",
                "_input_idx": 1,
                "start_time": 2.0,
                "end_time": 3.2,
                "duration": 1.2,
                "transition": {"type_in": "slide_left", "duration_in": 0.0},
            }
        ],
    )
    assert "type_in" not in graph
    assert "/0.00" not in graph
    assert "enable='between(t,2.00,3.20)'" in graph


def test_drawtext_escapes_special_characters_and_windows_font_path(monkeypatch):
    monkeypatch.setattr(Config, "FONT_PATH", r"C:\Fonts\Stockpile:Bold.ttf")
    graph, _, _ = TimelineEngine().build_filtergraph(
        shots=[],
        behind_subject_text={
            "text": r"50%: don't break, please \ now",
            "start_time": 0.5,
            "duration": 1.0,
        },
    )
    assert "drawtext=" in graph
    assert "\:" in graph
    assert "\%" in graph
    assert "\," in graph
    assert "fontfile='C:\\Fonts\\Stockpile\:Bold.ttf'" in graph
