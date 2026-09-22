"""SFX Indexer: Discovers, categorizes, and unifies audio sound effects across local libraries.

Merges the 93 split meme sound effects with the 96 Social SFX Pack audio files
into a single searchable catalog of 189 items.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPLIT_SFX_DIR = BASE_DIR / "output" / "split_sfx"
CATALOG_PATH = SPLIT_SFX_DIR / "sfx_catalog.json"

SOCIAL_SFX_DIR = Path(r"D:\SUS AI ONLY\Social SFX Pack - Collection 1 (1)\Social SFX Pack - Collection 1")


def clean_name(filename: str) -> str:
    """Generate a clean, human-readable name from audio filename."""
    stem = Path(filename).stem
    # Remove leading numbers/underscores like '01_'
    stem = re.sub(r"^\d+[\s_-]*", "", stem)
    # Replace dashes/underscores with spaces
    stem = stem.replace("-", " ").replace("_", " ")
    # Clean up common redundant suffixes
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title()


def build_unified_catalog() -> List[Dict[str, Any]]:
    """Build and save unified catalog of all sound effects."""
    catalog = []
    
    # 1. Load existing split SFX (1..93)
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
                for item in existing:
                    item["source"] = "split_sfx"
                    item["path"] = str(SPLIT_SFX_DIR / item["file"])
                    catalog.append(item)
            logger.info(f"Loaded {len(catalog)} sounds from existing split_sfx library.")
        except Exception as e:
            logger.error(f"Error loading existing catalog: {e}")

    # 2. Index Social SFX Pack (96 files)
    social_count = 0
    if SOCIAL_SFX_DIR.exists():
        start_id = 100
        category_mapping = {
            "Camera Sounds": ("Camera & Mechanical", "Camera shutter, focus beep, or film advance sound"),
            "Drops": ("Cinematic Drop & Impact", "Deep sub-bass drop, cinematic impact, or transition fall"),
            "Electronic": ("UI & Electronic", "Modern digital chime, notification ping, or tech glitch"),
            "Impacts": ("Impact", "Punchy physical hit, cinematic thud, or crash"),
            "Keyboard Typing": ("Office & Foley", "Mechanical keyboard key clatter and typing Foley"),
            "Mechanical": ("Mechanical", "Switch, click, latch, or mechanical gear interaction"),
            "Risers": ("Tension Riser", "Cinematic crescendo riser and tension builder"),
            "Whooshs": ("Transition Whoosh", "Fast air whoosh, whip transition sweep, or dynamic pass")
        }

        for subfolder in sorted(SOCIAL_SFX_DIR.iterdir()):
            if subfolder.is_dir():
                cat_name = subfolder.name
                cat_info = category_mapping.get(cat_name, (cat_name, f"High quality {cat_name.lower()} sound effect"))
                
                audio_files = sorted([
                    f for f in subfolder.iterdir()
                    if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".m4a")
                ])

                for af in audio_files:
                    start_id += 1
                    readable_name = clean_name(af.name)
                    item = {
                        "id": start_id,
                        "name": readable_name,
                        "file": af.name,
                        "path": str(af),
                        "cat": cat_info[0],
                        "desc": f"{readable_name} ({cat_info[1]})",
                        "source": "social_sfx_pack",
                        "folder": cat_name
                    }
                    catalog.append(item)
                    social_count += 1

        logger.info(f"Indexed {social_count} new sound effects from Social SFX Pack.")
    else:
        logger.warning(f"Social SFX Pack directory not found at: {SOCIAL_SFX_DIR}")

    # Save merged catalog
    try:
        SPLIT_SFX_DIR.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
        logger.info(f"Saved unified SFX catalog with {len(catalog)} total items to: {CATALOG_PATH}")
    except Exception as e:
        logger.error(f"Error saving unified catalog: {e}")

    return catalog


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cat = build_unified_catalog()
    print(f"Total unified SFX items: {len(cat)}")
