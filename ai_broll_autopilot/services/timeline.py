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
        audio_sfx_list: List[Dict[str, Any]] = None
    ) -> Tuple[str, str, str]:
        """Construct FFmpeg complex filtergraph for compositing B-roll video transitions and audio mixing.

        Returns:
            (filtergraph_string, final_video_layer_name, final_audio_layer_name)
        """
        filters = []
        audio_sfx_list = audio_sfx_list or []

        # -------------------------------------------------------------
        # 1. Base Video Normalization (Stream 0:v)
        # -------------------------------------------------------------
        filters.append(
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
            f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps}[base]"
        )

        current_layer = "base"

        # -------------------------------------------------------------
        # 2. B-Roll Video Overlays with Dynamic Transitions
        # -------------------------------------------------------------
        # In FFmpeg cmd, input 0 is base video.
        # B-roll videos will be inputs 1 .. len(shots).
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
            dur_in = min(0.35, trans.get("duration_in", 0.3))
            type_out = trans.get("type_out", "dissolve")
            dur_out = min(0.35, trans.get("duration_out", 0.3))

            # Apply transition effects
            if type_in == "slide_left":
                # Whip slide in from right
                filters.append(
                    f"{broll_stream}scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},"
                    f"setpts=PTS-STARTPTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(1-(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            elif type_in == "slide_right":
                # Whip slide in from left
                filters.append(
                    f"{broll_stream}scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},"
                    f"setpts=PTS-STARTPTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                slide_expr = f"if(lt(t,{start_t:.2f}+{dur_in:.2f}),(-1+(t-{start_t:.2f})/{dur_in:.2f})*W,0)"
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=x='{slide_expr}':y=0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            elif type_in == "cut":
                # Direct hard cut
                filters.append(
                    f"{broll_stream}scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},"
                    f"setpts=PTS-STARTPTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )
            else:
                # Default: Smooth crossfade alpha dissolve (in and out)
                shot_dur = max(0.5, end_t - start_t)
                fade_out_st = max(0.0, shot_dur - dur_out)
                filters.append(
                    f"{broll_stream}scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self.fps},"
                    f"format=yuva420p,"
                    f"fade=t=in:st=0:d={dur_in:.2f}:alpha=1,"
                    f"fade=t=out:st={fade_out_st:.2f}:d={dur_out:.2f}:alpha=1,"
                    f"setpts=PTS-STARTPTS+{start_t:.2f}/TB[{scaled_broll}]"
                )
                filters.append(
                    f"[{current_layer}][{scaled_broll}]overlay=0:0:enable='between(t,{start_t:.2f},{end_t:.2f})':eof_action=pass[{next_layer}]"
                )

            current_layer = next_layer

        # -------------------------------------------------------------
        # 3. Multi-Track Audio Mixing (Dialogue + SFX + Stingers)
        # -------------------------------------------------------------
        final_audio_layer = "final_a"

        if not audio_sfx_list:
            # No additional SFX: pass base audio
            filters.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo[final_a]")
        else:
            # Inputs offset: 0 is base video, 1..len(shots) are B-rolls
            # Audio SFX inputs start at 1 + len(shots)
            audio_inputs_start = 1 + len(shots)
            mix_streams = ["[base_a]"]
            filters.append("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[base_a]")

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

            # Mix all streams together
            total_audio_inputs = len(mix_streams)
            filters.append(
                f"{''.join(mix_streams)}amix=inputs={total_audio_inputs}:duration=first:dropout_transition=0:normalize=0[final_a]"
            )

        return ";".join(filters), current_layer, final_audio_layer
