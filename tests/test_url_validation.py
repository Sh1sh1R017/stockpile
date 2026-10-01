"""Regression tests for server-side external URL validation."""

import pytest

from ai_broll_autopilot.api.path_safety import validate_external_url


def test_youtube_allowlist_accepts_supported_hosts():
    assert validate_external_url("https://www.youtube.com/watch?v=abc", allowed_hosts={"youtube.com", "youtu.be"}) == "https://www.youtube.com/watch?v=abc"
    assert validate_external_url("https://youtu.be/abc", allowed_hosts={"youtube.com", "youtu.be"}) == "https://youtu.be/abc"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=abc",
        "https://example.com/video.mp4",
        "https://127.0.0.1/video.mp4",
        "https://192.168.1.10/video.mp4",
        "file:///etc/passwd",
    ],
)
def test_external_url_validation_rejects_unsafe_urls(url: str):
    with pytest.raises(ValueError):
        validate_external_url(url, allowed_hosts={"youtube.com", "youtu.be"})
