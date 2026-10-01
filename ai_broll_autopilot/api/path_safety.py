"""Filesystem confinement helpers for API routes."""

from __future__ import annotations

import re
from pathlib import Path


_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def safe_join(root: Path | str, user_path: str | Path) -> Path:
    """Resolve *user_path* under *root* and reject traversal/symlink escapes."""
    root_path = Path(root).expanduser().resolve()
    raw = str(user_path).strip()

    if not raw:
        return root_path

    if _WINDOWS_ABSOLUTE.match(raw) or raw.startswith("\\\\") or raw.startswith("//"):
        candidate = Path(raw)
    else:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = root_path / candidate

    candidate = candidate.expanduser().resolve()

    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"Path escapes allowed root: {user_path}") from exc

    return candidate
