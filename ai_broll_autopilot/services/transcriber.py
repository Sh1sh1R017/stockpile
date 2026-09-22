"""Audio transcription service providing timestamped segments and SRT using OpenAI Whisper."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
import whisper

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


def format_timestamp_srt(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"


class Transcriber:
    """Service for extracting audio and generating timestamped transcripts."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name or Config.WHISPER_MODEL
        self.model = None
        self._lock = asyncio.Lock()
        self._load_model()

    def _load_model(self):
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Whisper model '{self.model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    async def transcribe(self, video_path: str) -> Dict[str, Any]:
        """Transcribe audio from video file to full text and timestamped segments."""
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Extracting and transcribing audio for: {path.name}")

        # Extract audio to temp wav using ffmpeg
        audio_temp = path.with_name(f"temp_audio_{path.stem}.wav")
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-v", "quiet",
                str(audio_temp)
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()

            if not audio_temp.exists() or audio_temp.stat().st_size == 0:
                raise RuntimeError("Failed to extract audio from video")

            async with self._lock:
                result = await asyncio.to_thread(self._run_whisper, str(audio_temp))

            return result

        finally:
            if audio_temp.exists():
                audio_temp.unlink(missing_ok=True)

    def _run_whisper(self, audio_path: str) -> Dict[str, Any]:
        if not self.model:
            raise ValueError("Whisper model not initialized")

        res = self.model.transcribe(
            audio_path,
            task="transcribe",
            fp16=False,
            verbose=False,
        )

        full_text = res.get("text", "").strip()
        raw_segments = res.get("segments", [])

        clean_segments = []
        srt_lines = []

        for idx, seg in enumerate(raw_segments, start=1):
            start = round(float(seg["start"]), 2)
            end = round(float(seg["end"]), 2)
            text = seg["text"].strip()
            if not text:
                continue

            clean_segments.append({
                "id": idx,
                "start": start,
                "end": end,
                "duration": round(end - start, 2),
                "text": text,
            })

            srt_lines.append(f"{idx}\n{format_timestamp_srt(start)} --> {format_timestamp_srt(end)}\n{text}\n")

        srt_content = "\n".join(srt_lines)

        return {
            "text": full_text,
            "segments": clean_segments,
            "srt": srt_content,
            "language": res.get("language", "en"),
        }
