"""Input Watcher monitoring local folder for video file drops."""

import logging
import time
from pathlib import Path
from typing import Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


class VideoDropHandler(FileSystemEventHandler):
    """Event handler for dropped video files."""

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.processed_files: Set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return

        p = Path(str(event.src_path))
        if p.suffix.lower() in SUPPORTED_EXTENSIONS and str(p) not in self.processed_files:
            # Wait for file copy/write completion
            time.sleep(2)
            if p.exists() and p.stat().st_size > 0:
                self.processed_files.add(str(p))
                logger.info(f"Input Watcher detected new video: {p.name}")
                self.callback(str(p))


class InputWatcher:
    """Watches the input directory for video files."""

    def __init__(self, folder_path: Path, on_video_drop: Callable[[str], None]):
        self.folder = folder_path
        self.callback = on_video_drop
        self.observer: Observer = None

    def start(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        handler = VideoDropHandler(self.callback)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.folder), recursive=False)
        self.observer.start()
        logger.info(f"Input Watcher active on: {self.folder}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Input Watcher stopped")
