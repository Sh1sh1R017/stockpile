"""Caption Layer Compiler for Stockpile.

Compiles canonical CaptionEvents and transcript segments into multi-track ASS subtitle layers:
  1. NORMAL_CAPTION_EVENTS (top kinetic captions, above subject)
  2. HOOK_ABOVE_SUBJECT_EVENTS (hook words staying above subject)
  3. HOOK_BEHIND_SUBJECT_EVENTS (hook words rendered beneath subject, occluded by person matte)

Conforms to the canonical EditPlan architecture and seamlessly integrates with
the Timeline compositor (FFmpeg alphamerge) and OpenReel multitrack timeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ai_broll_autopilot.services.razor_caption.caption_event import (
    CaptionEvent, CaptionMode, EmphasisLevel, LayerMode, AnimationType, SpatialRegion
)
from ai_broll_autopilot.services.razor_caption.engine import RazorCaptionEngine
from ai_broll_autopilot.services.razor_caption.presets import (
    get_preset, map_word_to_emoji, ZapCapPreset, ZAPCAP_PRESETS
)
from ai_broll_autopilot.services.subject_caption import (
    annotate_segments_for_subject_captions, has_behind_subject_segments
)
from ai_broll_autopilot.services.subtitle_engine import (
    SubtitleEngine, format_ass_timestamp
)
from ai_broll_autopilot.services.subject_isolation import subject_isolation_service

logger = logging.getLogger(__name__)


def hex_to_ass_color(hex_str: str, alpha: int = 0) -> str:
    """Convert #RRGGBB hex string to &HAABBGGRR ASS color format."""
    if not hex_str:
        return f"&H{alpha:02X}FFFFFF&"
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H{alpha:02X}{b}{g}{r}&"
    elif len(h) == 3:
        r, g, b = h[0] * 2, h[1] * 2, h[2] * 2
        return f"&H{alpha:02X}{b}{g}{r}&"
    return f"&H{alpha:02X}FFFFFF&"


class SemanticLayer(str, Enum):
    NORMAL_CAPTION = "normal_caption"
    HOOK_ABOVE_SUBJECT = "hook_above_subject"
    HOOK_BEHIND_SUBJECT = "hook_behind_subject"


@dataclass
class CompiledCaptionLayers:
    """Result of caption layer compilation."""
    normal_ass_path: Optional[str]
    behind_subject_ass_path: Optional[str]
    subject_matte_path: Optional[str]
    requires_matte: bool
    behind_event_count: int
    normal_event_count: int


