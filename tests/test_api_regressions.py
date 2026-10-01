from __future__ import annotations

from pathlib import Path

import pytest

from ai_broll_autopilot.api.app import JobSettingsRequest, _safe_sfx_path
from ai_broll_autopilot.services.subtitle_engine import SubtitleEngine


def test_job_settings_accept_full_caption_editor_contract() -> None:
    req = JobSettingsRequest(
        subtitles_enabled=True,
        subtitle_style="hormozi",
        subtitle_position="bottom",
        subtitle_y_percent=84,
        preset="hormozi",
        words_per_beat=3,
        caption_motion="pop",
        custom_colors={"main": "#FFFFFF", "second": "#FFE600", "third": "#00FF66"},
        enable_emojis=True,
        subtitles_behind_subject=False,
        bgm_track_id="none",
        bgm_volume=0.16,
        bgm_ducking=True,
        hdr_upscale_enabled=False,
        hdr_output_scale=1.0,
        hdr_tone="vivid",
    )
    assert req.subtitle_y_percent == 84
    assert req.custom_colors["second"] == "#FFE600"
    assert req.words_per_beat == 3


@pytest.mark.parametrize("value", [-1, 101])
def test_job_settings_reject_invalid_caption_y(value: float) -> None:
    with pytest.raises(ValueError):
        JobSettingsRequest(subtitle_y_percent=value)


def test_sfx_path_must_stay_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "split_sfx"
    root.mkdir()
    safe = root / "click.mp3"
    safe.write_bytes(b"audio")

    assert _safe_sfx_path(root, safe) == safe.resolve()
    assert _safe_sfx_path(root, root / "missing.mp3") is None
    assert _safe_sfx_path(root, root / ".." / "secret.mp3") is None


def test_subtitle_engine_honors_custom_colors_and_y_position(tmp_path: Path) -> None:
    out = tmp_path / "captions.ass"
    SubtitleEngine().generate_ass_file(
        segments=[{
            "start": 0.0,
            "end": 1.0,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.5, "end": 1.0},
            ],
        }],
        output_path=out,
        custom_colors={"main": "#123456", "second": "#ABCDEF", "third": "#FEDCBA"},
        subtitle_y_percent=84,
    )
    content = out.read_text(encoding="utf-8")
    assert "84" not in content  # y-percent is converted to an ASS margin.
    assert "&H00563412&" in content  # #123456 -> ASS BGR.
    assert "&H00EFCDAB&" in content  # #ABCDEF -> ASS BGR.
    assert ",2," in content  # bottom-center alignment for a lower caption position.
