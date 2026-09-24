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
        hdr_tone: str = "vivid",
        watermark_path: str = None,
        watermark_position: str = "bottom_safe",
        watermark_scale: float = 0.28,
        preserve_dialogue_only: bool = False,
        frame_overlay_path: str = None,
        viewport: tuple = None,
    ) -> str:
        """Render the composite video with B-roll cutaway overlays, dynamic transitions,
        kinetic subtitles, frame overlay mask, watermark branding, and mixed audio SFX with ducked background music.
        Optionally upscales and converts the final master to HDR10 via sdr2hdr."""
        base_p = Path(base_video)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        shots: List[Dict[str, Any]] = [s for s in edit_plan.get("shots", []) if s.get("asset_path")]

        # Gather all sound effects (transition stingers/whooshes + contextual Foley + Level 3 Graphic impacts)
        audio_sfx_list: List[Dict[str, Any]] = []

        # 1. B-roll cutaway transition stingers / subtle whooshes
        for idx, shot in enumerate(shots, start=1):
            start_t = float(shot.get("start_time", 0.0))
            trans = shot.get("transition", {})
            stinger = trans.get("stinger_sfx")
            if stinger and stinger.get("path") and os.path.exists(stinger["path"]):
                audio_sfx_list.append({
                    "path": stinger["path"],
                    "start_time": max(0.0, start_t - 0.05),
                    "volume": stinger.get("volume", 0.25),
                    "type": "transition_stinger"
                })
            elif os.path.exists("assets/sfx/whoosh.mp3"):
                audio_sfx_list.append({
                    "path": "assets/sfx/whoosh.mp3",
                    "start_time": max(0.0, start_t - 0.05),
                    "volume": 0.18,
                    "type": "transition_whoosh"
                })

            if not preserve_dialogue_only:
                ctx_sfx = shot.get("contextual_sfx")
                if ctx_sfx and ctx_sfx.get("path") and os.path.exists(ctx_sfx["path"]):
                    offset = float(ctx_sfx.get("start_offset", 0.2))
                    audio_sfx_list.append({
                        "path": ctx_sfx["path"],
                        "start_time": start_t + offset,
                        "volume": ctx_sfx.get("volume", 0.40),
                        "type": "contextual_foley"
                    })

        # 2. Level 3 Graphic Impact SFX
        for item in edit_plan.get("text_emphasis_graphics", []):
            start_t = float(item.get("start_time", 0.0))
            impact_path = item.get("sfx_path", "assets/sfx/impact.mp3")
            if impact_path and os.path.exists(impact_path):
                audio_sfx_list.append({
                    "path": impact_path,
                    "start_time": max(0.0, start_t),
                    "volume": item.get("sfx_volume", 0.22),
                    "type": "graphic_impact"
                })

        logger.info(
            f"Rendering timeline: base={base_p.name} with {len(shots)} B-roll cutaway overlays, "
            f"{len(audio_sfx_list)} audio SFX tracks, subtitles={bool(ass_subtitles_path)}, "
            f"BGM={bool(bgm_path)}, frame_overlay={bool(frame_overlay_path)}, watermark={bool(watermark_path)}"
        )

        # Build FFmpeg command inputs
        # Input 0: Base video
        cmd = ["ffmpeg", "-y", "-i", str(base_p)]

        # Inputs 1 .. len(shots): B-roll video streams
        for shot in shots:
            cmd.extend(["-stream_loop", "-1", "-i", str(shot["asset_path"])])

        # Optional Frame Overlay stream (torn paper mask & branding)
        frame_overlay_stream_idx = None
        if frame_overlay_path and os.path.exists(frame_overlay_path):
            frame_overlay_stream_idx = 1 + len(shots)
            cmd.extend(["-loop", "1", "-i", str(frame_overlay_path)])

        # Optional Watermark input stream
        watermark_stream_idx = None
        if watermark_path and os.path.exists(watermark_path):
            watermark_stream_idx = 1 + len(shots) + (1 if frame_overlay_stream_idx is not None else 0)
            cmd.extend(["-loop", "1", "-i", str(watermark_path)])

        # Audio inputs start index
        audio_inputs_start = (
            1 + len(shots)
            + (1 if frame_overlay_stream_idx is not None else 0)
            + (1 if watermark_stream_idx is not None else 0)
        )

        # Inputs audio_inputs_start .. : Audio SFX files
        for sfx in audio_sfx_list:
            cmd.extend(["-i", str(sfx["path"])])

        # Optional BGM input stream (looped)
        bgm_stream_idx = None
        if bgm_path and os.path.exists(bgm_path):
            bgm_stream_idx = audio_inputs_start + len(audio_sfx_list)
            cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])

        # Build complex filtergraph
        filtergraph, final_video, final_audio = self.timeline.build_filtergraph(
            shots=shots,
            audio_sfx_list=audio_sfx_list,
            ass_subtitles_path=ass_subtitles_path,
            bgm_stream_idx=bgm_stream_idx,
            bgm_volume=bgm_volume,
            ducking_enabled=ducking_enabled,
            watermark_stream_idx=watermark_stream_idx,
            watermark_position=watermark_position,
            watermark_scale=watermark_scale,
            frame_overlay_stream_idx=frame_overlay_stream_idx,
            viewport=viewport,
        )

        # Probe base video duration to ensure output matches base video exactly
        import subprocess
        base_dur = None
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(base_p)
            ]
            res = subprocess.check_output(probe_cmd).decode().strip()
            base_dur = float(res)
        except Exception as e:
            logger.warning(f"Could not probe base video duration: {e}")

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
        ])
        if base_dur and base_dur > 0:
            cmd.extend(["-t", f"{base_dur:.3f}"])
        else:
            cmd.append("-shortest")
        cmd.extend([
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
