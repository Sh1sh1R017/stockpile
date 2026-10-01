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
        behind_subject_text: Dict[str, Any] = None,
        subject_matte_stream_idx: int = None,
        behind_subject_ass_path: str = None,
        layout_mode: str = "single",
        cyber_grid_backdrop_idx: int = None,
        cyber_grid_mask_before_idx: int = None,
        cyber_grid_mask_after_idx: int = None,
        reference_style: bool = False,
        reference_card_mask_idx: int = None,
        reference_card_width_ratio: float = 0.944,
        reference_card_height_ratio: float = 0.574,
        reference_card_radius: int = 52,
        output_duration: float = None,
    ) -> Tuple[str, str, str]:
        """Construct FFmpeg complex filtergraph for compositing B-roll video transitions,
        subject-aware typography and behind-subject captions, frame overlay mask, and multi-track audio mixing with BGM auto-ducking.

        Returns:
            (filtergraph_string, final_video_layer_name, final_audio_layer_name)
        """
        filters = []
        audio_sfx_list = audio_sfx_list or []
        active_broll_intervals = []

        reference_mask_labels = []
        active_shot_indices = [
            int(shot.get("_input_idx", i))
            for i, shot in enumerate(shots, start=1)
            if shot.get("asset_path")
        ]
        if reference_style and reference_card_mask_idx is not None:
            reference_mask_labels = ["ref_mask_0"] + [
                f"ref_mask_{i}" for i in active_shot_indices
            ]
            filters.append(
                f"[{reference_card_mask_idx}:v]fps={self.fps},format=gray,"
                f"split={len(reference_mask_labels)}"
                + "".join(f"[{label}]" for label in reference_mask_labels)
            )

        # -------------------------------------------------------------
        # 1. Base Video Normalization & Layout Setup
        # -------------------------------------------------------------
        if layout_mode == "before_after_cyber_grid" and cyber_grid_backdrop_idx is not None:
            # Dual-card Cyber Grid Before & After Compositing
            filters.append("[0:v]split=2[v_raw][v_proc]")

            # Left Card: BEFORE (352x600, raw video, rounded corners)
            filters.append(
                f"[v_raw]scale=352:600:force_original_aspect_ratio=increase,crop=352:600,setsar=1,fps={self.fps}[v_b_crop]"
            )
            filters.append(f"[{cyber_grid_mask_before_idx}:v]scale=352:600[m_b]")
            filters.append("[v_b_crop][m_b]alphamerge[v_before]")

            # Right Card: AFTER (600x1060, punch-in zoom 1.40x, color grading, cutaway B-roll overlays, rounded corners)
            filters.append(
                f"[v_proc]scale=600*1.40:1060*1.40:force_original_aspect_ratio=increase,"
                f"crop=600:1060:(in_w-600)/2:min(in_h-1060\\,in_h*0.10),setsar=1,fps={self.fps},"
                f"eq=contrast=1.20:saturation=1.28:brightness=-0.02,unsharp=5:5:0.8:5:5:0.0[v_a_graded]"
            )

            # Overlay B-roll shots inside the AFTER card
            current_after = "v_a_graded"
            for idx, shot in enumerate(shots, start=1):
                if not shot.get("asset_path"):
                    continue
                start_t = float(shot["start_time"])
                end_t = float(shot["end_time"])
                active_broll_intervals.append((start_t, end_t))
                speed = float(shot.get("speed") or 1.0)
                input_idx = int(shot.get("_input_idx", idx))
                broll_stream = f"[{input_idx}:v]"
                scaled_broll = f"broll_after_{idx}"
                next_after = f"after_layer_{idx}"
                filters.append(
                    f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                    f"scale=600:1060:force_original_aspect_ratio=increase,crop=600:1060,setsar=1,fps={self.fps},"
                    f"setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_after}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_after}]"
                )
                current_after = next_after

            # Apply rounded corner alpha mask to the AFTER card
            filters.append(f"[{cyber_grid_mask_after_idx}:v]scale=600:1060[m_a]")
            filters.append(f"[{current_after}][m_a]alphamerge[v_after]")

            # Composite both cards onto the 1080x1920 cyber grid backdrop
            filters.append(
                f"[{cyber_grid_backdrop_idx}:v]scale={self.width}:{self.height},setsar=1,fps={self.fps}[bg_canvas]"
            )
            filters.append("[bg_canvas][v_before]overlay=64:550:eof_action=pass[comp_b]")
            filters.append("[comp_b][v_after]overlay=440:320:eof_action=pass[cyber_comp]")
            current_layer = "cyber_comp"
        else:
            if reference_style and reference_card_mask_idx is not None:
                # Reference style: a centered editorial card on a near-black canvas.
                # Measurements are based on the supplied final edit: ~94% canvas width
                # and ~57% canvas height, with strongly rounded corners.
                card_w = int(round(self.width * reference_card_width_ratio))
                card_h = int(round(self.height * reference_card_height_ratio))
                card_w -= card_w % 2
                card_h -= card_h % 2
                card_x = (self.width - card_w) // 2
                card_y = (self.height - card_h) // 2

                reference_scale = (
                    f"scale={card_w}:{card_h}:force_original_aspect_ratio=increase,"
                    f"crop={card_w}:{card_h},setsar=1,fps={self.fps},"
                    f"eq=contrast=1.05:saturation=1.03:brightness=-0.01"
                )
                filters.append(f"[0:v]{reference_scale}[base_card]")
                filters.append("[base_card][ref_mask_0]alphamerge[base_card_rounded]")
                filters.append(
                    f"color=c=#050505:s={self.width}x{self.height}:r={self.fps}:d={max(1.0, float(output_duration or 30.0)):.3f}[reference_canvas]"
                )
                filters.append(
                    f"[reference_canvas][base_card_rounded]overlay={card_x}:{card_y}:eof_action=pass[base]"
                )

                scale_and_pad = (
                    f"scale={card_w}:{card_h}:force_original_aspect_ratio=increase,"
                    f"crop={card_w}:{card_h},setsar=1,fps={self.fps},"
                    f"eq=contrast=1.05:saturation=1.03:brightness=-0.01"
                )
                current_layer = "base"
            elif viewport:
                vp_x, vp_y, vp_w, vp_h = viewport
                scale_and_pad = (
                    f"scale={vp_w}:{vp_h}:force_original_aspect_ratio=increase,"
                    f"crop={vp_w}:{vp_h},pad={self.width}:{self.height}:{vp_x}:{vp_y}:color=black,setsar=1,fps={self.fps}"
                )
                filters.append(f"[0:v]{scale_and_pad}[base]")
                current_layer = "base"
            else:
                scale_and_pad = (
                    f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps}"
                )
                filters.append(f"[0:v]{scale_and_pad}[base]")
                current_layer = "base"

            # If subject matte compositing is enabled, split base into background and subject foreground source
            uses_subject_source = (
                subject_matte_stream_idx is not None
                and not reference_style
                and (
                    (behind_subject_text and behind_subject_text.get("text") and not behind_subject_ass_path)
                    or (behind_subject_ass_path and __import__("os").path.exists(behind_subject_ass_path))
                )
            )
            if uses_subject_source:
                filters.append("[base]split=2[base_bg][subject_src]")
                current_layer = "base_bg"

        # -------------------------------------------------------------
        # 1b. Backward-Compatible Subject-Aware Layered Text Overlay
        # -------------------------------------------------------------
        if behind_subject_text and behind_subject_text.get("text") and not behind_subject_ass_path:
            raw_text = (
                str(behind_subject_text.get("text", ""))
                .replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace(":", "\\:")
                .replace("%", "\\%")
                .replace(",", "\\,")
            )
            t_start = float(behind_subject_text.get("start_time", 0.5))
            t_dur = float(behind_subject_text.get("duration", 2.5))
            t_end = t_start + t_dur
            pos_y = float(behind_subject_text.get("transform", {}).get("position", {}).get("y", 0.28))
            font_size = int(behind_subject_text.get("style", {}).get("fontSize", 68))
            font_color = behind_subject_text.get("style", {}).get("color", "yellow")
            if font_color.startswith("#"):
                font_color = "0x" + font_color[1:]

            from ai_broll_autopilot.config import Config
            font_path = str(getattr(Config, "FONT_PATH", "") or "")
            if font_path:
                font_path = font_path.replace("\\", "\\\\").replace(":", "\\:")
            fontfile_opt = f":fontfile='{font_path}'" if font_path else ""
            drawtext_flt = (
                f"drawtext=text='{raw_text}':fontsize={font_size}:fontcolor={font_color}{fontfile_opt}:"
                f"bordercolor=black:borderw=5:x=(w-text_w)/2:y={int(self.height * pos_y)}:"
                f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
            )

            if subject_matte_stream_idx is not None:
                filters.append(f"[{current_layer}]{drawtext_flt}[bg_with_text]")
                filters.append(
                    f"[{subject_matte_stream_idx}:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},format=gray[subject_mask]"
                )
                filters.append(f"[subject_src][subject_mask]alphamerge[subject_fg]")
                filters.append(
                    f"[bg_with_text][subject_fg]overlay=0:0:enable='between(t,{t_start:.2f},{t_end:.2f})':eof_action=pass[layer_subj_comp]"
                )
                current_layer = "layer_subj_comp"
            else:
                filters.append(f"[{current_layer}]{drawtext_flt}[layer_subj_txt]")
                current_layer = "layer_subj_txt"

        # -------------------------------------------------------------
        # 2. B-Roll Video Overlays with Dynamic Transitions (Single Layout)
        # -------------------------------------------------------------
        if layout_mode != "before_after_cyber_grid":
            for idx, shot in enumerate(shots, start=1):
                if not shot.get("asset_path"):
                    continue

                input_idx = int(shot.get("_input_idx", idx))
                broll_stream = f"[{input_idx}:v]"
                scaled_broll = f"broll_{input_idx}"
                next_layer = f"layer_{idx}"

                start_t = float(shot["start_time"])
                end_t = float(shot["end_time"])
                active_broll_intervals.append((start_t, end_t))
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

                if reference_style:
                    type_in = "cut"

                # Snappy fast-paced transitions (0.18s max)
                dur_in = max(0.0, min(0.20, float(trans.get("duration_in", 0.18) or 0.0)))
                dur_out = max(0.0, min(0.20, float(trans.get("duration_out", 0.18) or 0.0)))
                if type_in in {"slide_left", "slide_right"} and dur_in <= 0.0:
                    type_in = "cut"
                if type_in != "cut":
                    dur_in = max(0.001, dur_in)
                if type_in == "dissolve":
                    dur_out = max(0.001, dur_out)

                # Apply transition effects with high-velocity speed acceleration
                if reference_style:
                    reference_card_label = f"broll_ref_card_{input_idx}"
                    mask_label = f"ref_mask_{input_idx}" if input_idx in active_shot_indices else None
                    filters.append(
                        f"{broll_stream}setpts=(PTS-STARTPTS)/{speed:.2f},"
                        f"{scale_and_pad},setpts=PTS+{start_t:.2f}/TB[{scaled_broll}]"
                    )
                    if mask_label:
                        filters.append(
                            f"[{scaled_broll}][{mask_label}]alphamerge[{reference_card_label}]"
                        )
                    else:
                        reference_card_label = scaled_broll
                    filters.append(
                        f"[{current_layer}][{reference_card_label}]"
                        f"overlay=x='(W-w)/2':y='(H-h)/2':"
                        f"enable='between(t,{start_t:.2f},{end_t:.2f})':"
                        f"eof_action=pass[{next_layer}]"
                    )
                elif type_in == "slide_left":
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
        # 2c. Subject-Aware Layered Caption Compositing (Captions Behind Subject)
        # -------------------------------------------------------------
        if behind_subject_ass_path:
            import os
            from pathlib import Path
            if os.path.exists(behind_subject_ass_path):
                clean_behind_ass = str(Path(behind_subject_ass_path).resolve()).replace('\\', '/').replace(':', '\\:')
                # Burn behind-subject captions onto the composed background
                filters.append(f"[{current_layer}]subtitles='{clean_behind_ass}'[caption_under_subject]")

                if subject_matte_stream_idx is not None:
                    # Prepare subject mask from matte stream
                    filters.append(
                        f"[{subject_matte_stream_idx}:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                        f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},format=gray[subject_mask]"
                    )
                    # Merge A-roll RGB with alpha mask to get isolated foreground subject
                    filters.append(f"[subject_src][subject_mask]alphamerge[subject_fg]")

                    # B-Roll occlusion protection: ensure A-roll subject does NOT appear over active B-roll
                    if active_broll_intervals:
                        broll_cond = "+".join(f"between(t,{st:.2f},{et:.2f})" for st, et in active_broll_intervals)
                        enable_expr = f":enable='not({broll_cond})'"
                    else:
                        enable_expr = ""

                    filters.append(
                        f"[caption_under_subject][subject_fg]overlay=0:0{enable_expr}:eof_action=pass[subject_caption_layer]"
                    )
                    current_layer = "subject_caption_layer"
                else:
                    # Graceful fallback: keep captions visible without subject occlusion
                    current_layer = "caption_under_subject"

        # -------------------------------------------------------------
        # 3. Normal Kinetic Subtitle Burn-In (Overlayed on top of subject layer)
        # -------------------------------------------------------------
        if ass_subtitles_path:
            import os
            from pathlib import Path
            if os.path.exists(ass_subtitles_path):
                clean_ass = str(Path(ass_subtitles_path).resolve()).replace('\\', '/').replace(':', '\\:')
                filters.append(f"[{current_layer}]subtitles='{clean_ass}'[subbed_v]")
                current_layer = "subbed_v"

        # -------------------------------------------------------------
        # 4. Campaign Frame Overlay (Torn Paper Mask & Header/Watermark)
        # -------------------------------------------------------------
        if frame_overlay_stream_idx is not None:
            framed_layer = "framed_layer"
            filters.append(
                f"[{current_layer}][{frame_overlay_stream_idx}:v]overlay=0:0:format=auto:shortest=1[{framed_layer}]"
            )
            current_layer = framed_layer

        # -------------------------------------------------------------
        # 5. Campaign Watermark Overlay
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
        # 4. Multi-Track Audio Mixing (Dialogue + SFX + BGM Ducking)
        # -------------------------------------------------------------
        final_audio_layer = "final_a"
        filters.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[base_a_raw]")
        need_ducking = bgm_stream_idx is not None and ducking_enabled
        if need_ducking:
            filters.append("[base_a_raw]asplit=2[base_a][base_a_sc]")
        else:
            filters.append("[base_a_raw]anull[base_a]")
        mix_streams = ["[base_a]"]

        # 4a. Transition stingers & Foley SFX
        if audio_sfx_list:
            used_video_indices = [
                i for i in [
                    frame_overlay_stream_idx,
                    watermark_stream_idx,
                    subject_matte_stream_idx,
                    cyber_grid_backdrop_idx,
                    cyber_grid_mask_before_idx,
                    cyber_grid_mask_after_idx,
                    reference_card_mask_idx,
                ] if i is not None
            ]
            audio_inputs_start = (
                max([0, len(shots)] + used_video_indices) + 1
                if used_video_indices
                else 1 + len(shots)
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
                    f"[bgm_pre][base_a_sc]sidechaincompress=threshold=0.07:ratio=5:attack=40:release=350[bgm_ducked]"
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
