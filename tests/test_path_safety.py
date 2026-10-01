"""Filesystem safety regression tests."""

import os
from pathlib import Path

import pytest

from ai_broll_autopilot.api.path_safety import safe_join


def test_safe_join_accepts_paths_inside_root(tmp_path: Path):
    result = safe_join(tmp_path, "workspace/job/output.mp4")
    assert result == (tmp_path / "workspace/job/output.mp4").resolve()


@pytest.mark.parametrize(
    "user_path",
    [
        "../outside.txt",
        "../../outside.txt",
        "/tmp/outside.txt",
        r"C:\outside.txt",
        r"C:/outside.txt",
        r"\\server\share\outside.txt",
    ],
)
def test_safe_join_rejects_escape_attempts(tmp_path: Path, user_path: str):
    with pytest.raises(ValueError):
        safe_join(tmp_path, user_path)


def test_safe_join_rejects_symlink_escape(tmp_path: Path):
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable")
    with pytest.raises(ValueError):
        safe_join(tmp_path, "link/file.mp4")
