"""Timeline Engine calculating tracks, dynamic transitions, and multi-track audio mixing."""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class TimelineEngine:
    """Manages timeline calculation, dynamic visual transitions, and multi-track audio filtergraphs."""

    def __init__(self, target_width: int = 1080, target_height: int = 1920, target_fps: int = 30):
        self.width = target_width
        self.height = target_height
        self.fps = target_fps

    def build_filtergraph(
        self,
        shots: List[Dict[str, Any]],
        audio_sfx_list: List[Dict[str, Any]] = None,
        ass_subtitles_path: str = None,
        bgm_stream_idx: int = None,
        bgm_volume: float = 0.15,
        ducking_enabled: bool = True,
        watermark_stream_idx: int = None,
        watermark_position: str = "bottom_safe",
        watermark_scale: float = 0.28,
        frame_overlay_stream_idx: int = None,
        viewport: Tuple[int, int, int, int] = None,
    ) -> Tuple[str, str, str]:
        """Construct FFmpeg complex filtergraph for compositing B-roll video transitions,
        kinetic subtitles, frame overlay mask, and multi-track audio mixing with BGM auto-ducking.

        Returns:
            (filtergraph_string, final_video_layer_name, final_audio_layer_name)
        """
        filters = []
        audio_sfx_list = audio_sfx_list or []

        # -------------------------------------------------------------
        # 1. Base Video Normalization (Stream 0:v)
        # -------------------------------------------------------------
        if viewport:
            vp_x, vp_y, vp_w, vp_h = viewport
            scale_and_pad = (
                f"scale={vp_w}:{vp_h}:force_original_aspect_ratio=increase,"
                f"crop={vp_w}:{vp_h},pad={self.width}:{self.height}:{vp_x}:{vp_y}:color=black,setsar=1,fps={self.fps}"
            )
            filters.append(f"[0:v]{scale_and_pad}[base]")
        else:
            scale_and_pad = (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps}"
            )
            filters.append(f"[0:v]{scale_and_pad}[base]")

        current_layer = "base"

        # -------------------------------------------------------------
        # 2. B-Roll Video Overlays with Dynamic Transitions
        # -------------------------------------------------------------
        for idx, shot in enumerate(shots, start=1):
            if not shot.get("asset_path"):
                continue

            broll_stream = f"[{idx}:v]"
            scaled_broll = f"broll_{idx}"
            next_layer = f"layer_{idx}"

            start_t = float(shot["start_time"])
            end_t = float(shot["end_time"])
            duration = max(0.2, end_t - start_t)

            trans = shot.get("transition", {})
            type_in = trans.get("type_in", "dissolve")
            from ai_broll_autopilot.config import Config
            is_streamer_or_meme = (
                shot.get("style") == "meme" or
                any(k in str(shot.get("meme_template", "")).lower() for k in ("speed", "caseoh", "jynx", "homeless", "pornstar", "shave", "doctor", "chad", "harold")) or
                any(k in str(shot.get("search_prompt", "")).lower() for k in ("speed", "caseoh", "jynx", "streamer"))
            )
            speed = float(shot.get("speed") or (Config.STREAMER_SPEED_MULTIPLIER if is_streamer_or_meme else Config.BROLL_SPEED_MULTIPLIER))

            # Snappy fast-paced transitions (0.18s max)
            dur_in = min(0.20, trans.get("duration_in", 0.18))
            dur_out = min(0.20, trans.get("duration_out", 0.18))

            # Apply transition effects with high-velocity speed acceleration
            if type_in == "slide_left":
                # Whip slide in from right
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"{scale_and_pad},"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(1-(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            elif type_in == "slide_right":
                # Whip slide in from left
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"{scale_and_pad},"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(-1+(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            elif type_in == "cut":
                # Direct hard cut
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"{scale_and_pad},"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            else:
                # Default: Smooth crossfade alpha dissolve (in and out) with speedup
                shot_dur = max(0.4, end_t - start_t)
                fade_out_st = max(0.0, shot_dur - dur_out)
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"{scale_and_pad},"
                    f"format=yuva420p,"
                    f"fade=t=in:st=0:d={dur_in:.2f}:alpha=1,"
                    f"fade=t=out:st={fade_out_st:.2f}:d={dur_out:.2f}:alpha=1,"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )

            current_layer = next_layer

        # -------------------------------------------------------------
        # 2b. Campaign Frame Overlay (Torn Paper Mask & Header/Watermark)
        # -------------------------------------------------------------
        if frame_overlay_stream_idx is not None:
            framed_layer = "framed_layer"
            filters.append(
                f"[{current_layer}][{frame_overlay_stream_idx}:v]overlay=0:0:format=auto:shortest=1[{framed_layer}]"
            )
            current_layer = framed_layer

        # -------------------------------------------------------------
        # 3. Campaign Watermark Overlay
        # -------------------------------------------------------------
        if watermark_stream_idx is not None:
            wm_in = f"[{watermark_stream_idx}:v]"
            scale_factor = watermark_scale if watermark_scale else 0.28
            target_wm_w = max(100, int(self.width * scale_factor))
            filters.append(f"{wm_in}scale={target_wm_w}:-1[scaled_wm]")

            if watermark_position == "top_safe":
                ox = "(W-w)/2"
                oy = "160"
            elif watermark_position == "top_left":
                ox = "40"
                oy = "160"
            elif watermark_position == "bottom_left":
                ox = "60"
                oy = "H-h-200"
            else:  # Default bottom_safe (centered, above lower UI and clear of captions)
                ox = "(W-w)/2"
                oy = "H-h-200"

            filters.append(
                f"[{current_layer}][scaled_wm]overlay=x='{ox}':y='{oy}':format=auto:eof_action=repeat[wm_layer]"
            )
            current_layer = "wm_layer"

        # -------------------------------------------------------------
        # 4. Kinetic Subtitle Burn-In (Overlayed on top of all video)
        # -------------------------------------------------------------
        if ass_subtitles_path:
            import os
            from pathlib import Path
            if os.path.exists(ass_subtitles_path):
                clean_ass = str(Path(ass_subtitles_path).resolve()).replace('\\', '/').replace(':', '\\:')
                filters.append(f"[{current_layer}]subtitles='{clean_ass}'[subbed_v]")
                current_layer = "subbed_v"

        # -------------------------------------------------------------
        # 4. Multi-Track Audio Mixing (Dialogue + SFX + BGM Ducking)
        # -------------------------------------------------------------
        final_audio_layer = "final_a"
        mix_streams = ["[base_a]"]
        filters.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[base_a]")

        # 4a. Transition stingers & Foley SFX
        if audio_sfx_list:
            audio_inputs_start = (
                1 + len(shots)
                + (1 if frame_overlay_stream_idx is not None else 0)
                + (1 if watermark_stream_idx is not None else 0)
            )
            for a_idx, sfx_item in enumerate(audio_sfx_list):
                stream_in = f"[{audio_inputs_start + a_idx}:a]"
                stream_out = f"sfx_{a_idx}"
                delay_ms = int(max(0.0, sfx_item["start_time"]) * 1000)
                vol = float(sfx_item.get("volume", 0.40))

                filters.append(
                    f"{stream_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol:.2f},"
                    f"adelay={delay_ms}|{delay_ms}[{stream_out}]"
                )
                mix_streams.append(f"[{stream_out}]")

        # 4b. Background Music (BGM) with Auto-Ducking
        if bgm_stream_idx is not None:
            bgm_in = f"[{bgm_stream_idx}:a]"
            vol_val = max(0.02, min(0.60, bgm_volume))
            if ducking_enabled:
                # Dynamic sidechain compression: ducks BGM volume when speaker talks
                filters.append(
                    f"{bgm_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol_val:.2f}[bgm_pre]"
                )
                filters.append(
                    f"[bgm_pre][base_a]sidechaincompress=threshold=0.07:ratio=5:attack=40:release=350[bgm_ducked]"
                )
                mix_streams.append("[bgm_ducked]")
            else:
                filters.append(
                    f"{bgm_in}aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"volume={vol_val:.2f}[bgm_ducked]"
                )
                mix_streams.append("[bgm_ducked]")

        # Final audio mix
        total_audio_inputs = len(mix_streams)
        if total_audio_inputs > 1:
            filters.append(
                f"{''.join(mix_streams)}amix=inputs={total_audio_inputs}:duration=first:dropout_transition=0:normalize=0[final_a]"
            )
        else:
            final_audio_layer = "base_a"

        return ";".join(filters), current_layer, final_audio_layer
