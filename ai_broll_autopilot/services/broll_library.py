"""Local-First Niche B-Roll Library Index and Ingestion Engine.

Manages cataloged B-roll footage organized by niche and metadata tags,
providing fast local semantic search before falling back to external fetchers.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.niches import niche_registry

logger = logging.getLogger(__name__)


def extract_media_metadata(file_path: Path) -> Dict[str, Any]:
    """Probe video file with ffprobe to extract duration, resolution, and fps."""
    meta = {
        "duration": 0.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
    }
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Video stream
        streams = data.get("streams", [])
        if streams:
            v = streams[0]
            meta["width"] = int(v.get("width", 1920))
            meta["height"] = int(v.get("height", 1080))
            if "r_frame_rate" in v and "/" in v["r_frame_rate"]:
                num, den = v["r_frame_rate"].split("/")
                if float(den) > 0:
                    meta["fps"] = round(float(num) / float(den), 2)
            if "duration" in v and v["duration"]:
                meta["duration"] = float(v["duration"])

        # Format duration fallback
        fmt = data.get("format", {})
        if meta["duration"] == 0.0 and "duration" in fmt and fmt["duration"]:
            meta["duration"] = float(fmt["duration"])

    except Exception as e:
        logger.debug(f"ffprobe metadata extraction failed for {file_path.name}: {e}")

    return meta


class BrollLibraryService:
    """Local-first B-Roll catalog supporting multi-niche indexing and fast discovery."""

    VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}

    def __init__(self, db: Optional[Database] = None, library_root: Optional[Path] = None):
        self.db = db or Database()
        self.library_root = library_root or (Config.PROJECT_ROOT / "library")
        self.library_root.mkdir(parents=True, exist_ok=True)
        # Ensure niche folders exist
        for niche_id in niche_registry.list_ids():
            (self.library_root / niche_id).mkdir(exist_ok=True)

    def index_file(
        self,
        file_path: Path,
        niche_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        score: int = 7,
    ) -> Dict[str, Any]:
        """Index a single video file into the local B-roll catalog."""
        if not file_path.exists() or file_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid video file path: {file_path}")

        resolved_niche = niche_id or self._guess_niche_from_path(file_path)
        meta = extract_media_metadata(file_path)

        asset_id = f"broll_{resolved_niche}_{file_path.stem}"
        clean_title = title or file_path.stem.replace("_", " ").title()
        tag_list = tags or [resolved_niche]

        self.db.save_broll_asset(
            asset_id=asset_id,
            file_path=str(file_path.resolve()),
            title=clean_title,
            source="local_library",
            prompt=description or clean_title,
            duration=meta["duration"],
            score=score,
            niche_id=resolved_niche,
            tags=tag_list,
            width=meta["width"],
            height=meta["height"],
            fps=meta["fps"],
            description=description or clean_title,
        )

        logger.info(f"Indexed B-roll asset '{asset_id}' into niche '{resolved_niche}' ({meta['duration']:.1f}s)")
        return self.db.get_broll_asset(asset_id) or {}

    def index_directory(
        self,
        dir_path: Path,
        niche_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """Recursively scan and index video files in a folder."""
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Directory {dir_path} does not exist.")
            return 0

        indexed_count = 0
        for root, _, files in os.walk(dir_path):
            root_path = Path(root)
            # Determine niche from subfolder name if not explicitly passed
            folder_niche = niche_id or self._guess_niche_from_path(root_path)

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.VIDEO_EXTENSIONS:
                    file_full_path = root_path / file
                    try:
                        self.index_file(
                            file_path=file_full_path,
                            niche_id=folder_niche,
                            tags=tags,
                        )
                        indexed_count += 1
                    except Exception as e:
                        logger.error(f"Failed indexing {file_full_path}: {e}")

        logger.info(f"Successfully indexed {indexed_count} video files from {dir_path}")
        return indexed_count

    def search_local(
        self,
        query: str,
        niche_id: Optional[str] = None,
        min_duration: float = 1.0,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search local catalog for footage matching query terms and niche.

        Returns:
            List of matched asset dicts verified to exist on disk.
        """
        results = self.db.search_broll_assets(
            niche_id=niche_id,
            query=query,
            min_score=0,
            limit=limit * 2,
        )

        valid_matches = []
        for asset in results:
            fp = Path(asset["file_path"])
            if fp.exists():
                dur = float(asset.get("duration") or 0.0)
                if dur >= min_duration or dur == 0.0:
                    valid_matches.append(asset)
            if len(valid_matches) >= limit:
                break

        return valid_matches

    def list_assets(self, niche_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List cataloged assets, optionally filtered by niche."""
        return self.db.list_broll_assets(niche_id=niche_id, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics of cataloged footage across niches."""
        all_assets = self.db.list_broll_assets(limit=1000)
        niche_counts: Dict[str, int] = {}
        total_duration = 0.0

        for a in all_assets:
            n = a.get("niche_id", "generic")
            niche_counts[n] = niche_counts.get(n, 0) + 1
            total_duration += float(a.get("duration") or 0.0)

        return {
            "total_assets": len(all_assets),
            "total_duration_seconds": round(total_duration, 1),
            "niche_counts": niche_counts,
            "library_path": str(self.library_root),
        }

    def _guess_niche_from_path(self, path: Path) -> str:
        """Infer niche identifier from directory or file name."""
        path_str = str(path).lower()
        for niche_id in niche_registry.list_ids():
            if niche_id in path_str:
                return niche_id
            # Check parent niche
            profile = niche_registry.get_profile(niche_id)
            if profile.parent_niche in path_str:
                return profile.id
        return "generic"


# Global singleton instance
broll_library = BrollLibraryService()
