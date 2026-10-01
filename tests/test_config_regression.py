"""Regression coverage for environment parsing in the legacy configuration loader."""

from src.utils.config import load_config


def test_fractional_max_clip_duration_is_supported(monkeypatch):
    monkeypatch.setenv("MAX_CLIP_DURATION_SECONDS", "1.8")
    config = load_config()
    assert config["max_clip_duration_seconds"] == 1.8
