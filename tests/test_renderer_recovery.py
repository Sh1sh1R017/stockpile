import subprocess

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.renderer import Renderer


def test_encoder_args_force_cpu(monkeypatch):
    monkeypatch.setattr(Config, "NVENC_MODE", "off")
    assert Renderer._encoder_args() == [
        "-c:v", "libx264", "-preset", "veryfast", "-threads", "0", "-crf", str(Config.VIDEO_CRF)
    ]


def test_encoder_args_auto_uses_nvenc_when_available(monkeypatch):
    monkeypatch.setattr(Config, "NVENC_MODE", "auto")
    monkeypatch.setattr(Config, "NVENC_PRESET", "p4")
    monkeypatch.setattr(Config, "NVENC_CQ", 19)

    class Result:
        stdout = " V..... h264_nvenc NVENC H.264 encoder\\n"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())
    assert Renderer._encoder_args() == [
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-rc", "vbr",
        "-cq", "19",
        "-b:v", "0",
    ]


def test_encoder_args_auto_falls_back_to_x264(monkeypatch):
    monkeypatch.setattr(Config, "NVENC_MODE", "auto")

    class Result:
        stdout = " V..... libx264 H.264 encoder\\n"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())
    args = Renderer._encoder_args()
    assert args[:6] == ["-c:v", "libx264", "-preset", "veryfast", "-threads", "0"]
    assert args[-2:] == ["-crf", str(Config.VIDEO_CRF)]


def test_fast_render_validation_defaults_on(monkeypatch):
    monkeypatch.delenv("STOCKPILE_FAST_VALIDATION", raising=False)
    assert Config.FAST_RENDER_VALIDATION is True
