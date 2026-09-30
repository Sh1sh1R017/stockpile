"""Video rendering engine executing FFmpeg multi-layer compositing, transitions, and audio mixing."""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.timeline import TimelineEngine

logger = logging.getLogger(__name__)


def _ensure_reference_card_mask(path: Path, width: int, height: int, radius: int = 52) -> Path:
    """Create the rounded-rectangle alpha mask used by the reference editorial card."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path

    try:
        from PIL import Image, ImageDraw

        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=max(1, min(radius, width // 2, height // 2)),
            fill=255,
        )
        mask.save(path)
    except Exception as exc:
        logger.warning("Could not create reference card mask: %s", exc)
        # Fail closed: an opaque mask still preserves the centered card treatment.
        from PIL import Image

        Image.new("L", (width, height), 255).save(path)
    return path


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
        behind_subject_ass_path: str = None,
        subject_matte_path: str = None,
        layout_mode: str = None,
    ) -> str:
        """Render the composite video with B-roll cutaway overlays, dynamic transitions,
        kinetic subtitles, frame overlay mask, watermark branding, and mixed audio SFX with ducked background music.
        Optionally upscales and converts the final master to HDR10 via sdr2hdr."""
        base_p = Path(base_video)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        style_meta = edit_plan.get("style") or {}
        style_id = ""
        if isinstance(style_meta, dict):
            style_id = str(style_meta.get("id") or style_meta.get("style_id") or "").lower()
        reference_style = style_id == "cinematic_social_editorial"

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

        # Check for text overlays with behind_subject flag
        behind_subject_overlay = None
        for ov in edit_plan.get("text_overlays", []):
            if ov.get("behind_subject") or ov.get("behindSubject"):
                behind_subject_overlay = ov
                break

        # Check if behind-subject subtitles are active
        has_behind_subtitles = bool(behind_subject_ass_path and os.path.exists(behind_subject_ass_path))
        if not has_behind_subtitles and edit_plan.get("subtitles"):
            for sub in edit_plan.get("subtitles", []):
                if sub.get("behind_subject") or sub.get("behindSubject"):
                    has_behind_subtitles = True
                    break

        if not subject_matte_path or not os.path.exists(subject_matte_path):
            subject_matte_path = None
            if has_behind_subtitles:
                matte_file = out_p.parent / "subject_matte.mp4"
                try:
                    from ai_broll_autopilot.services.subject_isolation import subject_isolation_service
                    m_path = subject_isolation_service.create_subject_matte_clip(
                        video_path=str(base_p),
                        output_matte_path=str(matte_file),
                        start_time=0.0,
                        duration=None,
                        target_width=Config.TARGET_WIDTH,
                        target_height=Config.TARGET_HEIGHT,
                    )
                    if m_path and os.path.exists(m_path):
                        subject_matte_path = m_path
                except Exception as e:
                    logger.warning(f"Subject isolation matte for subtitles skipped: {e}. Falling back to standard compositing.")
            elif behind_subject_overlay:
                matte_file = out_p.parent / f"matte_{behind_subject_overlay.get('id', 'hook')}.mp4"
                try:
                    from ai_broll_autopilot.services.subject_isolation import subject_isolation_service
                    st = float(behind_subject_overlay.get("start_time", 0.0))
                    dur = float(behind_subject_overlay.get("duration", 2.5))
                    m_path = subject_isolation_service.create_subject_matte_clip(
                        video_path=str(base_p),
                        output_matte_path=str(matte_file),
                        start_time=st,
                        duration=dur,
                        target_width=Config.TARGET_WIDTH,
                        target_height=Config.TARGET_HEIGHT,
                    )
                    if m_path and os.path.exists(m_path):
                        subject_matte_path = m_path
                except Exception as e:
                    logger.warning(f"Subject isolation matte skipped: {e}. Falling back to normal text overlay.")

        logger.info(
            f"Rendering timeline: base={base_p.name} with {len(shots)} B-roll cutaway overlays, "
            f"{len(audio_sfx_list)} audio SFX tracks, subtitles={bool(ass_subtitles_path)}, "
            f"behind_subtitles={bool(behind_subject_ass_path)}, "
            f"BGM={bool(bgm_path)}, frame_overlay={bool(frame_overlay_path)}, watermark={bool(watermark_path)}, "
            f"behind_subject_matte={bool(subject_matte_path)}"
        )

        # Build FFmpeg command inputs
        # Input 0: Base video
        cmd = ["ffmpeg", "-y", "-i", str(base_p)]

        # Inputs 1 .. len(shots): B-roll video streams
        for shot in shots:
            cmd.extend(["-stream_loop", "-1", "-i", str(shot["asset_path"])])

        # Layout mode resolution
        layout_mode = (
            layout_mode
            or edit_plan.get("layout_mode")
            or edit_plan.get("render_settings", {}).get("layout_mode")
            or "single"
        )

        current_input_idx = 1 + len(shots)

        # Reference card mask input. It is shared across the A-roll card and B-roll
        # cutaways by TimelineEngine via a split fan-out.
        reference_card_mask_idx = None
        if reference_style and layout_mode != "before_after_cyber_grid":
            card_w = int(round(Config.TARGET_WIDTH * 0.944))
            card_h = int(round(Config.TARGET_HEIGHT * 0.574))
            card_w -= card_w % 2
            card_h -= card_h % 2
            mask_path = out_p.parent / "reference_card_mask.png"
            mask_path = _ensure_reference_card_mask(mask_path, card_w, card_h)
            reference_card_mask_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(mask_path)])
            current_input_idx += 1

        # Optional Frame Overlay stream (torn paper mask & branding)
        frame_overlay_stream_idx = None
        if frame_overlay_path and os.path.exists(frame_overlay_path):
            frame_overlay_stream_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(frame_overlay_path)])
            current_input_idx += 1

        # Optional Watermark input stream
        watermark_stream_idx = None
        if watermark_path and os.path.exists(watermark_path):
            watermark_stream_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(watermark_path)])
            current_input_idx += 1

        # Optional Subject Matte input stream for layered typography
        subject_matte_stream_idx = None
        if subject_matte_path and os.path.exists(subject_matte_path):
            subject_matte_stream_idx = current_input_idx
            cmd.extend(["-stream_loop", "-1", "-i", str(subject_matte_path)])
            current_input_idx += 1

        # Optional Cyber Grid Before & After streams
        cyber_grid_backdrop_idx = None
        cyber_grid_mask_before_idx = None
        cyber_grid_mask_after_idx = None
        if layout_mode == "before_after_cyber_grid":
            from ai_broll_autopilot.services.cyber_grid_engine import cyber_grid_engine
            bg_p, mb_p, ma_p = cyber_grid_engine.ensure_assets()

            cyber_grid_backdrop_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(bg_p)])
            current_input_idx += 1

            cyber_grid_mask_before_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(mb_p)])
            current_input_idx += 1

            cyber_grid_mask_after_idx = current_input_idx
            cmd.extend(["-loop", "1", "-i", str(ma_p)])
            current_input_idx += 1

        # Audio inputs start index
        audio_inputs_start = current_input_idx

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
            behind_subject_text=behind_subject_overlay,
            subject_matte_stream_idx=subject_matte_stream_idx,
            behind_subject_ass_path=behind_subject_ass_path,
            layout_mode=layout_mode,
            cyber_grid_backdrop_idx=cyber_grid_backdrop_idx,
            cyber_grid_mask_before_idx=cyber_grid_mask_before_idx,
            cyber_grid_mask_after_idx=cyber_grid_mask_after_idx,
            reference_style=reference_style,
            reference_card_mask_idx=reference_card_mask_idx,
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
            "-ar", "48000",
            "-ac", "2",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
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
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg rendering error: {res.stderr}")

        if not out_p.exists() or out_p.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg rendering failed: output file not created at {out_p}")

        # Validate and enforce media compliance for browser and OpenReel playback
        from ai_broll_autopilot.services.media_validator import media_validator
        val_res = media_validator.validate(out_p, auto_remedy=True)
        if not val_res.is_valid:
            logger.error(f"Rendered video failed media validation: {val_res.errors}")
            raise RuntimeError(f"Media validation failed for {out_p.name}: {', '.join(val_res.errors)}")

        logger.info(f"Render completed successfully: {out_p.name} ({out_p.stat().st_size / 1024 / 1024:.2f} MB, faststart={val_res.has_faststart})")

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
                    media_validator.validate(hdr_out_p, auto_remedy=True)
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
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-ac", "2",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            "-v", "warning",
            str(out_p)
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        from ai_broll_autopilot.services.media_validator import media_validator
        media_validator.validate(out_p, auto_remedy=True)
        return str(out_p)
