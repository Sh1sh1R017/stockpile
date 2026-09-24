"""Kinetic Subtitle Engine generating styled word-by-word highlighted captions.

Implements viral short-form caption styling (Alex Hormozi Yellow, MrBeast Neon Green,
and Clean White) using Advanced SubStation Alpha (.ass) format with sub-second word sync.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def format_ass_timestamp(seconds: float) -> str:
    """Format float seconds to ASS timestamp format (H:MM:SS.cc)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    csecs = int(round((seconds - int(seconds)) * 100))
    if csecs >= 100:
        secs += 1
        csecs -= 100
    return f"{hrs}:{mins:02d}:{secs:02d}.{csecs:02d}"


class SubtitleEngine:
    """Generates viral kinetic subtitles in .ass format for FFmpeg burn-in."""

    PRESETS = {
        "hormozi": {
            "name": "Hormozi Punch",
            "active_color": "&H0000FFFF&",    # Bright Yellow in BGR (&HAABBGGRR)
            "inactive_color": "&H00FFFFFF&",  # White
            "outline_color": "&H00000000&",   # Black outline
            "font_name": "Impact",
            "font_size": 76,
            "outline_width": 5.5,
            "shadow_offset": 3.0,
            "uppercase": True,
            "words_per_group": 3,
        },
        "beast": {
            "name": "MrBeast Neon",
            "active_color": "&H0033FF00&",    # Neon Green in BGR
            "inactive_color": "&H00FFFFFF&",
            "outline_color": "&H00000000&",
            "font_name": "Impact",
            "font_size": 76,
            "outline_width": 5.5,
            "shadow_offset": 3.0,
            "uppercase": True,
            "words_per_group": 3,
        },
        "mrbeast": {
            "name": "MrBeast Neon",
            "active_color": "&H0033FF00&",    # Neon Green in BGR
            "inactive_color": "&H00FFFFFF&",
            "outline_color": "&H00000000&",
            "font_name": "Impact",
            "font_size": 76,
            "outline_width": 5.5,
            "shadow_offset": 3.0,
            "uppercase": True,
            "words_per_group": 3,
        },
        "clean": {
            "name": "Clean White",
            "active_color": "&H0000FFFF&",
            "inactive_color": "&H00F0F0F0&",
            "outline_color": "&H00000000&",
            "font_name": "Arial",
            "font_size": 68,
            "outline_width": 4.0,
            "shadow_offset": 2.0,
            "uppercase": False,
            "words_per_group": 4,
        },
        "curious_clean": {
            "name": "Curious Mike Benchmark (Yellow Badge)",
            "active_color": "&H0014D5E9&",    # Bright Canary Yellow in BGR (&HAABBGGRR)
            "inactive_color": "&H00FFFFFF&",  # Pure crisp white
            "outline_color": "&H00000000&",   # Dark outline for legibility
            "font_name": "Arial Black",       # Heavy punchy sans
            "font_size": 54,
            "outline_width": 3.5,
            "shadow_offset": 2.0,
            "uppercase": True,
            "words_per_group": 3,
            "box_badge": True,
        }
    }

    def __init__(self, target_width: int = 1080, target_height: int = 1920):
        self.width = target_width
        self.height = target_height

    def generate_ass_file(
        self,
        segments: List[Dict[str, Any]],
        output_path: Path,
        style_preset: str = "hormozi",
        position: str = "bottom",
        custom_margin_v: Optional[int] = None,
        hook_text: Optional[str] = None,
        hook_duration: Optional[float] = None,
        suppress_hook: bool = False,
        text_emphasis_events: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """Generate an .ass file with kinetic active-word highlighting and optional Level 3 emphasis graphics."""
        cfg = self.PRESETS.get(style_preset.lower(), self.PRESETS["hormozi"])
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Alignment: 2 = bottom-center, 5 = middle-center, 8 = top-center
        margin_v = custom_margin_v if custom_margin_v is not None else 280
        align = 2
        if position == "center":
            align = 5
            margin_v = 0
        elif position == "top":
            align = 8
            margin_v = custom_margin_v if custom_margin_v is not None else 280

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.width}
PlayResY: {self.height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kinetic,{cfg['font_name']},{cfg['font_size']},{cfg['inactive_color']},{cfg['active_color']},{cfg['outline_color']},&H80000000,-1,0,0,0,100,100,1,0,1,{cfg['outline_width']},{cfg['shadow_offset']},{align},40,40,{margin_v},1
Style: Hook,Impact,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5.0,2.5,8,40,40,160,1
Style: Level3Yellow,Arial Black,110,&H0014D5E9&,&H0014D5E9&,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8.0,4.0,5,40,40,0,1
Style: Level3Pink,Arial Black,110,&H005500FF&,&H005500FF&,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8.0,4.0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        if not suppress_hook and hook_text and hook_text.strip():
            h_dur = hook_duration if hook_duration else 45.0
            h_start = "0:00:00.00"
            h_end = format_ass_timestamp(h_dur)
            clean_hook = hook_text.strip().upper()
            events.append(f"Dialogue: 1,{h_start},{h_end},Hook,,0,0,0,,{clean_hook}")

        if text_emphasis_events:
            for ev in text_emphasis_events:
                st = format_ass_timestamp(float(ev["start_time"]))
                et = format_ass_timestamp(float(ev["start_time"]) + float(ev.get("duration", 1.2)))
                style_name = "Level3Pink" if ev.get("color") == "pink" else "Level3Yellow"
                raw_text = ev.get("text", "").strip()
                clean_text = raw_text.replace("\n", "\\N")
                anim = "{\\fscx85\\fscy85\\t(0,120,\\fscx115\\fscy115)\\t(120,240,\\fscx100\\fscy100)}"
                events.append(f"Dialogue: 2,{st},{et},{style_name},,0,0,0,,{anim}{clean_text}")

        words_per_group = cfg["words_per_group"]

        # Flatten word stream
        all_words: List[Dict[str, Any]] = []
        for seg in segments:
            seg_words = seg.get("words", [])
            if seg_words:
                all_words.extend(seg_words)
            else:
                # Fallback: estimate word timings uniformly across segment
                seg_text = seg.get("text", "").strip()
                tokens = seg_text.split()
                if tokens:
                    s = float(seg.get("start", 0.0))
                    e = float(seg.get("end", s + 1.5))
                    dur_per = (e - s) / len(tokens)
                    for i, tok in enumerate(tokens):
                        all_words.append({
                            "word": tok,
                            "start": round(s + i * dur_per, 2),
                            "end": round(s + (i + 1) * dur_per, 2),
                        })

        if not all_words:
            logger.warning("No words found to generate subtitles.")
            output_path.write_text(header, encoding="utf-8")
            return output_path

        # Chunk words into groups of 2 to 4 words for short-form pacing
        word_groups: List[List[Dict[str, Any]]] = []
        current_group = []

        for w in all_words:
            w_text = w.get("word", "").strip()
            if not w_text:
                continue
            current_group.append(w)
            # Break group on comma, period, question, or limit
            if len(current_group) >= words_per_group or w_text[-1] in {".", "!", "?", ","}:
                word_groups.append(current_group)
                current_group = []

        if current_group:
            word_groups.append(current_group)

        # Generate active highlight lines for each group
        for group in word_groups:
            if not group:
                continue

            for active_idx, active_word in enumerate(group):
                start_str = format_ass_timestamp(float(active_word["start"]))
                end_str = format_ass_timestamp(float(active_word["end"]))

                # Format text with previous words, active word, and next words
                formatted_words = []
                is_box_badge = cfg.get("box_badge", False)
                for idx, item in enumerate(group):
                    word_str = item["word"].upper() if cfg["uppercase"] else item["word"]
                    if idx == active_idx:
                        if is_box_badge:
                            # Signature Curious Mike yellow filled badge with black text
                            formatted_words.append(
                                f"{{\\1c&H00000000&\\3c{cfg['active_color']}\\bord20\\fscx104\\fscy104}} {word_str} "
                                f"{{\\1c{cfg['inactive_color']}\\3c{cfg['outline_color']}\\bord{cfg['outline_width']}\\fscx100\\fscy100}}"
                            )
                        else:
                            # Highlighted active word with scale pop
                            formatted_words.append(
                                f"{{\\c{cfg['active_color']}\\fscx108\\fscy108}}{word_str}{{\\c{cfg['inactive_color']}\\fscx100\\fscy100}}"
                            )
                    else:
                        formatted_words.append(word_str)

                line_text = " ".join(formatted_words)
                events.append(f"Dialogue: 0,{start_str},{end_str},Kinetic,,0,0,0,,{line_text}")

        # Sort all dialogue events chronologically so libass streams them without skipping
        def _get_start_sec(line: str) -> float:
            try:
                tokens = line.split(",")
                t_str = tokens[1].strip()
                h, m, sc = t_str.split(":")
                s, c = sc.split(".")
                return int(h) * 3600 + int(m) * 60 + int(s) + int(c) / 100.0
            except Exception:
                return 0.0

        events.sort(key=_get_start_sec)

        full_ass = header + "\n".join(events) + "\n"
        output_path.write_text(full_ass, encoding="utf-8")
        logger.info(f"Generated {len(events)} kinetic subtitle events in {output_path.name}")
        return output_path
