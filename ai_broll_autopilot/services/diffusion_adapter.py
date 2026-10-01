"""Diffusion Studio Adapter.

Converts Stockpile Edit Plans into native Diffusion Studio compositions
(@diffusionstudio/core Schema 4.0.0) with timeline precision, layered video,
B-roll cutaways, styled editable captions, graphic text callouts,
multi-track audio mix (Dialogue, BGM ducking, SFX), and bidirectional OpenReel handoff.
"""

import json
import logging
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.services.edit_director import EditPlan
from ai_broll_autopilot.services.editor_base import EditorAdapter
from ai_broll_autopilot.utils.timeline_math import TimelinePrecision, NormalizedClipTiming

logger = logging.getLogger(__name__)

DIFFUSION_STUDIO_SCHEMA_VERSION = "4.0.0"


class DiffusionAdapter(EditorAdapter):
    """Translates Stockpile EditPlan into a Diffusion Studio Composition specification."""

    @property
    def engine_name(self) -> str:
        return "diffusion"

    @property
    def schema_version(self) -> str:
        return DIFFUSION_STUDIO_SCHEMA_VERSION

    def __init__(
        self,
        default_width: int = 1080,
        default_height: int = 1920,
        default_fps: int = 30,
    ):
        self.default_width = default_width
        self.default_height = default_height
        self.default_fps = default_fps

    def create_project(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert EditPlan into Diffusion Studio Composition spec conforming to EditorAdapter."""
        return self.create_diffusion_composition(
            edit_plan=edit_plan,
            project_name=project_name,
            resolved_broll_map=resolved_broll_map,
            base_asset_url=base_asset_url,
        )

    def create_composition(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience alias for create_diffusion_composition."""
        return self.create_diffusion_composition(
            edit_plan=edit_plan,
            project_name=project_name,
            resolved_broll_map=resolved_broll_map,
            base_asset_url=base_asset_url,
        )

    def create_diffusion_composition(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete Diffusion Studio Composition specification.

        Args:
            edit_plan: Canonical Stockpile EditPlan instance.
            project_name: Optional custom project title.
            resolved_broll_map: Map of shot_id -> local disk path for B-roll assets.
            base_asset_url: Base HTTP URL for streaming media.

        Returns:
            JSON-serializable dict conforming to Diffusion Studio composition schema.
        """
        start_ms = time.time()
        title = project_name or edit_plan.title or "Stockpile Viral Composition"
        comp_id = f"comp_{uuid.uuid4().hex[:12]}"

        # 1. Resolve timeline duration with sub-millisecond precision
        total_duration = TimelinePrecision.quantize(edit_plan.target_duration)
        clip_in = TimelinePrecision.quantize(edit_plan.clip_interval.get("in_point", 0.0))
        clip_out = TimelinePrecision.quantize(edit_plan.clip_interval.get("out_point", total_duration))
        computed_dur = TimelinePrecision.calc_duration(clip_in, clip_out)
        duration = computed_dur if computed_dur > 0 else total_duration

        # 2. Main Speaker Video Source
        source_media = edit_plan.source_media or {}
        source_path = source_media.get("path", "")
        source_filename = Path(source_path).name if source_path else "source_video.mp4"
        source_url = (
            f"{base_asset_url}/source"
            if base_asset_url
            else (f"file:///{Path(source_path).as_posix()}" if source_path else "")
        )

        broll_map = resolved_broll_map or {}

        # -------------------------------------------------------------
        # LAYER 1: Main Speaker Video Track (A-Roll)
        # -------------------------------------------------------------
        main_clip_timing = NormalizedClipTiming.create(
            start_time=0.0,
            duration=duration,
            in_point=clip_in,
            out_point=clip_out,
            source_duration=float(source_media.get("duration", duration)),
            fps=self.default_fps,
        )

        # Convert punch-in zooms to Diffusion Studio keyframe animations
        zoom_animations: List[Dict[str, Any]] = []
        for z in edit_plan.zooms:
            z_time = TimelinePrecision.quantize(z.get("time", 0.0))
            z_scale = TimelinePrecision.quantize(z.get("scale", 1.25))
            zoom_animations.append({
                "property": "scale",
                "time": z_time,
                "value": z_scale,
                "easing": "ease-out",
            })

        main_video_clip = {
            "id": f"clip_main_{uuid.uuid4().hex[:6]}",
            "type": "video",
            "name": source_filename,
            "source": source_url,
            "delay": main_clip_timing.start_time,
            "duration": main_clip_timing.duration,
            "range": [main_clip_timing.in_point, main_clip_timing.out_point],
            "position": {"x": 0.5, "y": 0.5},
            "scale": 1.0,
            "anchor": {"x": 0.5, "y": 0.5},
            "opacity": 1.0,
            "volume": 1.0,
            "muted": False,
            "fitMode": "cover",
            "animations": zoom_animations,
        }

        main_video_clips: List[Dict[str, Any]] = []
        if getattr(edit_plan, "a_roll_ranges", None) and len(edit_plan.a_roll_ranges) > 0:
            for idx, r in enumerate(edit_plan.a_roll_ranges):
                r_start = TimelinePrecision.quantize(r.get("start", 0.0))
                r_dur = TimelinePrecision.quantize(r.get("duration", 1.0))
                r_in = TimelinePrecision.quantize(r.get("source_in", 0.0))
                r_out = TimelinePrecision.quantize(r.get("source_out", r_in + r_dur))

                seg_zooms = [
                    z for z in zoom_animations
                    if r_start <= z["time"] < (r_start + r_dur)
                ]

                main_video_clips.append({
                    "id": f"clip_main_seg_{idx+1}_{uuid.uuid4().hex[:4]}",
                    "type": "video",
                    "name": f"{source_filename} [Part {idx+1}]",
                    "source": source_url,
                    "delay": r_start,
                    "duration": r_dur,
                    "range": [r_in, r_out],
                    "position": {"x": 0.5, "y": 0.5},
                    "scale": 1.0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                    "volume": 1.0,
                    "muted": False,
                    "fitMode": "cover",
                    "animations": seg_zooms,
                })
        else:
            main_video_clips.append(main_video_clip)

        layer_main_video = {
            "id": "layer_main_video",
            "name": "Main Speaker (A-Roll)",
            "type": "video",
            "order": 1,
            "visible": True,
            "clips": main_video_clips,
        }

        # -------------------------------------------------------------
        # LAYER 2: B-Roll Cutaway Video Track
        # -------------------------------------------------------------
        broll_clips: List[Dict[str, Any]] = []
        for idx, shot in enumerate(edit_plan.shots):
            shot_id = shot.get("shot_id", f"broll_{idx+1}")
            st = TimelinePrecision.quantize(shot.get("start_time", 0.0))
            dur = TimelinePrecision.quantize(shot.get("duration", 2.0))
            asset_path = shot.get("asset_path") or broll_map.get(shot_id, "")
            asset_name = Path(asset_path).name if asset_path else f"{shot_id}.mp4"

            broll_url = (
                f"{base_asset_url}/{urllib.parse.quote(asset_name, safe='~()*!._-')}"
                if base_asset_url
                else (f"file:///{Path(asset_path).as_posix()}" if asset_path else "")
            )

            timing = NormalizedClipTiming.create(
                start_time=st,
                duration=dur,
                in_point=0.0,
                out_point=dur,
                fps=self.default_fps,
            )

            broll_clips.append({
                "id": f"clip_{shot_id}",
                "type": "video",
                "name": asset_name,
                "source": broll_url,
                "delay": timing.start_time,
                "duration": timing.duration,
                "range": [timing.in_point, timing.out_point],
                "position": {"x": 0.5, "y": 0.5},
                "scale": 1.0,
                "anchor": {"x": 0.5, "y": 0.5},
                "opacity": 1.0,
                "volume": 0.0,  # Muted by default to preserve dialogue clarity
                "muted": True,
                "fitMode": "cover",
                "transition": {
                    "type": shot.get("transition", "cut"),
                    "duration": 0.25,
                },
                "metadata": {
                    "shot_id": shot_id,
                    "search_query": shot.get("search_query", ""),
                    "category": shot.get("category", ""),
                    "rationale": shot.get("rationale", ""),
                    "narrative_role": shot.get("narrative_role", "ILLUSTRATE"),
                    "emotional_intent": shot.get("emotional_intent", ""),
                    "confidence": shot.get("confidence", 1.0),
                    "pacing_category": shot.get("pacing_category", "normal"),
                },
            })

        layer_broll_video = {
            "id": "layer_broll_video",
            "name": "B-Roll Cutaways",
            "type": "video",
            "order": 2,
            "visible": True,
            "clips": broll_clips,
        }

        # -------------------------------------------------------------
        # LAYER 3: Graphic Text Overlays & Hook Cards
        # -------------------------------------------------------------
        text_clips: List[Dict[str, Any]] = []
        subtitle_texts = {
            " ".join(str(s.get("text", "")).strip().lower().split())
            for s in edit_plan.subtitles
            if str(s.get("text", "")).strip()
        }
        for i, ov in enumerate(edit_plan.text_overlays):
            overlay_id = str(ov.get("id", f"text_ov_{i+1}"))
            normalized_overlay_text = " ".join(
                str(ov.get("text", "")).strip().lower().split()
            )
            # Hook/title text is already represented by the caption timeline.
            # Keeping a second text clip creates the exact double-caption bug.
            if overlay_id.startswith("cap_hook") or normalized_overlay_text in subtitle_texts:
                continue

            pos_preset = ov.get("position", "center")
            if pos_preset in ["top", "hook"]:
                pos_y = 0.28
                behind_subject = True
            elif pos_preset == "center":
                pos_y = 0.50
                behind_subject = ov.get("behind_subject", False)
            else:
                pos_y = 0.72
                behind_subject = False

            raw_text = ov.get("text", "")
            text_val = raw_text.upper() if behind_subject else raw_text
            st = TimelinePrecision.quantize(ov.get("start_time", 0.5))
            dur = TimelinePrecision.quantize(ov.get("duration", 2.2))

            text_clips.append({
                "id": ov.get("id", f"text_ov_{i+1}"),
                "type": "text",
                "text": text_val,
                "delay": st,
                "duration": dur,
                "position": {"x": 0.5, "y": pos_y},
                "fontSize": ov.get("font_size", 68 if behind_subject else 56),
                "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                "fontWeight": "bold",
                "color": "#FFFFFF",
                "align": "center",
                "baseline": "middle",
                "strokes": [{
                    "color": "#000000",
                    "width": 6,
                }],
                "shadows": [{
                    "color": "rgba(0,0,0,0.7)",
                    "blur": 8,
                    "offset": {"x": 2, "y": 4},
                }],
                "behindSubject": behind_subject,
                "animation": ov.get("animation_preset", ov.get("animation", "pop")),
            })

        # Content-aware kinetic graphics (Number stats, key term badges, lower thirds)
        for g in getattr(edit_plan, "graphics", []):
            g_st = TimelinePrecision.quantize(g.get("start_time", 1.0))
            g_dur = TimelinePrecision.quantize(g.get("duration", 2.5))
            p_text = g.get("primary_text", "")
            s_text = g.get("secondary_text", "")
            display_text = f"{p_text}\n{s_text}".strip() if s_text else p_text

            pos_y = (g.get("position", {}).get("y_percent", 25.0)) / 100.0
            pos_x = (g.get("position", {}).get("x_percent", 50.0)) / 100.0

            text_clips.append({
                "id": g.get("graphic_id", f"gfx_{len(text_clips)+1}"),
                "type": "text",
                "text": display_text,
                "delay": g_st,
                "duration": g_dur,
                "position": {"x": pos_x, "y": pos_y},
                "fontSize": 62 if g.get("graphic_type") == "number_stat" else 48,
                "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                "fontWeight": "black" if g.get("graphic_type") == "number_stat" else "bold",
                "color": g.get("accent_color", "#FFCC00"),
                "align": "center",
                "baseline": "middle",
                "strokes": [{"color": "#000000", "width": 6}],
                "shadows": [{"color": "rgba(0,0,0,0.85)", "blur": 10, "offset": {"x": 2, "y": 4}}],
                "behindSubject": False,
                "animation": g.get("animation_in", "pop"),
            })

        layer_text_overlays = {
            "id": "layer_text_overlays",
            "name": "Text Overlays & Hooks",
            "type": "text",
            "order": 3,
            "visible": True,
            "clips": text_clips,
        }

        # -------------------------------------------------------------
        # LAYER 4: Dynamic Subtitles & Captions
        # -------------------------------------------------------------
        caption_clips: List[Dict[str, Any]] = []
        for s in edit_plan.subtitles:
            sub_st = TimelinePrecision.quantize(s.get("startTime", 0.0))
            sub_et = TimelinePrecision.quantize(s.get("endTime", sub_st + 1.5))
            sub_dur = TimelinePrecision.calc_duration(sub_st, sub_et)

            words_data: List[Dict[str, Any]] = []
            for w in s.get("words", []):
                w_start = TimelinePrecision.quantize(w.get("start", sub_st))
                w_end = TimelinePrecision.quantize(w.get("end", w_start + 0.3))
                words_data.append({
                    "text": w.get("word", w.get("text", "")),
                    "start": w_start,
                    "end": w_end,
                })

            caption_clips.append({
                "id": s.get("id", f"caption_{uuid.uuid4().hex[:6]}"),
                "type": "caption",
                "text": s.get("text", ""),
                "delay": sub_st,
                "duration": sub_dur,
                "range": [sub_st, sub_et],
                "preset": "classic",
                "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                "fontSize": 54,
                "color": "#FFFFFF",
                "highlightColors": [edit_plan.style.get("highlight_color", "#FFDD00")],
                "stroke": {
                    "color": "#000000",
                    "width": 5,
                },
                "shadow": {
                    "color": "rgba(0,0,0,0.8)",
                    "blur": 6,
                    "offset": {"x": 2, "y": 3},
                },
                "position": {"x": 0.5, "y": 0.82},
                "words": words_data,
            })

        layer_captions = {
            "id": "layer_captions",
            "name": "Subtitles",
            "type": "caption",
            "order": 4,
            "visible": True,
            "clips": caption_clips,
        }

        # -------------------------------------------------------------
        # LAYER 5: Audio Mix - Dialogue Track
        # -------------------------------------------------------------
        dialogue_clip = {
            "id": f"audio_dialogue_{uuid.uuid4().hex[:6]}",
            "type": "audio",
            "name": "Dialogue Track",
            "role": "dialogue",
            "source": source_url,
            "delay": 0.0,
            "duration": duration,
            "range": [clip_in, clip_out],
            "volume": 1.0,
            "muted": False,
        }

        dialogue_clips: List[Dict[str, Any]] = []
        if getattr(edit_plan, "a_roll_ranges", None) and len(edit_plan.a_roll_ranges) > 0:
            for idx, r in enumerate(edit_plan.a_roll_ranges):
                r_start = TimelinePrecision.quantize(r.get("start", 0.0))
                r_dur = TimelinePrecision.quantize(r.get("duration", 1.0))
                r_in = TimelinePrecision.quantize(r.get("source_in", 0.0))
                r_out = TimelinePrecision.quantize(r.get("source_out", r_in + r_dur))
                dialogue_clips.append({
                    "id": f"audio_dialogue_seg_{idx+1}_{uuid.uuid4().hex[:4]}",
                    "type": "audio",
                    "name": f"Dialogue Track [Part {idx+1}]",
                    "role": "dialogue",
                    "source": source_url,
                    "delay": r_start,
                    "duration": r_dur,
                    "range": [r_in, r_out],
                    "volume": 1.0,
                    "muted": False,
                })
        else:
            dialogue_clips.append(dialogue_clip)

        layer_audio_dialogue = {
            "id": "layer_audio_dialogue",
            "name": "Audio - Dialogue",
            "type": "audio",
            "order": 5,
            "visible": True,
            "clips": dialogue_clips,
        }

        # -------------------------------------------------------------
        # LAYER 6: Audio Mix - Background Music (BGM)
        # -------------------------------------------------------------
        bgm_clips: List[Dict[str, Any]] = []
        bgm_track = edit_plan.audio_cues.get("bgm_track") if edit_plan.audio_cues else None
        if bgm_track:
            bgm_name = Path(bgm_track).name
            bgm_url = (
                f"{base_asset_url}/{urllib.parse.quote(bgm_name, safe='~()*!._-')}"
                if base_asset_url
                else (f"file:///{Path(bgm_track).as_posix()}" if bgm_track else "")
            )
            bgm_clips.append({
                "id": f"audio_bgm_{uuid.uuid4().hex[:6]}",
                "type": "audio",
                "name": bgm_name,
                "role": "bgm",
                "source": bgm_url,
                "delay": 0.0,
                "duration": duration,
                "range": [0.0, duration],
                "volume": 0.15,  # Ducked under speech
                "muted": False,
            })

        layer_audio_bgm = {
            "id": "layer_audio_bgm",
            "name": "Audio - BGM",
            "type": "audio",
            "order": 6,
            "visible": True,
            "clips": bgm_clips,
        }

        # -------------------------------------------------------------
        # LAYER 7: Audio Mix - Sound Effects (SFX)
        # -------------------------------------------------------------
        sfx_clips: List[Dict[str, Any]] = []
        has_curated_cues = bool(edit_plan.audio_cues and edit_plan.audio_cues.get("sfx"))

        # Primary: SFX curated by sound_designer with strict density and semantic justification
        if has_curated_cues:
            for i, sfx_cue in enumerate(edit_plan.audio_cues["sfx"]):
                sfx_file = sfx_cue.get("file", "")
                if sfx_file:
                    sfx_name = Path(sfx_file).name
                    sfx_url = (
                        f"{base_asset_url}/{urllib.parse.quote(sfx_name, safe='~()*!._-')}"
                        if base_asset_url
                        else (f"file:///{Path(sfx_file).as_posix()}" if sfx_file else "")
                    )
                    sfx_t = TimelinePrecision.quantize(sfx_cue.get("time", 0.0))
                    sfx_dur = TimelinePrecision.quantize(sfx_cue.get("duration", 0.8))
                    sfx_clips.append({
                        "id": f"sfx_cue_{i+1}",
                        "type": "audio",
                        "name": sfx_name,
                        "role": "sfx",
                        "source": sfx_url,
                        "delay": sfx_t,
                        "duration": sfx_dur,
                        "range": [0.0, sfx_dur],
                        "volume": TimelinePrecision.quantize(sfx_cue.get("volume", 0.7)),
                        "muted": False,
                        "metadata": {
                            "eventType": sfx_cue.get("event_type") or sfx_cue.get("cue_type", "sfx"),
                            "justification": sfx_cue.get("justification", ""),
                            "syncTarget": sfx_cue.get("sync_target", ""),
                            "category": sfx_cue.get("category", "accent"),
                        }
                    })
        else:
            # Fallback legacy: SFX attached to B-roll cutaway transitions (only if no curated cues exist)
            for i, shot in enumerate(edit_plan.shots):
                sfx_file = shot.get("sfx_file") or shot.get("sfx_cue")
                stinger_vol = 0.75
                trans = shot.get("transition")
                if not sfx_file and isinstance(trans, dict):
                    stinger = trans.get("stinger_sfx")
                    if isinstance(stinger, dict):
                        sfx_file = stinger.get("path") or stinger.get("file")
                        stinger_vol = float(stinger.get("volume", 0.45))
                if not sfx_file and isinstance(shot.get("stinger_sfx"), dict):
                    stinger = shot.get("stinger_sfx")
                    sfx_file = stinger.get("path") or stinger.get("file")
                    stinger_vol = float(stinger.get("volume", 0.45))

                if sfx_file:
                    sfx_name = Path(sfx_file).name
                    sfx_url = (
                        f"{base_asset_url}/{urllib.parse.quote(sfx_name, safe='~()*!._-')}"
                        if base_asset_url
                        else (f"file:///{Path(sfx_file).as_posix()}" if sfx_file else "")
                    )
                    shot_st = TimelinePrecision.quantize(shot.get("start_time", 0.0))
                    sfx_clips.append({
                        "id": f"sfx_shot_{shot.get('shot_id', i+1)}",
                        "type": "audio",
                        "name": sfx_name,
                        "role": "sfx",
                        "source": sfx_url,
                        "delay": shot_st,
                        "duration": 0.8,
                        "range": [0.0, 0.8],
                        "volume": stinger_vol,
                        "muted": False,
                    })

        layer_audio_sfx = {
            "id": "layer_audio_sfx",
            "name": "Audio - SFX",
            "type": "audio",
            "order": 7,
            "visible": True,
            "clips": sfx_clips,
        }

        conversion_time_ms = round((time.time() - start_ms) * 1000, 2)

        layers_list = [
            layer_main_video,
            layer_broll_video,
            layer_text_overlays,
            layer_captions,
            layer_audio_dialogue,
            layer_audio_bgm,
            layer_audio_sfx,
        ]

        return {
            "version": DIFFUSION_STUDIO_SCHEMA_VERSION,
            "schema_version": DIFFUSION_STUDIO_SCHEMA_VERSION,
            "engine": "diffusion",
            "tracks": layers_list,
            "composition": {
                "id": comp_id,
                "title": title,
                "settings": {
                    "width": self.default_width,
                    "height": self.default_height,
                    "fps": self.default_fps,
                    "duration": duration,
                    "background": "#000000",
                    "playbackEndBehavior": "stop",
                },
                "layers": layers_list,
                "tracks": layers_list,
                "metadata": {
                    "generator": "Stockpile AI Director",
                    "plan_id": edit_plan.plan_id,
                    "niche": edit_plan.niche.get("niche_id", "generic"),
                    "style": edit_plan.style.get("style_id", "clean_podcast"),
                    "clip_count": (
                        1 + len(broll_clips) + len(text_clips) + len(caption_clips) + 1 + len(bgm_clips) + len(sfx_clips)
                    ),
                    "layer_count": 7,
                    "conversion_time_ms": conversion_time_ms,
                    "editorial_spec": edit_plan.editorial_spec,
                    "quality_report": edit_plan.quality_report,
                },
            },
        }

    def to_openreel_project(
        self,
        diffusion_comp: Dict[str, Any],
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert a Diffusion Studio composition specification into OpenReel Schema 1.2.0.

        Enables seamless bidirectional handoff between Diffusion Studio and OpenReel.
        """
        comp = diffusion_comp.get("composition", diffusion_comp)
        settings = comp.get("settings", {})
        duration = float(settings.get("duration", 30.0))
        width = int(settings.get("width", 1080))
        height = int(settings.get("height", 1920))
        fps = int(settings.get("fps", 30))
        now_ms = int(time.time() * 1000)

        # Deterministic project identity
        if project_id:
            proj_id = project_id if project_id.startswith("proj_") else f"proj_{project_id}"
        elif comp.get("id"):
            clean_id = comp["id"].replace("comp_", "")
            proj_id = f"proj_{clean_id}"
        else:
            proj_id = f"proj_{uuid.uuid4().hex[:12]}"

        media_items: List[Dict[str, Any]] = []
        media_id_map: Dict[str, str] = {}
        subtitles: List[Dict[str, Any]] = []

        def _get_or_create_media(source_url: str, name: str, media_type: str = "video") -> str:
            if source_url in media_id_map:
                return media_id_map[source_url]
            m_id = f"media_{uuid.uuid4().hex[:8]}"
            media_id_map[source_url] = m_id
            media_items.append({
                "id": m_id,
                "name": name,
                "type": media_type,
                "url": source_url,
                "originalUrl": source_url,
                "thumbnailUrl": f"{source_url}/thumb" if source_url.startswith("http") else None,
                "metadata": {
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "frameRate": fps,
                    "codec": "h264" if media_type == "video" else "aac",
                    "hasVideo": (media_type == "video"),
                    "hasAudio": True,
                },
                "blob": None,
                "fileHandle": None,
                "waveformData": None,
                "isPlaceholder": False,
                "sourceFile": {"name": name, "size": 0, "lastModified": now_ms},
            })
            return m_id

        tracks: List[Dict[str, Any]] = []
        text_clips: List[Dict[str, Any]] = []
        markers: List[Dict[str, Any]] = []

        for layer in comp.get("layers", []):
            layer_type = layer.get("type", "video")
            l_id = layer.get("id", f"track_{uuid.uuid4().hex[:6]}")
            l_name = layer.get("name", "Track")

            # 1. Caption layer -> Timeline Subtitles (not a timeline track in OpenReel Schema 1.2.0)
            if layer_type == "caption" or "caption" in l_id:
                for c in layer.get("clips", []):
                    sub_id = c.get("id", f"sub_{uuid.uuid4().hex[:6]}")
                    c_start = float(c.get("delay", c.get("startTime", 0.0)))
                    c_dur = float(c.get("duration", 2.0))
                    words = c.get("words", [])
                    subtitles.append({
                        "id": sub_id,
                        "text": c.get("text", ""),
                        "startTime": c_start,
                        "endTime": c_start + c_dur,
                        "animationStyle": "word-highlight",
                        "style": {
                            "fontFamily": c.get("fontFamily", "Montserrat"),
                            "fontSize": c.get("fontSize", 54),
                            "color": c.get("color", "#FFFFFF"),
                            "backgroundColor": "transparent",
                            "position": "bottom",
                            "highlightColor": (c.get("highlightColors") or ["#FFDD00"])[0],
                        },
                        "words": [
                            {
                                "text": w.get("word", w.get("text", "")),
                                "startTime": float(w.get("start", w.get("startTime", c_start))),
                                "endTime": float(w.get("end", w.get("endTime", c_start + c_dur))),
                            }
                            for w in words
                        ] if words else [],
                    })
                continue

            # 2. Text overlay layer -> OpenReel textClips + standard text track
            if layer_type == "text" or "text" in l_id:
                for c in layer.get("clips", []):
                    c_start = float(c.get("delay", c.get("startTime", 0.0)))
                    c_dur = float(c.get("duration", 2.0))
                    tc = {
                        "id": c.get("id", f"text_{uuid.uuid4().hex[:6]}"),
                        "trackId": l_id,
                        "startTime": c_start,
                        "duration": c_dur,
                        "text": c.get("text", ""),
                        "behindSubject": bool(c.get("behindSubject", False)),
                        "animation": {
                            "preset": "fade_up",
                            "params": {"distance": 50, "overshoot": 1.1},
                            "inDuration": 0.35,
                            "outDuration": 0.25,
                        },
                        "style": {
                            "fontFamily": c.get("fontFamily", "Montserrat"),
                            "fontSize": c.get("fontSize", 54),
                            "fontWeight": "bold",
                            "fontStyle": "normal",
                            "color": c.get("color", "#FFFFFF"),
                            "strokeColor": "#000000",
                            "strokeWidth": 6,
                            "shadowColor": "rgba(0, 0, 0, 0.85)",
                            "shadowBlur": 10,
                            "textAlign": c.get("align", "center"),
                            "verticalAlign": "middle",
                            "lineHeight": 1.15,
                            "letterSpacing": 0.8,
                        },
                        "transform": {
                            "position": c.get("position", {"x": 0.5, "y": 0.25}),
                            "scale": {"x": 1.0, "y": 1.0},
                            "rotation": 0,
                            "anchor": {"x": 0.5, "y": 0.5},
                            "opacity": 1.0,
                        },
                        "keyframes": [],
                    }
                    text_clips.append(tc)

                tracks.append({
                    "id": l_id,
                    "name": l_name,
                    "type": "text",
                    "role": "general",
                    "mode": "standard",
                    "clips": [],
                    "transitions": [],
                    "hidden": not layer.get("visible", True),
                    "muted": False,
                    "locked": False,
                    "solo": False,
                    "volume": 1.0,
                    "order": layer.get("order", 0),
                })
                continue

            # 3. Video or Audio layers
            clips: List[Dict[str, Any]] = []
            for c in layer.get("clips", []):
                c_type = c.get("type", layer_type)
                if c_type not in ("video", "audio", "image"):
                    continue
                c_start = float(c.get("delay", c.get("startTime", 0.0)))
                c_dur = float(c.get("duration", 2.0))
                c_range = c.get("range", [0.0, c_dur])
                c_source = c.get("source", "")
                c_name = c.get("name", "clip")

                m_id = _get_or_create_media(c_source, c_name, media_type=c_type)
                in_pt = float(c_range[0]) if (c_range and len(c_range) > 0 and c_range[0] is not None) else 0.0
                out_pt = float(c_range[1]) if (c_range and len(c_range) > 1 and c_range[1] is not None) else in_pt + c_dur

                clip_dict = {
                    "id": c.get("id", f"clip_{uuid.uuid4().hex[:6]}"),
                    "trackId": l_id,
                    "mediaId": m_id,
                    "startTime": c_start,
                    "duration": c_dur,
                    "inPoint": in_pt,
                    "outPoint": out_pt,
                    "effects": [],
                    "audioEffects": [],
                    "transform": {
                        "position": c.get("position", {"x": 0.5, "y": 0.5}),
                        "scale": {"x": c.get("scale", 1.0), "y": c.get("scale", 1.0)} if isinstance(c.get("scale"), (int, float)) else c.get("scale", {"x": 1.0, "y": 1.0}),
                        "rotation": c.get("rotation", 0),
                        "anchor": c.get("anchor", {"x": 0.5, "y": 0.5}),
                        "opacity": float(c.get("opacity", 1.0)),
                        "fitMode": c.get("fitMode", "cover"),
                    },
                    "volume": float(c.get("volume", 1.0)),
                    "keyframes": c.get("animations", []),
                }
                clips.append(clip_dict)

                if "broll" in l_id:
                    markers.append({
                        "id": f"marker_broll_{len(markers)+1}",
                        "time": c_start,
                        "label": f"B-Roll: {c_name}",
                        "color": "#F59E0B",
                    })

            track_role = "general"
            if "broll" in l_id:
                track_role = "general"
            elif "main" in l_id:
                track_role = "dialogue"
            elif "bgm" in l_id:
                track_role = "music"
            elif "sfx" in l_id:
                track_role = "effects"
            elif "dialogue" in l_id:
                track_role = "dialogue"

            tracks.append({
                "id": l_id,
                "name": l_name,
                "type": "video" if layer_type in ("video", "image") else "audio",
                "role": track_role,
                "mode": "standard",
                "clips": clips,
                "transitions": [],
                "hidden": not layer.get("visible", True),
                "muted": (layer_type == "video" and "broll" in l_id),
                "locked": False,
                "solo": False,
                "volume": float(layer.get("volume", 1.0)),
                "order": layer.get("order", 0),
            })

        # Validate that all timeline clip mediaId references are in mediaLibrary.items
        media_id_set = {item["id"] for item in media_items}
        for track in tracks:
            for clip in track.get("clips", []):
                m_id = clip.get("mediaId")
                if m_id and m_id not in media_id_set:
                    dummy_name = clip.get("id", "media")
                    media_items.append({
                        "id": m_id,
                        "name": dummy_name,
                        "type": "video" if track.get("type") == "video" else "audio",
                        "url": "",
                        "originalUrl": "",
                        "thumbnailUrl": None,
                        "metadata": {
                            "duration": duration,
                            "width": width,
                            "height": height,
                            "frameRate": fps,
                            "codec": "h264",
                            "hasVideo": True,
                            "hasAudio": True,
                        },
                        "blob": None,
                        "fileHandle": None,
                        "waveformData": None,
                        "isPlaceholder": False,
                    })
                    media_id_set.add(m_id)

        return {
            "version": "1.2.0",
            "project": {
                "id": proj_id,
                "name": project_name or comp.get("title", "Diffusion Handoff Project"),
                "createdAt": now_ms,
                "modifiedAt": now_ms,
                "metadata": comp.get("metadata", {}),
                "settings": {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "frameRate": fps,
                    "sampleRate": 48000,
                    "channels": 2,
                    "duration": duration,
                    "backgroundColor": settings.get("background", "#000000"),
                },
                "timeline": {
                    "tracks": tracks,
                    "subtitles": subtitles,
                    "duration": duration,
                    "markers": markers,
                },
                "mediaLibrary": {
                    "items": media_items,
                },
                "textClips": text_clips,
                "shapeClips": [],
                "svgClips": [],
                "stickerClips": [],
                "adjustmentLayers": [],
                "capabilities": ["tracks-universal", "behind-subject"],
            },
        }


diffusion_adapter = DiffusionAdapter()
