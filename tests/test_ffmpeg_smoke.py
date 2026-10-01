"""Static filtergraph and FFmpeg smoke tests."""

import shutil
import subprocess

import pytest

from ai_broll_autopilot.services.filtergraph_lint import (
    assert_filtergraph_labels,
    validate_filtergraph_labels,
)
from ai_broll_autopilot.services.timeline import TimelineEngine


def test_filtergraph_validator_detects_dangling_outputs():
    graph = "[0:v]null[used];[used]null[final];[0:a]anull[dangling]"
    assert validate_filtergraph_labels(graph, final_labels={"final"}) == [
        "label 'dangling' produced by filter segment 2 has no consumer"
    ]


def test_timeline_no_asset_graph_has_no_dangling_labels():
    graph, final_video, final_audio = TimelineEngine().build_filtergraph(
        shots=[],
        ducking_enabled=False,
    )
    assert_filtergraph_labels(graph, final_labels={final_video, final_audio})


@pytest.mark.ffmpeg
def test_real_ffmpeg_lavfi_smoke(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg executable unavailable")

    source = tmp_path / "source.mp4"
    bgm = tmp_path / "bgm.wav"
    output = tmp_path / "output.mp4"

    subprocess.run(
        [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000",
            "-t", "3",
            "-c:a", "pcm_s16le",
            str(bgm),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    graph, final_video, final_audio = TimelineEngine().build_filtergraph(
        shots=[],
        bgm_stream_idx=1,
        ducking_enabled=True,
        output_duration=3.0,
    )
    assert_filtergraph_labels(graph, final_labels={final_video, final_audio})

    subprocess.run(
        [
            ffmpeg, "-y",
            "-i", str(source),
            "-i", str(bgm),
            "-filter_complex", graph,
            "-map", f"[{final_video}]",
            "-map", f"[{final_audio}]",
            "-t", "3",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-c:a", "aac",
            "-ar", "48000",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(probe.stdout.strip())
    assert 2.7 <= duration <= 3.2
