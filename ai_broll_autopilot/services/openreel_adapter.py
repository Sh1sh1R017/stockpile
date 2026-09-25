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
from ai_broll_autopilot.services.subject_isolation import subject_isolation_service

logger = logging.getLogger(__name__)

OPENREEL_SCHEMA_VERSION = "1.2.0"


class OpenReelAdapter:
    """Transforms Stockpile EditPlan into OpenReel Schema 1.2.0 native project file."""

    def __init__(self, default_width: int = 1080, default_height: int = 1920, default_fps: int = 30):
        self.default_width = default_width
        self.default_height = default_height
        self.default_fps = default_fps

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
            "capabilities": ["tracks-universal", "behind-subject"],
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
            "project_id": project_data["project"]["id"],
            "title": edit_plan.title,
            "niche": edit_plan.niche.get("name"),
            "niche_id": edit_plan.niche.get("id"),
            "style": edit_plan.style.get("name"),
            "style_id": edit_plan.style.get("id"),
            "duration": edit_plan.target_duration,
            "resolution": f"{self.default_width}x{self.default_height} (9:16 vertical)",
            "tracks_count": len(project_data["project"]["timeline"]["tracks"]),
            "broll_cutaways_count": len(edit_plan.shots),
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
        """Synchronize user timeline edits from OpenReel Schema 1.2.0 back into Stockpile EditPlan.

        Extracts updated shot start times, durations, and asset mappings from B-Roll track,
        updated in/out points from A-roll track, subtitles, and text overlays.
        """
        proj = openreel_data.get("project", openreel_data)
        timeline = proj.get("timeline", {})
        tracks = timeline.get("tracks", [])

        # 1. Update A-Roll (main video) interval & target duration
        for trk in tracks:
            if trk.get("id") == "track_video_main" or trk.get("role") == "dialogue":
                clips = trk.get("clips", [])
                if clips:
                    main_clip = clips[0]
                    in_pt = float(main_clip.get("inPoint", edit_plan.clip_interval.get("in_point", 0.0)))
                    dur = float(main_clip.get("duration", edit_plan.target_duration))
                    edit_plan.clip_interval["in_point"] = in_pt
                    edit_plan.clip_interval["out_point"] = in_pt + dur
                    edit_plan.target_duration = dur

        # 2. Update B-Roll cutaway shots
        broll_clips = []
        for trk in tracks:
            if trk.get("id") == "track_video_broll" or (trk.get("type") == "video" and trk.get("role") != "dialogue"):
                broll_clips = trk.get("clips", [])
                break

        if broll_clips:
            updated_shots = []
            existing_shots_by_id = {s.get("shot_id"): s for s in edit_plan.shots}

            for clip in broll_clips:
                clip_id = clip.get("id", "")
                st = float(clip.get("startTime", 0.0))
                dur = float(clip.get("duration", 2.5))
                end = st + dur
                media_id = clip.get("mediaId", "")

                matched_shot = None
                for sid, s in existing_shots_by_id.items():
                    if sid == clip_id or f"clip_{sid}" == clip_id or f"media_{sid}" == media_id:
                        matched_shot = s.copy()
                        break

                if not matched_shot:
                    matched_shot = {
                        "shot_id": clip_id or f"broll_custom_{int(st*10)}",
                        "visual_prompt": clip.get("name", "Custom B-Roll Cutaway"),
                        "rationale": "User-added cutaway in OpenReel timeline",
                    }

                matched_shot["start_time"] = round(st, 3)
                matched_shot["duration"] = round(dur, 3)
                matched_shot["end_time"] = round(end, 3)

                # Preserve transition info if modified in OpenReel
                trans_list = trk.get("transitions", [])
                for t in trans_list:
                    if t.get("toClipId") == clip_id or t.get("fromClipId") == clip_id:
                        matched_shot.setdefault("transition", {})["type"] = t.get("type", "crossfade")
                        matched_shot["transition"]["duration"] = float(t.get("duration", 0.3))

                updated_shots.append(matched_shot)

            updated_shots.sort(key=lambda s: s.get("start_time", 0.0))
            edit_plan.shots = updated_shots

        # 3. Update Subtitles if present
        openreel_subs = timeline.get("subtitles", [])
        if openreel_subs:
            subs = []
            for sub in openreel_subs:
                subs.append({
                    "id": sub.get("id"),
                    "start": float(sub.get("startTime", 0.0)),
                    "end": float(sub.get("endTime", 0.0)),
                    "text": sub.get("text", ""),
                    "words": sub.get("words", []),
                })
            edit_plan.subtitles = subs

        # 4. Update Text Overlays from textClips
        text_clips = proj.get("textClips", [])
        if text_clips:
            overlays = []
            for tc in text_clips:
                overlays.append({
                    "id": tc.get("id"),
                    "text": tc.get("text", ""),
                    "start_time": float(tc.get("startTime", 0.0)),
                    "duration": float(tc.get("duration", 2.5)),
                    "end_time": float(tc.get("startTime", 0.0)) + float(tc.get("duration", 2.5)),
                    "behind_subject": bool(tc.get("behindSubject", False)),
                    "style": tc.get("style", {}),
                    "transform": tc.get("transform", {}),
                    "animation": tc.get("animation", {}),
                })
            edit_plan.text_overlays = overlays

        logger.info(
            f"Updated EditPlan from OpenReel: {len(edit_plan.shots)} shots, "
            f"{len(edit_plan.subtitles)} subtitles, duration={edit_plan.target_duration}s"
        )
        return edit_plan


# Global adapter instance
openreel_adapter = OpenReelAdapter()
