#!/usr/bin/env python3
"""Convenience root entry point for AI B-Roll Autopilot."""

import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
root_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(root_dir))

from ai_broll_autopilot.cli import main

if __name__ == "__main__":
    main()
