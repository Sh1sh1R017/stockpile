"""Video rendering engine executing FFmpeg multi-layer compositing, transitions, and audio mixing."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.timeline import TimelineEngine

logger = logging.getLogger(__name__)


class Renderer:
    """Renders composite video using FFmpeg multi-input complex filtergraphs."""

    def __init__(self):
        self.timeline = TimelineEngine(
            target_width=Config.TARGET_WIDTH,
            target_height=Config.TARGET_HEIGHT,
            target_fps=Config.TARGET_FPS
        )

    async def render(self, base_video: str, edit_plan: Dict[str, Any], output_path: str) -> str:
        """Render the composite video with B-roll cutaway overlays, dynamic transitions, and mixed audio SFX."""
        base_p = Path(base_video)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        shots: List[Dict[str, Any]] = [s for s in edit_plan.get("shots", []) if s.get("asset_path")]

        # Gather all sound effects (transition stingers + contextual Foley)
        audio_sfx_list: List[Dict[str, Any]] = []

        for idx, shot in enumerate(shots, start=1):
            start_t = float(shot.get("start_time", 0.0))

            # 1. Transition stinger SFX (e.g. whoosh on entry)
            trans = shot.get("transition", {})
            stinger = trans.get("stinger_sfx")
            if stinger and stinger.get("path") and os.path.exists(stinger["path"]):
                audio_sfx_list.append({
                    "path": stinger["path"],
                    "start_time": max(0.0, start_t - 0.05),
                    "volume": stinger.get("volume", 0.45),
                    "type": "transition_stinger"
                })

            # 2. Contextual Foley / Reaction SFX
            ctx_sfx = shot.get("contextual_sfx")
            if ctx_sfx and ctx_sfx.get("path") and os.path.exists(ctx_sfx["path"]):
                offset = float(ctx_sfx.get("start_offset", 0.2))
                audio_sfx_list.append({
                    "path": ctx_sfx["path"],
                    "start_time": start_t + offset,
                    "volume": ctx_sfx.get("volume", 0.40),
                    "type": "contextual_foley"
                })

        logger.info(
            f"Rendering timeline: base={base_p.name} with {len(shots)} B-roll cutaway overlays "
            f"and {len(audio_sfx_list)} audio SFX tracks"
        )

        # Build FFmpeg command inputs
        # Input 0: Base video
        cmd = ["ffmpeg", "-y", "-i", str(base_p)]

        # Inputs 1 .. len(shots): B-roll video streams
        for shot in shots:
            cmd.extend(["-stream_loop", "-1", "-i", str(shot["asset_path"])])

        # Inputs (1 + len(shots)) .. : Audio SFX files
        for sfx in audio_sfx_list:
            cmd.extend(["-i", str(sfx["path"])])

        # Build complex filtergraph
        filtergraph, final_video, final_audio = self.timeline.build_filtergraph(shots, audio_sfx_list)

        cmd.extend([
            "-filter_complex", filtergraph,
            "-map", f"[{final_video}]",
            "-map", f"[{final_audio}]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-threads", "0",
            "-crf", str(Config.VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-v", "warning",
            str(out_p)
        ])

        logger.info(f"Executing FFmpeg render command ({len(shots)} video overlays, {len(audio_sfx_list)} audio SFX)...")
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        if not out_p.exists() or out_p.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg rendering failed: output file not created at {out_p}")

        logger.info(f"Render completed successfully: {out_p.name} ({out_p.stat().st_size / 1024 / 1024:.2f} MB)")
        return str(out_p)

    async def _normalize_single_video(self, base_p: Path, out_p: Path) -> str:
        """Fallback normalization if no B-roll was inserted."""
        cmd = [
            "ffmpeg", "-y", "-i", str(base_p),
            "-vf", f"scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-c:v", "libx264", "-preset", "veryfast", "-threads", "0", "-crf", str(Config.VIDEO_CRF),
            "-c:a", "aac", "-b:a", "192k",
            "-v", "warning",
            str(out_p)
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        return str(out_p)
