"""OpenReel Adapter.

Converts Stockpile Edit Plans into native OpenReel Schema 1.2.0 projects (.oreel / project.json).
Preserves non-destructive multitrack structure: separate tracks for main speaker video,
B-roll cutaways, subtitles with word-highlight timings, text overlays with behindSubject,
and multi-track audio mix (Dialogue, BGM ducking, SFX).
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
from ai_broll_autopilot.services.subject_isolation import subject_isolation_service

logger = logging.getLogger(__name__)

OPENREEL_SCHEMA_VERSION = "1.2.0"


class OpenReelAdapter(EditorAdapter):
    """Transforms Stockpile EditPlan into OpenReel Schema 1.2.0 native project file."""

    @property
    def engine_name(self) -> str:
        return "openreel"

    @property
    def schema_version(self) -> str:
        return OPENREEL_SCHEMA_VERSION

    def __init__(self, default_width: int = 1080, default_height: int = 1920, default_fps: int = 30):
        self.default_width = default_width
        self.default_height = default_height
        self.default_fps = default_fps

    def create_project(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Convert EditPlan into OpenReel project JSON dict conforming to EditorAdapter."""
        return self.create_openreel_project(
            edit_plan=edit_plan,
            project_name=project_name,
            resolved_broll_map=resolved_broll_map,
            base_asset_url=base_asset_url,
            **kwargs,
        )

    def create_openreel_project(
        self,
        edit_plan: EditPlan,
        project_name: Optional[str] = None,
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate OpenReel Schema 1.2.0 ProjectFile JSON dict.

        Args:
            edit_plan: Stockpile EditPlan instance.
            project_name: Optional custom project name.
            resolved_broll_map: Optional map of shot_id -> local file path for B-roll assets.
            base_asset_url: Optional base HTTP URL for streaming media in browser OpenReel.

        Returns:
            Dict conforming to OpenReel's ProjectFile { "version": "1.2.0", "project": { ... } }
        """
        proj_id = f"proj_{uuid.uuid4().hex[:12]}"
        name = project_name or edit_plan.title or "Stockpile Viral Short"
        duration = float(edit_plan.target_duration)
        now_ms = int(time.time() * 1000)

        # 1. Media Library Setup
        media_items: List[Dict[str, Any]] = []
        source_media = edit_plan.source_media
        source_path = source_media.get("path", "")
        source_name = Path(source_path).name if source_path else "source_video.mp4"
        source_media_id = "media_source_main"

        source_http_url = f"{base_asset_url}/source" if base_asset_url else (
            f"file:///{Path(source_path).as_posix()}" if source_path else ""
        )
        source_thumb_url = f"{base_asset_url}/source/thumb" if base_asset_url else None

        media_items.append({
            "id": source_media_id,
            "name": source_name,
            "type": "video",
            "metadata": {
                "duration": float(source_media.get("duration", duration)),
                "width": int(source_media.get("width", 1920)),
                "height": int(source_media.get("height", 1080)),
                "frameRate": int(source_media.get("fps", self.default_fps)),
                "codec": "h264",
                "sampleRate": 48000,
                "channels": 2,
                "fileSize": 0,
                "hasVideo": True,
                "hasAudio": True,
            },
            "fileHandle": None,
            "blob": None,
            "thumbnailUrl": source_thumb_url,
            "waveformData": None,
            "isPlaceholder": False,
            "originalUrl": source_http_url,
            "sourceFile": {
                "name": source_name,
                "size": 0,
                "lastModified": now_ms,
            },
            "url": source_http_url if (base_asset_url and source_http_url) else (f"file:///{Path(source_path).as_posix()}" if source_path else ""),
        })

        # Add B-roll media items
        broll_map = resolved_broll_map or {}
        for shot in edit_plan.shots:
            shot_id = shot.get("shot_id", "broll")
            asset_path = shot.get("asset_path") or broll_map.get(shot_id)
            if asset_path:
                broll_name = Path(asset_path).name
                broll_http_url = f"{base_asset_url}/{urllib.parse.quote(broll_name)}" if base_asset_url else f"file:///{Path(asset_path).as_posix()}"
                broll_thumb_url = f"{base_asset_url}/{urllib.parse.quote(broll_name)}/thumb" if base_asset_url else None
                media_items.append({
                    "id": f"media_{shot_id}",
                    "name": broll_name,
                    "type": "video",
                    "metadata": {
                        "duration": float(shot.get("duration", 3.0)),
                        "width": 1920,
                        "height": 1080,
                        "frameRate": self.default_fps,
                        "codec": "h264",
                        "sampleRate": 48000,
                        "channels": 2,
                        "fileSize": 0,
                        "hasVideo": True,
                        "hasAudio": False,
                    },
                    "fileHandle": None,
                    "blob": None,
                    "thumbnailUrl": broll_thumb_url,
                    "waveformData": None,
                    "isPlaceholder": False,
                    "originalUrl": broll_http_url,
                    "sourceFile": {
                        "name": broll_name,
                        "size": 0,
                        "lastModified": now_ms,
                    },
                    "url": broll_http_url if (base_asset_url and broll_http_url) else f"file:///{Path(asset_path).as_posix()}",
                })

        # 2. Timeline Tracks
        track_main_video = {
            "id": "track_video_main",
            "name": "Speaker / A-Roll",
            "type": "video",
            "role": "dialogue",
            "mode": "standard",
            "clips": [],
            "transitions": [],
            "hidden": False,
            "muted": False,
            "locked": False,
            "solo": False,
        }

        track_broll_video = {
            "id": "track_video_broll",
            "name": "B-Roll Cutaways",
            "type": "video",
            "role": "general",
            "mode": "standard",
            "clips": [],
            "transitions": [],
            "hidden": False,
            "muted": False,
            "locked": False,
            "solo": False,
        }

        track_bgm = {
            "id": "track_audio_bgm",
            "name": "Background Music",
            "type": "audio",
            "role": "music",
            "mode": "standard",
            "clips": [],
            "transitions": [],
            "hidden": False,
            "muted": False,
            "locked": False,
            "solo": False,
        }

        track_sfx = {
            "id": "track_audio_sfx",
            "name": "Sound Effects (SFX)",
            "type": "audio",
            "role": "effects",
            "mode": "standard",
            "clips": [],
            "transitions": [],
            "hidden": False,
            "muted": False,
            "locked": False,
            "solo": False,
        }

        # 3. Main Speaker Clip (Trimmed to In/Out points with 9:16 vertical cover fit)
        in_pt = float(edit_plan.clip_interval.get("in_point", 0.0))
        out_pt = float(edit_plan.clip_interval.get("out_point", in_pt + duration))

        # Build keyframes for punch-in zooms
        keyframes = []
        for zoom in edit_plan.zooms:
            z_time = float(zoom.get("time", 0.0))
            z_scale = float(zoom.get("scale", 1.08))
            keyframes.append({
                "id": f"kf_zoom_{uuid.uuid4().hex[:6]}",
                "time": z_time,
                "property": "transform.scale",
                "value": {"x": z_scale, "y": z_scale},
                "easing": zoom.get("easing", "snappy"),
            })

        if getattr(edit_plan, "a_roll_ranges", None) and len(edit_plan.a_roll_ranges) > 0:
            for idx, r in enumerate(edit_plan.a_roll_ranges):
                r_start = float(r.get("start", 0.0))
                r_dur = float(r.get("duration", 1.0))
                r_in = float(r.get("source_in", 0.0))
                r_out = float(r.get("source_out", r_in + r_dur))

                seg_keyframes = [
                    kf for kf in keyframes
                    if r_start <= kf["time"] < (r_start + r_dur)
                ]

                track_main_video["clips"].append({
                    "id": f"clip_main_seg_{idx+1}",
                    "mediaId": source_media_id,
                    "trackId": "track_video_main",
                    "startTime": r_start,
                    "duration": r_dur,
                    "inPoint": r_in,
                    "outPoint": r_out,
                    "effects": [],
                    "audioEffects": [],
                    "transform": {
                        "position": {"x": 0.5, "y": 0.5},
                        "scale": {"x": 1.0, "y": 1.0},
                        "rotation": 0,
                        "anchor": {"x": 0.5, "y": 0.5},
                        "opacity": 1.0,
                        "fitMode": "cover",
                    },
                    "volume": 1.0,
                    "keyframes": seg_keyframes,
                })
        else:
            main_clip = {
                "id": "clip_main_speech",
                "mediaId": source_media_id,
                "trackId": "track_video_main",
                "startTime": 0.0,
                "duration": duration,
                "inPoint": in_pt,
                "outPoint": out_pt,
                "effects": [],
                "audioEffects": [],
                "transform": {
                    "position": {"x": 0.5, "y": 0.5},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                    "fitMode": "cover",
                },
                "volume": 1.0,
                "keyframes": keyframes,
            }
            track_main_video["clips"].append(main_clip)

        # 4. B-Roll Overlay Clips & Transitions
        for i, shot in enumerate(edit_plan.shots):
            shot_id = shot.get("shot_id", f"broll_{i+1}")
            st = float(shot.get("start_time", 0.0))
            dur = float(shot.get("duration", 2.0))
            broll_media_id = f"media_{shot_id}" if (shot.get("asset_path") or broll_map.get(shot_id)) else source_media_id

            broll_clip = {
                "id": f"clip_{shot_id}",
                "mediaId": broll_media_id,
                "trackId": "track_video_broll",
                "startTime": st,
                "duration": dur,
                "inPoint": 0.0,
                "outPoint": dur,
                "effects": [],
                "audioEffects": [],
                "transform": {
                    "position": {"x": 0.5, "y": 0.5},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                    "fitMode": "cover",
                },
                "volume": 0.0,
                "keyframes": [],
                "metadata": {
                    "searchQuery": shot.get("search_query", ""),
                    "category": shot.get("category", ""),
                    "rationale": shot.get("rationale", ""),
                    "transition": shot.get("transition", "cut"),
                }
            }
            track_broll_video["clips"].append(broll_clip)

            # Assign SFX cue if present
            sfx_file = shot.get("sfx_file") or shot.get("sfx_cue")
            if sfx_file:
                sfx_name = Path(sfx_file).name
                sfx_http_url = f"{base_asset_url}/{urllib.parse.quote(sfx_name)}" if base_asset_url else f"file:///{Path(sfx_file).as_posix()}"
                sfx_media_id = f"media_sfx_{shot_id}"
                media_items.append({
                    "id": sfx_media_id,
                    "name": sfx_name,
                    "type": "audio",
                    "metadata": {
                        "duration": 1.5,
                        "sampleRate": 48000,
                        "channels": 2,
                        "codec": "wav",
                        "fileSize": 0,
                        "hasAudio": True,
                        "hasVideo": False,
                    },
                    "fileHandle": None,
                    "blob": None,
                    "thumbnailUrl": None,
                    "waveformData": None,
                    "isPlaceholder": False,
                    "url": sfx_http_url,
                    "originalUrl": sfx_http_url,
                })
                track_sfx["clips"].append({
                    "id": f"clip_sfx_{shot_id}",
                    "mediaId": sfx_media_id,
                    "trackId": "track_audio_sfx",
                    "startTime": max(0.0, st - 0.1),
                    "duration": 1.5,
                    "inPoint": 0.0,
                    "outPoint": 1.5,
                    "effects": [],
                    "audioEffects": [],
                    "transform": {"position": {"x": 0.5, "y": 0.5}, "scale": {"x": 1, "y": 1}, "rotation": 0, "anchor": {"x": 0.5, "y": 0.5}, "opacity": 1},
                    "volume": 0.85,
                    "keyframes": [],
                })

        # 5. Subtitles Structure with Word-Level Timestamps
        openreel_subtitles = []
        for s in edit_plan.subtitles:
            openreel_subtitles.append({
                "id": s.get("id", f"sub_{uuid.uuid4().hex[:6]}"),
                "text": s.get("text", ""),
                "startTime": float(s.get("startTime", 0.0)),
                "endTime": float(s.get("endTime", 0.0)),
                "animationStyle": s.get("animationStyle", "word-highlight"),
                "motionProfile": s.get("motionProfile", "word-pop"),
                "motionRecipe": s.get("motionRecipe", "motion-anything:word-pop"),
                "behindSubject": bool(s.get("behind_subject", s.get("behindSubject", False))),
                "style": s.get("style", {
                    "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                    "fontSize": 54,
                    "color": "#FFFFFF",
                    "backgroundColor": "transparent",
                    "position": "bottom",
                    "highlightColor": edit_plan.style.get("highlight_color", "#FFDD00"),
                }),
                "words": s.get("words", []),
            })

        # 6. Text Clips (Graphic Callouts & Hook Title with behindSubject)
        text_clips = []
        for i, ov in enumerate(edit_plan.text_overlays):
            ov_pos = ov.get("position", "center")
            # Upper third (behind head/neck) vs center vs lower third
            if ov_pos in ["top", "hook"]:
                pos_y = 0.28
                behind_subject = True
            elif ov_pos == "center":
                pos_y = 0.50
                behind_subject = ov.get("behind_subject", False)
            else:
                pos_y = 0.72
                behind_subject = False

            anim_preset = ov.get("animation_preset", ov.get("animation", "pop"))
            font_size = ov.get("font_size", 68 if behind_subject else 56)

            text_clips.append({
                "id": ov.get("id", f"text_ov_{i+1}"),
                "trackId": "track_overlay_text",
                "startTime": float(ov.get("start_time", 0.5)),
                "duration": float(ov.get("duration", 2.2)),
                "text": ov.get("text", "").upper() if behind_subject else ov.get("text", ""),
                "behindSubject": behind_subject,
                "animation": {
                    "preset": anim_preset,
                    "params": {
                        "popOvershoot": 1.15,
                        "bounceHeight": 20,
                        "slideDistance": 40,
                    },
                    "inDuration": 0.35,
                    "outDuration": 0.25,
                },
                "style": {
                    "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                    "fontSize": font_size,
                    "fontWeight": "bold",
                    "fontStyle": "normal",
                    "color": ov.get("emphasis_color", edit_plan.style.get("highlight_color", "#FFDD00")),
                    "strokeColor": "#000000",
                    "strokeWidth": 6,
                    "shadowColor": "rgba(0, 0, 0, 0.85)",
                    "shadowBlur": 10,
                    "textAlign": "center",
                    "verticalAlign": "middle",
                    "lineHeight": 1.15,
                    "letterSpacing": 0.8,
                },
                "transform": {
                    "position": {"x": 0.5, "y": pos_y},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                },
                "keyframes": [],
            })

        # Add content-aware kinetic graphics (Number stats, key term badges, lower thirds)
        for g in getattr(edit_plan, "graphics", []):
            g_st = float(g.get("start_time", 1.0))
            g_dur = float(g.get("duration", 2.5))
            p_text = g.get("primary_text", "")
            s_text = g.get("secondary_text", "")
            display_text = f"{p_text}\n{s_text}".strip() if s_text else p_text

            pos_y = (g.get("position", {}).get("y_percent", 25.0)) / 100.0
            pos_x = (g.get("position", {}).get("x_percent", 50.0)) / 100.0

            text_clips.append({
                "id": g.get("graphic_id", f"gfx_{len(text_clips)+1}"),
                "trackId": "track_overlay_text",
                "startTime": g_st,
                "duration": g_dur,
                "text": display_text,
                "behindSubject": False,
                "animation": {
                    "preset": g.get("animation_in", "pop_spring"),
                    "params": {"popOvershoot": 1.15, "bounceHeight": 20, "slideDistance": 40},
                    "inDuration": 0.35,
                    "outDuration": 0.25,
                },
                "style": {
                    "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                    "fontSize": 62 if g.get("graphic_type") == "number_stat" else 48,
                    "fontWeight": "black" if g.get("graphic_type") == "number_stat" else "bold",
                    "fontStyle": "normal",
                    "color": g.get("accent_color", "#FFCC00"),
                    "strokeColor": "#000000",
                    "strokeWidth": 6,
                    "shadowColor": "rgba(0, 0, 0, 0.85)",
                    "shadowBlur": 10,
                    "textAlign": "center",
                    "verticalAlign": "middle",
                    "lineHeight": 1.15,
                    "letterSpacing": 0.8,
                },
                "transform": {
                    "position": {"x": pos_x, "y": pos_y},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                },
                "keyframes": [],
            })

        # Assemble full Project model conforming to OpenReel Schema 1.2.0
        tracks_list = [track_main_video, track_broll_video, track_bgm]
        if track_sfx["clips"]:
            tracks_list.append(track_sfx)

        project = {
            "id": proj_id,
            "name": name,
            "createdAt": now_ms,
            "modifiedAt": now_ms,
            "settings": {
                "width": self.default_width,
                "height": self.default_height,
                "fps": self.default_fps,
                "frameRate": self.default_fps,
                "sampleRate": 48000,
                "channels": 2,
            },
            "timeline": {
                "tracks": tracks_list,
                "subtitles": openreel_subtitles,
                "duration": duration,
                "markers": [
                    {
                        "id": f"marker_{s.get('shot_id', i)}",
                        "time": float(s.get("start_time", 0.0)),
                        "label": f"B-Roll: {s.get('category', 'cutaway')}",
                        "color": "#F59E0B",
                    }
                    for i, s in enumerate(edit_plan.shots)
                ],
            },
            "mediaLibrary": {
                "items": media_items,
            },
            "textClips": text_clips,
            "shapeClips": [],
            "svgClips": [],
            "stickerClips": [],
            "capabilities": ["tracks-universal", "behind-subject", "subtitle-behind-subject"],
        }

        return {
            "version": OPENREEL_SCHEMA_VERSION,
            "project": project,
        }

    def export_project_files(
        self,
        edit_plan: EditPlan,
        output_dir: Path,
        project_filename: str = "project.oreel",
        resolved_broll_map: Optional[Dict[str, str]] = None,
        base_asset_url: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Export both native OpenReel .oreel file and companion project_manifest.json.

        Returns:
            Dict containing paths to created files: {"oreel": Path, "manifest": Path, "plan": Path}
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        project_data = self.create_openreel_project(
            edit_plan=edit_plan,
            project_name=edit_plan.title,
            resolved_broll_map=resolved_broll_map,
            base_asset_url=base_asset_url,
        )

        oreel_path = output_dir / project_filename
        with open(oreel_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)

        # Also write project.json for compatibility with OpenReel file picker
        json_path = output_dir / "project.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)

        # Write Edit Plan JSON
        plan_path = output_dir / "edit_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(edit_plan.to_dict(), f, indent=2)

        # Write OpenReel Project Manifest with import metadata
        manifest_data = {
            "manifest_version": "1.0.0",
            "openreel_schema_version": OPENREEL_SCHEMA_VERSION,
            "stockpile_version": getattr(edit_plan, "version", "2.1"),
            "project_id": project_data["project"]["id"],
            "title": edit_plan.title,
            "niche": edit_plan.niche.get("name"),
            "niche_id": edit_plan.niche.get("id"),
            "style": edit_plan.style.get("name"),
            "style_id": edit_plan.style.get("id"),
            "duration": edit_plan.target_duration,
            "resolution": f"{self.default_width}x{self.default_height} (9:16 vertical)",
            "tracks_count": len(project_data["project"]["timeline"]["tracks"]),
            "cuts_count": len(getattr(edit_plan, "cuts", [])),
            "broll_cutaways_count": len(edit_plan.shots),
            "graphics_count": len(getattr(edit_plan, "graphics", [])),
            "subtitles_count": len(edit_plan.subtitles),
            "text_overlays_count": len(edit_plan.text_overlays),
            "behind_subject_overlays_count": sum(1 for t in project_data["project"]["textClips"] if t.get("behindSubject")),
            "files": {
                "project_oreel": str(oreel_path.name),
                "project_json": str(json_path.name),
                "edit_plan": str(plan_path.name),
            },
            "openreel_instructions": "Load this project in OpenReel via useProjectStore.getState().loadProject(projectFile.project) or File -> Open Project.",
        }

        manifest_path = output_dir / "project_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Exported OpenReel project files to {output_dir}: {oreel_path.name}, {manifest_path.name}")
        return {
            "oreel": oreel_path,
            "project_json": json_path,
            "manifest": manifest_path,
            "plan": plan_path,
        }

    def update_edit_plan_from_openreel(
        self,
        edit_plan: EditPlan,
        openreel_data: Dict[str, Any],
    ) -> EditPlan:
        """Synchronize the complete editable OpenReel timeline back into EditPlan.

        OpenReel is treated as a non-destructive editor: the raw source remains the
        canonical A-roll media, while all A-roll segments, B-roll, captions, text,
        and SFX are independent timeline objects. Empty-but-present tracks are
        intentional edits and therefore must round-trip as empty lists.
        """
        proj = openreel_data.get("project", openreel_data)
        timeline = proj.get("timeline", {}) if isinstance(proj, dict) else {}
        tracks = timeline.get("tracks", []) if isinstance(timeline, dict) else []

        def track_by_id(track_id: str) -> Optional[Dict[str, Any]]:
            return next((t for t in tracks if t.get("id") == track_id), None)

        def first_track(*predicates):
            for track in tracks:
                if any(predicate(track) for predicate in predicates):
                    return track
            return None

        def text_clips_for_track(track_id: str) -> List[Dict[str, Any]]:
            return [
                clip for clip in (proj.get("textClips") or [])
                if str(clip.get("trackId", "")) == track_id
            ]

        # 1. A-Roll: synchronize every source segment, not only the first clip.
        main_track = track_by_id("track_video_main") or first_track(
            lambda t: t.get("role") == "dialogue" and t.get("type") == "video"
        )
        if main_track is not None:
            main_clips = [
                c for c in (main_track.get("clips") or [])
                if isinstance(c, dict)
            ]
            main_clips.sort(key=lambda c: float(c.get("startTime", 0.0)))

            if main_clips:
                updated_ranges = []
                for idx, clip in enumerate(main_clips):
                    start_time = max(0.0, float(clip.get("startTime", 0.0)))
                    duration = max(0.001, float(clip.get("duration", 0.0)))
                    source_in = max(
                        0.0,
                        float(
                            clip.get(
                                "inPoint",
                                clip.get("sourceIn", edit_plan.clip_interval.get("in_point", 0.0)),
                            )
                        ),
                    )
                    source_out = max(
                        source_in,
                        float(
                            clip.get(
                                "outPoint",
                                clip.get("sourceOut", source_in + duration),
                            )
                        ),
                    )
                    updated_ranges.append({
                        "start": round(start_time, 3),
                        "end": round(start_time + duration, 3),
                        "duration": round(duration, 3),
                        "source_in": round(source_in, 3),
                        "source_out": round(source_out, 3),
                    })

                edit_plan.a_roll_ranges = updated_ranges
                edit_plan.keep_intervals = [
                    (r["start"], r["end"]) for r in updated_ranges
                ]

                source_starts = [r["source_in"] for r in updated_ranges]
                source_ends = [r["source_out"] for r in updated_ranges]
                if source_starts and source_ends:
                    edit_plan.clip_interval["in_point"] = min(source_starts)
                    edit_plan.clip_interval["out_point"] = max(source_ends)

                timeline_duration = float(timeline.get("duration", 0.0) or 0.0)
                active_end = max(r["end"] for r in updated_ranges)
                edit_plan.target_duration = round(
                    max(active_end, timeline_duration) if timeline_duration > 0 else active_end,
                    3,
                )

        # 2. B-Roll: an empty existing track means the user deleted all B-roll.
        broll_track = track_by_id("track_video_broll")
        if broll_track is not None:
            broll_clips = [
                c for c in (broll_track.get("clips") or [])
                if isinstance(c, dict)
            ]
            existing_shots_by_id = {
                str(s.get("shot_id")): s for s in edit_plan.shots
                if s.get("shot_id") is not None
            }
            updated_shots = []

            for clip in broll_clips:
                clip_id = str(clip.get("id", ""))
                media_id = str(clip.get("mediaId", ""))
                start_time = max(0.0, float(clip.get("startTime", 0.0)))
                duration = max(0.001, float(clip.get("duration", 0.0)))
                matched_shot = None

                for sid, shot in existing_shots_by_id.items():
                    if (
                        sid == clip_id
                        or f"clip_{sid}" == clip_id
                        or f"media_{sid}" == media_id
                    ):
                        matched_shot = dict(shot)
                        break

                if matched_shot is None:
                    matched_shot = {
                        "shot_id": clip_id or f"broll_custom_{int(start_time * 1000)}",
                        "visual_prompt": clip.get("name", "Custom B-Roll Cutaway"),
                        "rationale": "User-added cutaway in OpenReel timeline",
                    }

                matched_shot["start_time"] = round(start_time, 3)
                matched_shot["duration"] = round(duration, 3)
                matched_shot["end_time"] = round(start_time + duration, 3)

                in_point = clip.get("inPoint")
                out_point = clip.get("outPoint")
                if in_point is not None:
                    matched_shot["asset_in_point"] = float(in_point)
                if out_point is not None:
                    matched_shot["asset_out_point"] = float(out_point)

                metadata = clip.get("metadata") or {}
                if metadata.get("searchQuery"):
                    matched_shot["search_query"] = metadata["searchQuery"]
                if metadata.get("rationale"):
                    matched_shot["rationale"] = metadata["rationale"]
                if metadata.get("category"):
                    matched_shot["category"] = metadata["category"]

                updated_shots.append(matched_shot)

            updated_shots.sort(key=lambda s: float(s.get("start_time", 0.0)))
            edit_plan.shots = updated_shots

        # 3. Captions: editable OpenReel TextClips are authoritative.
        captions_track = track_by_id("track_captions") or first_track(
            lambda t: t.get("role") == "captions"
            or str(t.get("name", "")).strip().lower() == "captions"
        )
        caption_texts = text_clips_for_track(captions_track.get("id")) if captions_track else []

        if caption_texts:
            caption_texts.sort(key=lambda c: float(c.get("startTime", 0.0)))
            existing_subs = {
                str(s.get("id")): s for s in edit_plan.subtitles
                if s.get("id") is not None
            }
            synced_subtitles = []

            for clip in caption_texts:
                metadata = clip.get("metadata") or {}
                sub_id = str(
                    metadata.get("subtitleId")
                    or clip.get("id")
                    or f"sub_{uuid.uuid4().hex[:6]}"
                )
                original = existing_subs.get(sub_id, {})

                start_time = float(clip.get("startTime", original.get("startTime", 0.0)))
                duration = max(0.001, float(clip.get("duration", 0.0)))
                words = metadata.get("words", original.get("words", []))

                synced_subtitles.append({
                    **original,
                    "id": sub_id,
                    "text": clip.get("text", original.get("text", "")),
                    "startTime": round(start_time, 3),
                    "endTime": round(start_time + duration, 3),
                    "animationStyle": metadata.get(
                        "animationStyle",
                        original.get("animationStyle", "word-highlight"),
                    ),
                    "motionProfile": metadata.get(
                        "motionProfile",
                        original.get("motionProfile", "word-pop"),
                    ),
                    "motionRecipe": metadata.get(
                        "motionRecipe",
                        original.get("motionRecipe", "motion-anything:word-pop"),
                    ),
                    "behind_subject": bool(
                        clip.get(
                            "behindSubject",
                            original.get("behind_subject", False),
                        )
                    ),
                    "style": clip.get("style", original.get("style", {})),
                    "words": words or [],
                })

            edit_plan.subtitles = synced_subtitles
        elif isinstance(timeline.get("subtitles"), list):
            # Backwards compatibility for older projects with no Captions TextClips.
            edit_plan.subtitles = [
                {
                    "id": sub.get("id"),
                    "startTime": float(sub.get("startTime", sub.get("start", 0.0))),
                    "endTime": float(sub.get("endTime", sub.get("end", 0.0))),
                    "text": sub.get("text", ""),
                    "animationStyle": sub.get("animationStyle", "word-highlight"),
                    "motionProfile": sub.get("motionProfile", "word-pop"),
                    "motionRecipe": sub.get("motionRecipe", "motion-anything:word-pop"),
                    "behind_subject": bool(
                        sub.get("behindSubject", sub.get("behind_subject", False))
                    ),
                    "style": sub.get("style", {}),
                    "words": sub.get("words", []),
                }
                for sub in timeline.get("subtitles", [])
            ]

        edit_plan.subtitles_behind_subject = any(
            bool(s.get("behind_subject", s.get("behindSubject", False)))
            for s in edit_plan.subtitles
        )

        # 4. Hook/text overlays: synchronize the dedicated OpenReel text track.
        overlay_track = track_by_id("track_overlay_text")
        if overlay_track is not None:
            overlays = []
            existing_overlays = {
                str(o.get("id")): o for o in edit_plan.text_overlays
                if o.get("id") is not None
            }

            for clip in text_clips_for_track(overlay_track.get("id")):
                clip_id = str(clip.get("id") or f"text_ov_{uuid.uuid4().hex[:6]}")
                original = existing_overlays.get(clip_id, {})
                start_time = float(clip.get("startTime", original.get("start_time", 0.0)))
                duration = max(0.001, float(clip.get("duration", original.get("duration", 2.5))))

                overlays.append({
                    **original,
                    "id": clip_id,
                    "text": clip.get("text", original.get("text", "")),
                    "start_time": round(start_time, 3),
                    "duration": round(duration, 3),
                    "end_time": round(start_time + duration, 3),
                    "behind_subject": bool(
                        clip.get("behindSubject", original.get("behind_subject", False))
                    ),
                    "style": clip.get("style", original.get("style", {})),
                    "transform": clip.get("transform", original.get("transform", {})),
                    "animation": clip.get("animation", original.get("animation", {})),
                })

            edit_plan.text_overlays = sorted(
                overlays,
                key=lambda item: float(item.get("start_time", 0.0)),
            )

        # 5. SFX: canonical audio_cues["sfx"] is synchronized from the SFX track.
        sfx_track = track_by_id("track_audio_sfx") or first_track(
            lambda t: t.get("role") == "effects"
        )
        if sfx_track is not None:
            project_media = {
                str(item.get("id")): item
                for item in (proj.get("mediaLibrary", {}).get("items", []) or [])
                if item.get("id")
            }
            prior_sfx = edit_plan.audio_cues.get("sfx", []) if isinstance(edit_plan.audio_cues, dict) else []
            prior_by_id = {
                str(c.get("id") or c.get("cue_id")): c
                for c in prior_sfx
                if c.get("id") is not None or c.get("cue_id") is not None
            }

            synced_sfx = []
            for clip in (sfx_track.get("clips") or []):
                metadata = clip.get("metadata") or {}
                cue_id = str(
                    metadata.get("cueId")
                    or clip.get("id", "").replace("clip_sfx_", "")
                    or f"sfx_{uuid.uuid4().hex[:6]}"
                )
                prior = dict(prior_by_id.get(cue_id, {}))
                media = project_media.get(str(clip.get("mediaId")), {})
                source_file = metadata.get("sourceFile") or prior.get("file") or ""
                if not source_file:
                    source_file = (
                        (media.get("sourceFile") or {}).get("folder", "")
                        + ("/" if (media.get("sourceFile") or {}).get("folder") else "")
                        + (media.get("sourceFile") or {}).get("name", "")
                    ) or media.get("originalUrl") or media.get("url") or media.get("name", "")

                synced_sfx.append({
                    **prior,
                    "id": cue_id,
                    "file": source_file,
                    "time": round(float(clip.get("startTime", 0.0)), 3),
                    "duration": round(max(0.05, float(clip.get("duration", 0.8))), 3),
                    "volume": float(clip.get("volume", prior.get("volume", 0.7))),
                    "event_type": metadata.get("eventType", prior.get("event_type", "sfx")),
                    "justification": metadata.get("justification", prior.get("justification", "")),
                    "sync_target": metadata.get("syncTarget", prior.get("sync_target", "")),
                    "category": metadata.get("category", prior.get("category", "accent")),
                })

            edit_plan.audio_cues = {
                **(edit_plan.audio_cues if isinstance(edit_plan.audio_cues, dict) else {}),
                "sfx": synced_sfx,
            }

        logger.info(
            "Updated EditPlan from OpenReel: "
            f"{len(edit_plan.a_roll_ranges)} A-roll segments, "
            f"{len(edit_plan.shots)} B-roll shots, "
            f"{len(edit_plan.subtitles)} captions, "
            f"{len(edit_plan.text_overlays)} text overlays, "
            f"{len(edit_plan.audio_cues.get('sfx', []) if isinstance(edit_plan.audio_cues, dict) else [])} SFX, "
            f"duration={edit_plan.target_duration}s"
        )
        return edit_plan


# Global adapter instance
openreel_adapter = OpenReelAdapter()
