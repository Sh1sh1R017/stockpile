"""Video rendering engine executing FFmpeg multi-layer compositing, transitions, and audio mixing."""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from PIL import Image, ImageDraw

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

    @staticmethod
    def _ensure_reference_card_mask(output_path: Path, width: int, height: int, width_ratio: float = 0.944, height_ratio: float = 0.574, radius: int = 52) -> Path:
        card_w = int(round(width * max(0.5, min(width_ratio, 1.0)))) & ~1
        card_h = int(round(height * max(0.35, min(height_ratio, 0.95)))) & ~1
        scaled_radius = max(8, min(int(round(radius * (width / 1080.0))), min(card_w, card_h) // 2))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path
        image = Image.new("L", (card_w, card_h), 0)
        ImageDraw.Draw(image).rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=scaled_radius, fill=255)
        image.save(output_path, format="PNG")
        return output_path

    @staticmethod
    def _encoder_args() -> List[str]:
        """Return the fastest safe hardware encoder available for this host.

        NVENC is opt-in/auto via config. A probe prevents broken FFmpeg builds from
        failing the entire render; CPU x264 remains the compatibility fallback.
        """
        mode = Config.NVENC_MODE
        if mode not in {"0", "1", "auto", "true", "false", "on", "off"}:
            mode = "auto"
        if mode in {"0", "false", "off"}:
            return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(Config.VIDEO_CRF), "-threads", "0"]
        try:
            probe = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
            )
            nvenc_available = "h264_nvenc" in (probe.stdout or "")
        except Exception:
            nvenc_available = False
        if mode in {"1", "true", "on"} and not nvenc_available:
            logger.warning("STOCKPILE_NVENC is enabled but h264_nvenc is unavailable; falling back to x264.")
        if nvenc_available:
            return ["-c:v", "h264_nvenc", "-preset", Config.NVENC_PRESET, "-rc", "vbr", "-cq", str(Config.NVENC_CQ), "-b:v", "0"]
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(Config.VIDEO_CRF), "-threads", "0"]

    async def render(self, base_video: str, edit_plan: Dict[str, Any], output_path: str, ass_subtitles_path: str = None, bgm_path: str = None, bgm_volume: float = 0.15, ducking_enabled: bool = True, upscale_hdr: bool = False, hdr_scale: float = 1.0, hdr_tone: str = "vivid", watermark_path: str = None, watermark_position: str = "bottom_safe", watermark_scale: float = 0.28, preserve_dialogue_only: bool = False, frame_overlay_path: str = None, viewport: tuple = None, behind_subject_ass_path: str = None, subject_matte_path: str = None, layout_mode: str = None) -> str:
        """Render the composite video with B-roll, captions, SFX and editorial layers."""
        base_p = Path(base_video)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        style_data = edit_plan.get("style") if isinstance(edit_plan.get("style"), dict) else {}
        editing_style = str(edit_plan.get("editing_style") or style_data.get("id") or "")
        reference_style = bool(edit_plan.get("reference_editing") or style_data.get("reference_style") or editing_style in {"cinematic_social_editorial", "cinematic_editorial"})
        shots = [s for s in edit_plan.get("shots", []) if s.get("asset_path")]
        audio_sfx_list: List[Dict[str, Any]] = []
        for shot in shots:
            start_t = float(shot.get("start_time", 0.0))
            trans = shot.get("transition", {})
            stinger = trans.get("stinger_sfx")
            if stinger and stinger.get("path") and os.path.exists(stinger["path"]):
                audio_sfx_list.append({"path": stinger["path"], "start_time": max(0.0, start_t - 0.05), "volume": stinger.get("volume", 0.25), "type": "transition_stinger"})
            elif not reference_style and os.path.exists("assets/sfx/whoosh.mp3"):
                audio_sfx_list.append({"path": "assets/sfx/whoosh.mp3", "start_time": max(0.0, start_t - 0.05), "volume": 0.18, "type": "transition_whoosh"})
            if not preserve_dialogue_only:
                ctx_sfx = shot.get("contextual_sfx")
                if ctx_sfx and ctx_sfx.get("path") and os.path.exists(ctx_sfx["path"]):
                    audio_sfx_list.append({"path": ctx_sfx["path"], "start_time": start_t + float(ctx_sfx.get("start_offset", 0.2)), "volume": ctx_sfx.get("volume", 0.40), "type": "contextual_foley"})
        for item in edit_plan.get("text_emphasis_graphics", []):
            impact_path = item.get("sfx_path") if reference_style else item.get("sfx_path", "assets/sfx/impact.mp3")
            if impact_path and os.path.exists(impact_path):
                audio_sfx_list.append({"path": impact_path, "start_time": max(0.0, float(item.get("start_time", 0.0))), "volume": item.get("sfx_volume", 0.22), "type": "graphic_impact"})
        behind_subject_overlay = next((ov for ov in edit_plan.get("text_overlays", []) if ov.get("behind_subject") or ov.get("behindSubject")), None)
        has_behind_subtitles = bool(behind_subject_ass_path and os.path.exists(behind_subject_ass_path)) or any(s.get("behind_subject") or s.get("behindSubject") for s in edit_plan.get("subtitles", []))
        if not subject_matte_path or not os.path.exists(subject_matte_path):
            subject_matte_path = None
            if has_behind_subtitles or behind_subject_overlay:
                matte_file = out_p.parent / ("subject_matte.mp4" if has_behind_subtitles else f"matte_{behind_subject_overlay.get('id', 'hook')}.mp4")
                if matte_file.exists() and matte_file.stat().st_size > 0:
                    subject_matte_path = str(matte_file)
                else:
                    try:
                        from ai_broll_autopilot.services.subject_isolation import subject_isolation_service
                        st = 0.0 if has_behind_subtitles else float(behind_subject_overlay.get("start_time", 0.0))
                        dur = None if has_behind_subtitles else float(behind_subject_overlay.get("duration", 2.5))
                        m_path = subject_isolation_service.create_subject_matte_clip(video_path=str(base_p), output_matte_path=str(matte_file), start_time=st, duration=dur, target_width=Config.TARGET_WIDTH, target_height=Config.TARGET_HEIGHT)
                        if m_path and os.path.exists(m_path):
                            subject_matte_path = m_path
                    except Exception as e:
                        logger.warning(f"Subject isolation matte skipped: {e}. Falling back to normal compositing.")
        cmd = ["ffmpeg", "-y", "-i", str(base_p)]
        for shot in shots:
            cmd.extend(["-stream_loop", "-1", "-i", str(shot["asset_path"])])
        layout_mode = layout_mode or edit_plan.get("layout_mode") or edit_plan.get("render_settings", {}).get("layout_mode") or "single"
        reference_card_mask_idx = None
        reference_card_width_ratio = float(style_data.get("visual_container_width_ratio", 0.944))
        reference_card_height_ratio = float(style_data.get("visual_container_height_ratio", 0.574))
        reference_card_radius = int(style_data.get("visual_container_radius", 52))
        current_input_idx = 1 + len(shots)
        frame_overlay_stream_idx = None
        if frame_overlay_path and os.path.exists(frame_overlay_path):
            frame_overlay_stream_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(frame_overlay_path)]); current_input_idx += 1
        watermark_stream_idx = None
        if watermark_path and os.path.exists(watermark_path):
            watermark_stream_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(watermark_path)]); current_input_idx += 1
        if reference_style:
            mask_path = self._ensure_reference_card_mask(out_p.parent / "reference_card_mask.png", self.timeline.width, self.timeline.height, width_ratio=reference_card_width_ratio, height_ratio=reference_card_height_ratio, radius=reference_card_radius)
            reference_card_mask_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(mask_path)]); current_input_idx += 1
        subject_matte_stream_idx = None
        if subject_matte_path and os.path.exists(subject_matte_path):
            subject_matte_stream_idx = current_input_idx; cmd.extend(["-stream_loop", "-1", "-i", str(subject_matte_path)]); current_input_idx += 1
        cyber_grid_backdrop_idx = cyber_grid_mask_before_idx = cyber_grid_mask_after_idx = None
        if layout_mode == "before_after_cyber_grid":
            from ai_broll_autopilot.services.cyber_grid_engine import cyber_grid_engine
            bg_p, mb_p, ma_p = cyber_grid_engine.ensure_assets()
            cyber_grid_backdrop_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(bg_p)]); current_input_idx += 1
            cyber_grid_mask_before_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(mb_p)]); current_input_idx += 1
            cyber_grid_mask_after_idx = current_input_idx; cmd.extend(["-loop", "1", "-i", str(ma_p)]); current_input_idx += 1
        audio_inputs_start = current_input_idx
        for sfx in audio_sfx_list:
            cmd.extend(["-i", str(sfx["path"])])
        bgm_stream_idx = None
        if bgm_path and os.path.exists(bgm_path):
            bgm_stream_idx = audio_inputs_start + len(audio_sfx_list); cmd.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        filtergraph, final_video, final_audio = self.timeline.build_filtergraph(shots=shots, audio_sfx_list=audio_sfx_list, ass_subtitles_path=ass_subtitles_path, bgm_stream_idx=bgm_stream_idx, bgm_volume=bgm_volume, ducking_enabled=ducking_enabled, watermark_stream_idx=watermark_stream_idx, watermark_position=watermark_position, watermark_scale=watermark_scale, frame_overlay_stream_idx=frame_overlay_stream_idx, viewport=viewport, behind_subject_text=behind_subject_overlay, subject_matte_stream_idx=subject_matte_stream_idx, behind_subject_ass_path=behind_subject_ass_path, layout_mode=layout_mode, cyber_grid_backdrop_idx=cyber_grid_backdrop_idx, cyber_grid_mask_before_idx=cyber_grid_mask_before_idx, cyber_grid_mask_after_idx=cyber_grid_mask_after_idx, reference_style=reference_style, reference_card_mask_idx=reference_card_mask_idx, reference_card_width_ratio=reference_card_width_ratio, reference_card_height_ratio=reference_card_height_ratio, reference_card_radius=reference_card_radius)
        base_dur = None
        try:
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(base_p)]
            base_dur = float(subprocess.check_output(probe_cmd).decode().strip())
        except Exception as e:
            logger.warning(f"Could not probe base video duration: {e}")
        cmd.extend(["-filter_complex", filtergraph, "-map", f"[{final_video}]", "-map", f"[{final_audio}]"])
        cmd.extend(self._encoder_args())
        cmd.extend(["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-avoid_negative_ts", "make_zero", "-movflags", "+faststart"])
        cmd.extend(["-t", f"{base_dur:.3f}"] if base_dur and base_dur > 0 else ["-shortest"])
        cmd.extend(["-v", "warning", str(out_p)])
        logger.info(f"Executing FFmpeg render ({len(shots)} overlays, {len(audio_sfx_list)} SFX, encoder={'NVENC' if 'h264_nvenc' in self._encoder_args() else 'x264'})")
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg rendering error: {res.stderr}")
            raise RuntimeError(f"FFmpeg rendering failed: {res.stderr[-2000:]}")
        if not out_p.exists() or out_p.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg rendering failed: output file not created at {out_p}")
        from ai_broll_autopilot.services.media_validator import media_validator
        val_res = media_validator.validate(out_p, auto_remedy=True)
        if not val_res.is_valid:
            raise RuntimeError(f"Media validation failed for {out_p.name}: {', '.join(val_res.errors)}")
        if upscale_hdr:
            hdr_out_p = out_p.with_name(f"{out_p.stem}_hdr10.mp4")
            try:
                from ai_broll_autopilot.services.sdr2hdr_service import SDR2HDREngine
                engine = SDR2HDREngine()
                await engine.convert_and_upscale_async(input_path=str(out_p), output_path=str(hdr_out_p), output_scale=hdr_scale, tone=hdr_tone, fast_mode=Config.HDR_FAST_MODE, processing_scale=Config.HDR_PROCESSING_SCALE)
                if hdr_out_p.exists() and hdr_out_p.stat().st_size > 0:
                    media_validator.validate(hdr_out_p, auto_remedy=True)
                    return str(hdr_out_p)
            except Exception as e:
                logger.error(f"SDR2HDR upscale failed, falling back to SDR master: {e}")
        return str(out_p)

    async def _normalize_single_video(self, base_p: Path, out_p: Path) -> str:
        """Fallback normalization if no B-roll was inserted."""
        cmd = ["ffmpeg", "-y", "-i", str(base_p), "-vf", f"scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"]
        cmd.extend(self._encoder_args())
        cmd.extend(["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-avoid_negative_ts", "make_zero", "-movflags", "+faststart", "-v", "warning", str(out_p)])
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        from ai_broll_autopilot.services.media_validator import media_validator
        media_validator.validate(out_p, auto_remedy=True)
        return str(out_p)
