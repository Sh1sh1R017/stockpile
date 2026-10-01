"""Filesystem confinement helpers for API routes."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from urllib.parse import urlparse


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


def validate_external_url(
    url: str,
    *,
    allowed_hosts: set[str] | None = None,
    require_https: bool = True,
) -> str:
    """Validate an external URL before a server-side downloader follows it."""
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in ({"https"} if require_https else {"http", "https"}):
        raise ValueError("Only HTTPS URLs are allowed")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL must include a hostname")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private or non-routable IP addresses are not allowed")
        if allowed_hosts and host not in allowed_hosts:
            raise ValueError("URL host is not allowed")
    elif allowed_hosts:
        normalized = {h.lower().rstrip(".") for h in allowed_hosts}
        if not any(host == h or host.endswith("." + h) for h in normalized):
            raise ValueError("URL host is not allowed")

    return parsed.geturl()