class CaptionCompositor:
    """Dedicated compiler for semantic caption layers and behind-subject hook compositing."""

    def __init__(self, target_width: int = 1080, target_height: int = 1920):
        self.width = target_width
        self.height = target_height
        self.sub_engine = SubtitleEngine(target_width=target_width, target_height=target_height)
        self.razor_engine = RazorCaptionEngine()

    async def prepare_caption_render_assets(
        self,
        source_video: str,
        edit_plan: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        work_dir: Path,
        style_preset: str = "hormozi",
        position: str = "bottom",
        custom_margin_v: Optional[int] = None,
        hook_text: Optional[str] = None,
        hook_duration: Optional[float] = None,
        suppress_hook: bool = False,
        text_emphasis_events: Optional[List[Dict[str, Any]]] = None,
        caption_motion: str = "word-pop",
        sample_fps: Optional[float] = None,
        custom_colors: Optional[Dict[str, str]] = None,
        enable_emojis: bool = True,
        words_per_beat: int = 3,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Main entry point to compile caption layers and generate person matte if needed.

        Returns:
            Tuple of (normal_ass_path, behind_subject_ass_path, subject_matte_path).
            If behind-subject is disabled or not needed, (normal_ass_path, None, None) is returned.
        """
        logger.info("[CAPTION-COMPOSITOR] Starting ZapCap caption layer compilation...")
        render_settings = edit_plan.get("render_settings", {}) if edit_plan else {}
        subtitles_enabled = render_settings.get("subtitles_enabled", True)
        if not subtitles_enabled or not transcript_segments:
            logger.info("[CAPTION-COMPOSITOR] Subtitles disabled or no transcript segments.")
            return None, None, None

        if "subtitles_behind_subject" in render_settings:
            behind_subject_enabled = bool(render_settings["subtitles_behind_subject"])
        elif edit_plan and "subtitles_behind_subject" in edit_plan:
            behind_subject_enabled = bool(edit_plan["subtitles_behind_subject"])
        else:
            # New jobs get the reference-style hook treatment by default. An
            # explicit False from the editor still disables it.
            behind_subject_enabled = True

        preset_key = render_settings.get("subtitle_style") or render_settings.get("preset") or style_preset or "hormozi"
        resolved_colors = custom_colors or render_settings.get("custom_colors") or (edit_plan.get("style", {}).get("colors"))
        emojis_flag = render_settings.get("enable_emojis", enable_emojis)
        wpb = int(render_settings.get("words_per_beat", words_per_beat))

        # 1. Determine if Rapid Razor captions should be compiled
        razor_events = self._resolve_razor_events(
            edit_plan=edit_plan,
            transcript_segments=transcript_segments,
            hook_text=hook_text,
            behind_subject_enabled=behind_subject_enabled,
            preset_name=preset_key,
            custom_colors=resolved_colors,
            enable_emojis=emojis_flag,
            words_per_beat=wpb,
        )

        if razor_events:
            return await self._compile_from_razor_events(
                source_video=source_video,
                razor_events=razor_events,
                work_dir=work_dir,
                style_preset=preset_key,
                position=position,
                custom_margin_v=custom_margin_v,
                behind_subject_enabled=behind_subject_enabled,
                sample_fps=sample_fps,
                custom_colors=resolved_colors,
                enable_emojis=emojis_flag,
            )

        # 2. Legacy / standard subtitle fallback
        return await self._compile_from_legacy_subtitles(
            source_video=source_video,
            edit_plan=edit_plan,
            transcript_segments=transcript_segments,
            work_dir=work_dir,
            style_preset=style_preset,
            position=position,
            custom_margin_v=custom_margin_v,
            hook_text=hook_text,
            hook_duration=hook_duration,
            suppress_hook=suppress_hook,
            text_emphasis_events=text_emphasis_events,
            caption_motion=caption_motion,
            behind_subject_enabled=behind_subject_enabled,
            sample_fps=sample_fps,
        )

    def _resolve_razor_events(
        self,
        edit_plan: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        hook_text: Optional[str] = None,
        behind_subject_enabled: bool = False,
        preset_name: str = "hormozi",
        custom_colors: Optional[Dict[str, str]] = None,
        enable_emojis: bool = True,
        words_per_beat: int = 3,
    ) -> List[CaptionEvent]:
        """Retrieve existing or compute canonical Razor CaptionEvents."""
        raw_razor = edit_plan.get("razor_captions", []) if edit_plan else []

        events: List[CaptionEvent] = []
        if raw_razor:
            # Reconstruct typed CaptionEvent objects from edit_plan entries
            for r in raw_razor:
                emp_data = r.get("emphasis", {})
                emp_lvl = emp_data.get("level", 0)
                try:
                    emp_enum = EmphasisLevel(emp_lvl)
                except Exception:
                    emp_enum = EmphasisLevel.NORMAL

                layer_val = r.get("layer", "above_subject")
                try:
                    layer_enum = LayerMode(layer_val)
                except Exception:
                    layer_enum = LayerMode.ABOVE_SUBJECT

                pos_data = r.get("position", {})
                anim_data = r.get("animation", {})
                try:
                    anim_enter = AnimationType(anim_data.get("enter", "snap"))
                except Exception:
                    anim_enter = AnimationType.SNAP
                try:
                    anim_exit = AnimationType(anim_data.get("exit", "snap"))
                except Exception:
                    anim_exit = AnimationType.SNAP

                ev = CaptionEvent(
                    word=r.get("text", r.get("word", "")),
                    start_time=float(r.get("start", 0.0)),
                    end_time=float(r.get("end", 0.0)),
                    duration=float(r.get("end", 0.0)) - float(r.get("start", 0.0)),
                    emphasis=emp_enum,
                    layer=layer_enum,
                    position_x=float(pos_data.get("x", 0.5)),
                    position_y=float(pos_data.get("y", 0.85)),
                    position_reason=pos_data.get("reason", ""),
                    enter_animation=anim_enter,
                    exit_animation=anim_exit,
                    enter_duration_ms=int(anim_data.get("enter_ms", 120)),
                    exit_duration_ms=int(anim_data.get("exit_ms", 80)),
                    emphasis_scale=float(emp_data.get("scale", 1.0)),
                    fill_color=emp_data.get("fill_color", "#FFFFFF"),
                    accent_color=emp_data.get("accent_color", "#FFE600"),
                    font_weight=emp_data.get("font_weight", "Bold"),
                    font_size_scale=float(emp_data.get("font_size_scale", 1.0)),
                    uppercase=bool(emp_data.get("uppercase", True)),
                    sfx_event=r.get("sfx"),
                    semantic_type=r.get("semantic_type", "normal"),
                    emoji=r.get("emoji"),
                    style_preset=r.get("style_preset", preset_name),
                    color_palette=r.get("color_palette", custom_colors),
                )
                events.append(ev)

        # If no razor_captions exist yet in plan, generate them dynamically
        if not events and transcript_segments:
            logger.info("[CAPTION-COMPOSITOR] [Razor] Generating canonical ZapCap CaptionEvents...")
            broll_times = []
            if edit_plan and "shots" in edit_plan:
                broll_times = [
                    (float(s.get("start_time", 0.0)), float(s.get("end_time", 0.0)))
                    for s in edit_plan.get("shots", [])
                    if s.get("asset_path")
                ]
            
            engine = RazorCaptionEngine(
                max_group_size=words_per_beat,
                enable_behind_subject=behind_subject_enabled,
            )
            engine.scorer.preset_name = preset_name
            engine.scorer.palette = custom_colors or {}
            engine.scorer.enable_emojis = enable_emojis

            events = engine.process(
                segments=transcript_segments,
                broll_active_times=broll_times,
            )
            # Store in edit_plan
            if edit_plan is not None:
                edit_plan["razor_captions"] = [e.to_edit_plan_entry() for e in events]

        # Normalize external hook_text if provided
        if hook_text and hook_text.strip():
            hook_words = set(re.sub(r"[^\w\s]", "", hook_text.lower()).split())
            for ev in events:
                clean_w = re.sub(r"[^\w\s]", "", ev.word.lower())
                if clean_w in hook_words:
                    ev.emphasis = EmphasisLevel.HOOK
                    ev.semantic_type = "hook"
                    ev.font_weight = "Black"
                    ev.fill_color = "#FFE600"
                    ev.accent_color = "#FFE600"
                    ev.font_size_scale = max(ev.font_size_scale, 1.25)
                    # Promote to behind-subject if enabled and word is substantive
                    if behind_subject_enabled and (
                        ev.named_entity or ev.numeric_value or ev.action_word or len(clean_w) >= 4
                    ):
                        ev.layer = LayerMode.BEHIND_SUBJECT

        if edit_plan is not None and events:
            engine_sync = RazorCaptionEngine(max_group_size=words_per_beat, enable_behind_subject=behind_subject_enabled)
            edit_plan["subtitles"] = engine_sync.to_subtitles(events, preset_name=preset_name)

        return events


    async def _compile_from_razor_events(
        self,
        source_video: str,
        razor_events: List[CaptionEvent],
        work_dir: Path,
        style_preset: str,
        position: str,
        custom_margin_v: Optional[int],
        behind_subject_enabled: bool,
        sample_fps: Optional[float] = None,
        custom_colors: Optional[Dict[str, str]] = None,
        enable_emojis: bool = True,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Split events into normal and behind-subject layers and generate ASS files."""
        normal_events: List[CaptionEvent] = []
        behind_events: List[CaptionEvent] = []

        for ev in razor_events:
            if behind_subject_enabled and ev.emphasis == EmphasisLevel.HOOK and ev.layer == LayerMode.BEHIND_SUBJECT:
                behind_events.append(ev)
            else:
                normal_events.append(ev)

        logger.info(
            "[CAPTION-COMPOSITOR] [ZapCap] Split events: %d normal/top, %d behind-subject.",
            len(normal_events), len(behind_events)
        )

        all_ass_dest = work_dir / "subtitles_kinetic.ass"
        normal_ass_dest = work_dir / "subtitles_normal.ass"
        behind_ass_dest = work_dir / "subtitles_behind_subject.ass"
        matte_dest = work_dir / "subject_matte.mp4"

        # Generate normal ASS file
        self._write_razor_ass_file(
            events=normal_events if behind_events else razor_events,
            output_path=normal_ass_dest if behind_events else all_ass_dest,
            style_preset=style_preset,
            position=position,
            custom_margin_v=custom_margin_v,
            is_behind_layer=False,
            custom_colors=custom_colors,
            enable_emojis=enable_emojis,
        )

        if not behind_events or not behind_subject_enabled:
            return str(all_ass_dest.resolve()), None, None

        # Generate behind-subject ASS file with hook events
        self._write_razor_ass_file(
            events=behind_events,
            output_path=behind_ass_dest,
            style_preset=style_preset,
            position="center",  # Hook behind subject sits centered across upper torso/chest
            custom_margin_v=custom_margin_v,
            is_behind_layer=True,
            custom_colors=custom_colors,
            enable_emojis=enable_emojis,
        )

        # Generate subject matte
        logger.info("[CAPTION-COMPOSITOR] [SEGMENTATION] Generating subject matte for %d behind-subject hook events...", len(behind_events))
        try:
            matte_path = await asyncio.to_thread(
                subject_isolation_service.generate_person_matte_video,
                video_path=source_video,
                output_path=str(matte_dest),
                sample_fps=sample_fps,
                processing_width=self.width,
                processing_height=self.height,
            )
            if not matte_dest.exists() or matte_dest.stat().st_size == 0:
                raise RuntimeError("Subject matte file generation failed.")

            logger.info("[CAPTION-COMPOSITOR] [BEHIND-SUBJECT] True behind-subject compositing enabled!")
            return str(normal_ass_dest.resolve()), str(behind_ass_dest.resolve()), str(matte_path.resolve())

        except Exception as e:
            logger.warning("[CAPTION-COMPOSITOR] [SEGMENTATION] Failed to generate matte: %s. Falling back to top captions.", e)
            # Safe graceful degradation: render all captions on top
            self._write_razor_ass_file(
                events=razor_events,
                output_path=all_ass_dest,
                style_preset=style_preset,
                position=position,
                custom_margin_v=custom_margin_v,
                is_behind_layer=False,
            )
            return str(all_ass_dest.resolve()), None, None

    async def _compile_from_legacy_subtitles(
        self,
        source_video: str,
        edit_plan: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        work_dir: Path,
        style_preset: str,
        position: str,
        custom_margin_v: Optional[int],
        hook_text: Optional[str],
        hook_duration: Optional[float],
        suppress_hook: bool,
        text_emphasis_events: Optional[List[Dict[str, Any]]],
        caption_motion: str,
        behind_subject_enabled: bool,
        sample_fps: Optional[float] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Legacy path for non-razor subtitles with fixed behind-subject hook support."""
        subtitles = edit_plan.get("subtitles", []) if edit_plan else []
        segments = annotate_segments_for_subject_captions(
            transcript_segments,
            subtitles,
            force_behind_subject=False,
        )

        has_behind = behind_subject_enabled and (
            has_behind_subject_segments(segments) or (hook_text and not suppress_hook)
        )

        all_ass_dest = work_dir / "subtitles_kinetic.ass"
        normal_ass_dest = work_dir / "subtitles_normal.ass"
        behind_ass_dest = work_dir / "subtitles_behind_subject.ass"
        matte_dest = work_dir / "subject_matte.mp4"

        try:
            self.sub_engine.generate_ass_file(
                segments=segments or transcript_segments,
                output_path=all_ass_dest,
                style_preset=style_preset,
                position=position,
                custom_margin_v=custom_margin_v,
                hook_text=hook_text,
                hook_duration=hook_duration,
                suppress_hook=suppress_hook,
                text_emphasis_events=text_emphasis_events,
                motion_profile=caption_motion,
            )
        except Exception as se:
            logger.warning(f"[CAPTION-COMPOSITOR] Could not generate base kinetic subtitles: {se}")
            return None, None, None

        if not has_behind:
            return str(all_ass_dest.resolve()), None, None

        try:
            # Normal layer: regular subtitles above subject
            self.sub_engine.generate_ass_file(
                segments=segments,
                output_path=normal_ass_dest,
                style_preset=style_preset,
                position=position,
                custom_margin_v=custom_margin_v,
                hook_text=None if behind_subject_enabled else hook_text,
                hook_duration=hook_duration,
                suppress_hook=True if behind_subject_enabled else suppress_hook,
                text_emphasis_events=text_emphasis_events,
                motion_profile=caption_motion,
                only_behind_subject=False,
            )

            # Behind layer: hook text and behind segments rendered UNDER subject
            self.sub_engine.generate_ass_file(
                segments=segments,
                output_path=behind_ass_dest,
                style_preset=style_preset,
                position=position,
                custom_margin_v=custom_margin_v,
                hook_text=hook_text if behind_subject_enabled else None,
                hook_duration=hook_duration,
                suppress_hook=False if (behind_subject_enabled and hook_text) else True,
                text_emphasis_events=None,
                motion_profile=caption_motion,
                only_behind_subject=True,
            )

            matte_path = await asyncio.to_thread(
                subject_isolation_service.generate_person_matte_video,
                video_path=source_video,
                output_path=str(matte_dest),
                sample_fps=sample_fps,
                processing_width=self.width,
                processing_height=self.height,
            )
            if not matte_dest.exists():
                raise RuntimeError("Subject matte file was not created.")

            return str(normal_ass_dest.resolve()), str(behind_ass_dest.resolve()), str(matte_path.resolve())

        except Exception as me:
            logger.warning(f"[CAPTION-COMPOSITOR] Failed to prepare legacy behind-subject captions: {me}. Falling back to normal.")
            return str(all_ass_dest.resolve()), None, None

    def _write_razor_ass_file(
        self,
        events: List[CaptionEvent],
        output_path: Path,
        style_preset: str,
        position: str,
        custom_margin_v: Optional[int],
        is_behind_layer: bool = False,
        custom_colors: Optional[Dict[str, str]] = None,
        enable_emojis: bool = True,
    ) -> Path:
        """Write ASS subtitle script from typed CaptionEvent objects with ZapCap presets and active-word rhythm."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        preset: ZapCapPreset = get_preset(style_preset)
        colors = custom_colors or {}

        # Resolve hex colors to ASS BGR format
        main_c_ass = hex_to_ass_color(colors.get("main") or preset.fill_color)
        second_c_ass = hex_to_ass_color(colors.get("second") or preset.highlight_color)
        third_c_ass = hex_to_ass_color(colors.get("third") or preset.secondary_color)
        stroke_c_ass = hex_to_ass_color(preset.stroke_color)
        shadow_c_ass = hex_to_ass_color("#000000", alpha=128)

        # Margins & Alignments (Safe-zone aware)
        if is_behind_layer:
            margin_v = custom_margin_v or 680
            align = 5  # Middle-Center for behind hook across upper chest
        else:
            if position == "top":
                margin_v = custom_margin_v or 240
                align = 8  # Top-Center
            elif position == "center":
                margin_v = custom_margin_v or 0
                align = 5  # Middle-Center
            else:  # bottom default (safe from TikTok / IG Reels bottom overlay)
                margin_v = custom_margin_v or 280
                align = 2  # Bottom-Center

        font_size = int(preset.font_size * (1.35 if is_behind_layer else 1.0))

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.width}
PlayResY: {self.height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: NormalBeat,{preset.font_family},{font_size},{main_c_ass},&H000000FF,{stroke_c_ass},{shadow_c_ass},-1,0,0,0,100,100,{int(preset.letter_spacing*100)},0,1,{preset.stroke_width},{preset.shadow_blur // 2},{align},40,40,{margin_v},1
Style: HookBehind,{preset.font_family},{font_size},{second_c_ass},&H000000FF,{stroke_c_ass},{shadow_c_ass},-1,0,0,0,100,100,{int(preset.letter_spacing*100)},0,1,{preset.stroke_width + 2},{preset.shadow_blur},{align},40,40,{margin_v},1
Style: HookWord,{preset.font_family},{font_size},{second_c_ass},&H000000FF,{stroke_c_ass},{shadow_c_ass},-1,0,0,0,100,100,{int(preset.letter_spacing*100)},0,1,{preset.stroke_width + 2},{preset.shadow_blur},{align},40,40,{margin_v},1
Style: StrongWord,{preset.font_family},{int(font_size * 1.1)},{second_c_ass},&H000000FF,{stroke_c_ass},{shadow_c_ass},-1,0,0,0,100,100,{int(preset.letter_spacing*100)},0,1,{preset.stroke_width + 1},{preset.shadow_blur // 2},{align},40,40,{margin_v},1


[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []

        if is_behind_layer:
            # Behind layer: render hook events centered across speaker torso/shoulders
            for ev in events:
                st = format_ass_timestamp(ev.start_time)
                et = format_ass_timestamp(ev.end_time)
                word_text = ev.word.strip().upper() if preset.uppercase else ev.word.strip()
                if ev.emoji and enable_emojis:
                    word_text = f"{word_text} {ev.emoji}"
                anim_tag = "{\\fscx100\\fscy100\\t(0,100,\\fscx120\\fscy120)\\t(100,200,\\fscx100\\fscy100)}"
                color_tag = f"{{\\c{second_c_ass}}}"
                line = f"Dialogue: 2,{st},{et},HookBehind,,0,0,0,,{anim_tag}{color_tag}{word_text}"
                dialogue_lines.append(line)
        else:
            # Normal kinetic layer: group into short rhythmic beats with active word highlighting
            # Group events by phrase_id
            phrases: Dict[int, List[CaptionEvent]] = {}
            for ev in events:
                phrases.setdefault(ev.phrase_id, []).append(ev)

            # If any phrase exceeds 4 words or all events share phrase_id 0, chunk into 1-4 word beats
            rechunked_phrases: Dict[int, List[CaptionEvent]] = {}
            p_idx = 0
            for pid, ev_list in phrases.items():
                if len(ev_list) > 4:
                    chunk_sz = 3
                    for k in range(0, len(ev_list), chunk_sz):
                        rechunked_phrases[p_idx] = ev_list[k:k + chunk_sz]
                        p_idx += 1
                else:
                    rechunked_phrases[p_idx] = ev_list
                    p_idx += 1
            phrases = rechunked_phrases

            for p_id, beat_events in phrases.items():
                if not beat_events:
                    continue

                # Each beat event is spoken sequentially. For each active word interval,
                # display the entire beat group with the current active word highlighted
                for curr_ev in beat_events:
                    st = format_ass_timestamp(curr_ev.start_time)
                    et = format_ass_timestamp(curr_ev.end_time)

                    tokens: List[str] = []
                    for ev in beat_events:
                        word_str = ev.word.strip().upper() if preset.uppercase else ev.word.strip()
                        if ev.emoji and enable_emojis:
                            word_str = f"{word_str} {ev.emoji}"

                        if ev == curr_ev:
                            # Active spoken word: Pop scale + Active highlight color
                            if ev.semantic_type == "money":
                                c_tag = f"{{\\c{third_c_ass}\\fscx118\\fscy118}}"
                            elif ev.semantic_type == "negation":
                                c_tag = "{\\c&H004444EF&\\fscx118\\fscy118}"
                            elif ev.emphasis in (EmphasisLevel.HOOK, EmphasisLevel.STRONG):
                                c_tag = f"{{\\c{second_c_ass}\\fscx122\\fscy122}}"
                            else:
                                c_tag = f"{{\\c{second_c_ass}\\fscx115\\fscy115}}"
                            tokens.append(f"{c_tag}{word_str}{{\\rNormalBeat}}")
                        else:
                            # Inactive context word
                            tokens.append(f"{{\\c{main_c_ass}}}{word_str}")

                    full_beat_text = " ".join(tokens)
                    line = f"Dialogue: 1,{st},{et},NormalBeat,,0,0,0,,{full_beat_text}"
                    dialogue_lines.append(line)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(dialogue_lines) + "\n")

        return output_path


# Global singleton instance
caption_compositor = CaptionCompositor()

