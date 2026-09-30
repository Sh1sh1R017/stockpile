from ai_broll_autopilot.services.caption_motion import apply_caption_motion
from ai_broll_autopilot.services.razor_caption.caption_event import CaptionEvent, EmphasisLevel
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
