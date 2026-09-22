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

    async def render(
        self,
        base_video: str,
        edit_plan: Dict[str, Any],
        output_path: str,
        ass_subtitles_path: str = None,
        bgm_path: str = None,
        bgm_volume: float = 0.15,
        ducking_enabled: bool = True,
        upscale_hdr: bool = False,
        hdr_scale: float = 1.0,
        hdr_tone: str = "vivid"
    ) -> str:
        """Render the composite video with B-roll cutaway overlays, dynamic transitions,
        kinetic subtitles, and mixed audio SFX with ducked background music.
        Optionally upscales and converts the final master to HDR10 via sdr2hdr."""
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
            f"Rendering timeline: base={base_p.name} with {len(shots)} B-roll cutaway overlays, "
            f"{len(audio_sfx_list)} audio SFX tracks, subtitles={bool(ass_subtitles_path)}, BGM={bool(bgm_path)}"
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

        # Optional BGM input stream (looped)
        bgm_stream_idx = None
        if bgm_path and os.path.exists(bgm_path):
            bgm_stream_idx = 1 + len(shots) + len(audio_sfx_list)
            cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])

        # Build complex filtergraph
        filtergraph, final_video, final_audio = self.timeline.build_filtergraph(
            shots=shots,
            audio_sfx_list=audio_sfx_list,
            ass_subtitles_path=ass_subtitles_path,
            bgm_stream_idx=bgm_stream_idx,
            bgm_volume=bgm_volume,
            ducking_enabled=ducking_enabled
        )

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

        if upscale_hdr:
            hdr_out_p = out_p.with_name(f"{out_p.stem}_hdr10.mp4")
            try:
                from ai_broll_autopilot.services.sdr2hdr_service import SDR2HDREngine
                engine = SDR2HDREngine()
                logger.info(f"Executing SDR2HDR upscale & HDR10 pass for {out_p.name} -> {hdr_out_p.name} (scale={hdr_scale}x)...")
                await engine.convert_and_upscale_async(
                    input_path=str(out_p),
                    output_path=str(hdr_out_p),
                    output_scale=hdr_scale,
                    tone=hdr_tone,
                    fast_mode=Config.HDR_FAST_MODE,
                    processing_scale=Config.HDR_PROCESSING_SCALE
                )
                if hdr_out_p.exists() and hdr_out_p.stat().st_size > 0:
                    logger.info(f"SDR2HDR upscaling succeeded: {hdr_out_p.name} ({hdr_out_p.stat().st_size / 1024 / 1024:.2f} MB)")
                    return str(hdr_out_p)
            except Exception as e:
                logger.error(f"SDR2HDR upscale failed, falling back to SDR master: {e}")

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
