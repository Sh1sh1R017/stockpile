"""Renderer API contract regressions."""

import inspect

from ai_broll_autopilot.services.renderer import Renderer


def test_renderer_accepts_orchestrator_clip_arguments():
    params = inspect.signature(Renderer.render).parameters
    assert "source_start_time" in params
    assert "render_duration" in params
