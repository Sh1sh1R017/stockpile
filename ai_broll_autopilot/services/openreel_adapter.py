"""OpenReel Adapter.

Converts Stockpile Edit Plans into native OpenReel Schema 1.2.0 projects (.oreel / project.json).
Preserves non-destructive multitrack structure: separate tracks for main speaker video,
B-roll cutaways, subtitles with word-highlight timings, text overlays, and audio mix.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.services.edit_director import EditPlan

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
    ) -> Dict[str, Any]:
        """Generate OpenReel Schema 1.2.0 ProjectFile JSON dict.

        Args:
            edit_plan: Stockpile EditPlan instance.
            project_name: Optional custom project name.
            resolved_broll_map: Optional map of shot_id -> local file path for B-roll assets.

        Returns:
            Dict conforming to OpenReel's ProjectFile { "version": "1.2.0", "project": { ... } }
        """
        proj_id = f"proj_{uuid.uuid4().hex[:12]}"
        name = project_name or edit_plan.title or "Stockpile Viral Short"
        duration = edit_plan.target_duration

        # 1. Media Library Setup
        media_items: List[Dict[str, Any]] = []
        source_media = edit_plan.source_media
        source_path = source_media.get("path", "")
        source_media_id = "media_source_main"

        media_items.append({
            "id": source_media_id,
            "name": Path(source_path).name if source_path else "source_video.mp4",
            "type": "video",
            "metadata": {
                "duration": source_media.get("duration", duration),
                "width": source_media.get("width", 1920),
                "height": source_media.get("height", 1080),
                "frameRate": source_media.get("fps", self.default_fps),
                "codec": "h264",
            },
            "sourceFile": {
                "name": Path(source_path).name if source_path else "source_video.mp4",
                "size": 0,
                "lastModified": 1720000000000,
            },
            "url": f"file:///{Path(source_path).as_posix()}" if source_path else "",
        })

        # Add B-roll media items
        broll_map = resolved_broll_map or {}
        for shot in edit_plan.shots:
            shot_id = shot.get("shot_id", "broll")
            asset_path = shot.get("asset_path") or broll_map.get(shot_id)
            if asset_path:
                media_items.append({
                    "id": f"media_{shot_id}",
                    "name": Path(asset_path).name,
                    "type": "video",
                    "metadata": {
                        "duration": shot.get("duration", 3.0),
                        "width": 1920,
                        "height": 1080,
                        "frameRate": self.default_fps,
                        "codec": "h264",
                    },
                    "sourceFile": {
                        "name": Path(asset_path).name,
                        "size": 0,
                        "lastModified": 1720000000000,
                    },
                    "url": f"file:///{Path(asset_path).as_posix()}",
                })

        # 2. Timeline Tracks
        track_main_video = {
            "id": "track_video_main",
            "name": "Speaker / A-Roll",
            "type": "video",
            "clips": [],
            "visible": True,
            "muted": False,
            "locked": False,
            "volume": 1.0,
        }

        track_broll_video = {
            "id": "track_video_broll",
            "name": "B-Roll Cutaways",
            "type": "video",
            "clips": [],
            "visible": True,
            "muted": False,
            "locked": False,
            "volume": 0.0,
        }

        track_bgm = {
            "id": "track_audio_bgm",
            "name": "Background Music",
            "type": "audio",
            "clips": [],
            "visible": True,
            "muted": False,
            "locked": False,
            "volume": edit_plan.style.get("bgm_ducking_volume", 0.18),
        }

        # 3. Main Speaker Clip (Trimmed to In/Out points with 9:16 vertical cover fit)
        in_pt = edit_plan.clip_interval.get("in_point", 0.0)
        out_pt = edit_plan.clip_interval.get("out_point", in_pt + duration)

        # Build keyframes for subtle punch-in zooms if specified
        keyframes = []
        for zoom in edit_plan.zooms:
            z_time = zoom.get("time", 0.0)
            z_scale = zoom.get("scale", 1.06)
            keyframes.append({
                "id": f"kf_zoom_{uuid.uuid4().hex[:6]}",
                "time": z_time,
                "property": "transform.scale",
                "value": {"x": z_scale, "y": z_scale},
                "easing": zoom.get("easing", "ease-out"),
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
                "position": {"x": 0, "y": 0},
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

        # 4. B-Roll Overlay Clips
        for i, shot in enumerate(edit_plan.shots):
            shot_id = shot.get("shot_id", f"broll_{i+1}")
            st = shot.get("start_time", 0.0)
            dur = shot.get("duration", 2.0)
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
                    "position": {"x": 0, "y": 0},
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
                }
            }
            track_broll_video["clips"].append(broll_clip)

        # 5. Subtitles Structure
        openreel_subtitles = []
        for s in edit_plan.subtitles:
            openreel_subtitles.append({
                "id": s.get("id", f"sub_{uuid.uuid4().hex[:6]}"),
                "text": s.get("text", ""),
                "startTime": s.get("startTime", 0.0),
                "endTime": s.get("endTime", 0.0),
                "animationStyle": s.get("animationStyle", "word-highlight"),
                "style": s.get("style", {
                    "fontFamily": "Montserrat",
                    "fontSize": 54,
                    "color": "#FFFFFF",
                    "backgroundColor": "transparent",
                    "position": "bottom",
                    "highlightColor": "#FFDD00",
                }),
                "words": s.get("words", []),
            })

        # 6. Text Clips (Graphic Callouts & Hook Title)
        text_clips = []
        for i, ov in enumerate(edit_plan.text_overlays):
            text_clips.append({
                "id": ov.get("id", f"text_ov_{i+1}"),
                "trackId": "track_overlay_text",
                "startTime": ov.get("start_time", 0.5),
                "duration": ov.get("duration", 2.0),
                "text": ov.get("text", ""),
                "style": {
                    "fontFamily": edit_plan.style.get("font_family", "Montserrat"),
                    "fontSize": 62,
                    "fontWeight": "bold",
                    "fontStyle": "normal",
                    "color": ov.get("emphasis_color", edit_plan.style.get("highlight_color", "#FFDD00")),
                    "strokeColor": "#000000",
                    "strokeWidth": 5,
                    "shadowColor": "rgba(0, 0, 0, 0.8)",
                    "shadowBlur": 8,
                    "textAlign": "center",
                    "verticalAlign": "middle",
                    "lineHeight": 1.2,
                    "letterSpacing": 0.8,
                },
                "transform": {
                    "position": {"x": 0, "y": -180 if ov.get("position") == "center" else 200},
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0,
                    "anchor": {"x": 0.5, "y": 0.5},
                    "opacity": 1.0,
                },
                "keyframes": [],
            })

        # Assemble full Project model
        project = {
            "id": proj_id,
            "name": name,
            "settings": {
                "width": self.default_width,
                "height": self.default_height,
                "fps": self.default_fps,
            },
            "timeline": {
                "tracks": [track_main_video, track_broll_video, track_bgm],
                "subtitles": openreel_subtitles,
                "transitions": [],
                "markers": [
                    {
                        "id": f"marker_{s.get('shot_id', i)}",
                        "time": s.get("start_time", 0.0),
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
            "graphics": [],
            "captions": [],
        }

        # Return OpenReel Serialized ProjectFile
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
    ) -> Dict[str, Path]:
        """Export both native OpenReel .oreel file and companion project_manifest.json.

        Returns:
            Dict containing paths to created files: {"oreel": Path, "manifest": Path, "plan": Path}
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate OpenReel ProjectFile
        project_data = self.create_openreel_project(
            edit_plan=edit_plan,
            project_name=edit_plan.title,
            resolved_broll_map=resolved_broll_map,
        )

        oreel_path = output_dir / project_filename
        with open(oreel_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)

        # Also write project.json for compatibility
        json_path = output_dir / "project.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)

        # 2. Write Edit Plan JSON
        plan_path = output_dir / "edit_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(edit_plan.to_dict(), f, indent=2)

        # 3. Write OpenReel Project Manifest with import metadata
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


# Global adapter instance
openreel_adapter = OpenReelAdapter()
