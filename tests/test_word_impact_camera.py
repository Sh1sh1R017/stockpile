from pathlib import Path

from ai_broll_autopilot.services.caption_motion import apply_caption_motion
from ai_broll_autopilot.services.razor_caption.caption_event import CaptionEvent, EmphasisLevel
from ai_broll_autopilot.services.razor_caption.engine import RazorCaptionEngine
from ai_broll_autopilot.services.razor_caption.state_machine import CaptionStateMachine


def test_chaos_impact_selects_camera_hit_recipe():
    events = [
        CaptionEvent(
            word="CHAOS",
            start_time=1.0,
            end_time=1.8,
            semantic_type="chaos",
            emphasis=EmphasisLevel.HOOK,
        )
    ]
    CaptionStateMachine().wire(events)
    ev = events[0]

    assert ev.motion_recipe == "kinetic:word-impact-camera"
    assert ev.video_effect == "impact-camera-punch"
    assert ev.motion_params["impact_scale"] >= 1.7
    assert ev.motion_params["camera_punch"] > 0.7
    assert ev.enter_animation.value == "overshoot"
    assert ev.emphasis_scale >= 1.5


def test_impact_auto_maps_chaos_to_camera_recipe():
    result = apply_caption_motion(
        [{"text": "CHAOS", "semantic_type": "chaos"}],
        "impact-auto",
    )
    assert result[0]["motionProfile"] == "word-impact-camera"
    assert result[0]["motionRecipe"] == "kinetic:word-impact-camera"
    assert result[0]["motionParams"]["start_scale"] == 0.18


def test_camera_impact_is_real_ass_animation(tmp_path: Path):
    ass = tmp_path / "captions.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )
    event = CaptionEvent(
        word="CHAOS",
        start_time=1.0,
        end_time=1.8,
        semantic_type="chaos",
        emphasis=EmphasisLevel.HOOK,
    )
    CaptionStateMachine().wire([event])
    RazorCaptionEngine._append_camera_impact_events(ass, [event])
    rendered = ass.read_text(encoding="utf-8")

    assert "CHAOS" in rendered
    assert r"\fscx18\fscy18" in rendered
    assert r"\fscx172\fscy172" in rendered
    assert r"\pos(540,960)" in rendered
    assert r"\frz-4" in rendered
