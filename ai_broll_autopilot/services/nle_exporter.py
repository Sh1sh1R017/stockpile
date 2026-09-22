"""Universal NLE Project Exporter for Adobe Premiere Pro, DaVinci Resolve & Final Cut Pro.

Inspired by Rotodraft Suite: Generates FCP 7 XML multi-track timelines with
A-roll on Video Track 1, B-roll cutaways on Video Track 2 at exact millisecond
placements, dialogue/metaphor markers, and 1-Click ZIP bundles.
"""

import io
import json
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class NLEExporter:
    """Exports multi-track timelines to Premiere Pro, DaVinci Resolve & ZIP packages."""

    @staticmethod
    def generate_fcp_xml(
        project_name: str,
        base_video_path: str,
        total_duration: float,
        shots: List[Dict[str, Any]],
        fps: int = 30,
        width: int = 1080,
        height: int = 1920
    ) -> str:
        """Generates standard Final Cut Pro 7 XML compatible with Adobe Premiere Pro and DaVinci Resolve."""
        root = ET.Element("xmeml", version="4")
        sequence = ET.SubElement(root, "sequence")
        ET.SubElement(sequence, "name").text = project_name

        total_frames = max(1, int(fps * total_duration))
        ET.SubElement(sequence, "duration").text = str(total_frames)

        rate = ET.SubElement(sequence, "rate")
        ET.SubElement(rate, "timebase").text = str(fps)
        ET.SubElement(rate, "ntsc").text = "FALSE"

        media = ET.SubElement(sequence, "media")
        video = ET.SubElement(media, "video")
        format_el = ET.SubElement(video, "format")
        sample = ET.SubElement(format_el, "samplecharacteristics")
        ET.SubElement(sample, "width").text = str(width)
        ET.SubElement(sample, "height").text = str(height)

        base_p = Path(base_video_path) if base_video_path else Path("base_video.mp4")

        # ── TRACK 1: BASE SPEAKER VIDEO (A-ROLL) ──
        track_aroll = ET.SubElement(video, "track")
        clip_base = ET.SubElement(track_aroll, "clipitem", id="clipitem-aroll-1")
        ET.SubElement(clip_base, "name").text = base_p.name
        ET.SubElement(clip_base, "duration").text = str(total_frames)
        ET.SubElement(clip_base, "start").text = "0"
        ET.SubElement(clip_base, "end").text = str(total_frames)
        ET.SubElement(clip_base, "in").text = "0"
        ET.SubElement(clip_base, "out").text = str(total_frames)

        file_base = ET.SubElement(clip_base, "file", id="file-aroll")
        ET.SubElement(file_base, "name").text = base_p.name
        try:
            ET.SubElement(file_base, "pathurl").text = base_p.resolve().as_uri()
        except Exception:
            ET.SubElement(file_base, "pathurl").text = f"file://localhost/{base_p.name}"

        # ── TRACK 2: B-ROLL CUTAWAYS (OVERLAYS) ──
        track_broll = ET.SubElement(video, "track")
        for i, shot in enumerate(shots, 1):
            asset_path = shot.get("asset_path")
            b_name = Path(asset_path).name if asset_path else f"broll_{i}.mp4"
            b_uri = Path(asset_path).resolve().as_uri() if asset_path and Path(asset_path).exists() else f"file://localhost/broll/{b_name}"

            start_sec = float(shot.get("start_time", 0.0))
            end_sec = float(shot.get("end_time", start_sec + 2.5))
            dur_sec = max(0.5, end_sec - start_sec)

            start_f = int(fps * start_sec)
            end_f = int(fps * end_sec)
            dur_f = max(1, end_f - start_f)

            clip_b = ET.SubElement(track_broll, "clipitem", id=f"clipitem-broll-{i}")
            ET.SubElement(clip_b, "name").text = b_name
            ET.SubElement(clip_b, "duration").text = str(dur_f)
            ET.SubElement(clip_b, "start").text = str(start_f)
            ET.SubElement(clip_b, "end").text = str(end_f)
            ET.SubElement(clip_b, "in").text = "0"
            ET.SubElement(clip_b, "out").text = str(dur_f)

            file_b = ET.SubElement(clip_b, "file", id=f"file-broll-{i}")
            ET.SubElement(file_b, "name").text = b_name
            ET.SubElement(file_b, "pathurl").text = b_uri

            # Ingest Dialogue & Metaphor Marker directly onto NLE Timeline
            marker = ET.SubElement(clip_b, "marker")
            ET.SubElement(marker, "name").text = f"Cut {i}: {shot.get('emotional_core', 'B-Roll')}"
            quote = shot.get("dialogue_quote", "")
            metaphor = shot.get("visceral_human_metaphor", "")
            ET.SubElement(marker, "comment").text = f"Quote: \"{quote}\" | Metaphor: {metaphor}"
            ET.SubElement(marker, "in").text = "0"

        # ── AUDIO TRACK: BASE AUDIO ──
        audio = ET.SubElement(media, "audio")
        track_a = ET.SubElement(audio, "track")
        clip_a = ET.SubElement(track_a, "clipitem", id="clipitem-audio-1")
        ET.SubElement(clip_a, "name").text = f"{base_p.stem}_audio"
        ET.SubElement(clip_a, "duration").text = str(total_frames)
        ET.SubElement(clip_a, "start").text = "0"
        ET.SubElement(clip_a, "end").text = str(total_frames)
        ET.SubElement(clip_a, "in").text = "0"
        ET.SubElement(clip_a, "out").text = str(total_frames)
        ET.SubElement(clip_a, "file", id="file-aroll")

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    @classmethod
    def create_zip_package(cls, job: Any, output_zip_path: Path) -> Path:
        """Create a complete production ZIP archive containing master video, XML, SRT, and B-roll clips."""
        output_zip_path.parent.mkdir(parents=True, exist_ok=True)
        shots = job.edit_plan.get("shots", []) if (job.edit_plan and isinstance(job.edit_plan, dict)) else []
        total_dur = job.edit_plan.get("total_duration", 12.0) if job.edit_plan else 12.0

        # Generate XML
        xml_content = cls.generate_fcp_xml(
            project_name=job.source_filename,
            base_video_path=job.source_file,
            total_duration=total_dur,
            shots=shots,
            width=Config.TARGET_WIDTH,
            height=Config.TARGET_HEIGHT,
            fps=Config.TARGET_FPS,
        )

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # 1. Timeline XML for Premiere Pro / DaVinci
            zipf.writestr(f"timeline_premiere_davinci.xml", xml_content)

            # 2. Master Rendered Video if exists
            if job.output_video_path and Path(job.output_video_path).exists():
                zipf.write(job.output_video_path, arcname=f"master_{Path(job.output_video_path).name}")

            # 3. Individual B-roll Cutaway Clips
            for idx, s in enumerate(shots, 1):
                p = s.get("asset_path")
                if p and Path(p).exists():
                    zipf.write(p, arcname=f"broll_cutaways/{Path(p).name}")

            # 4. SRT Subtitles if transcript exists
            if job.transcript_segments:
                srt_lines = []
                for seg in job.transcript_segments:
                    start_s = seg["start"]
                    end_s = seg["end"]
                    def to_srt_tc(t):
                        hrs = int(t // 3600)
                        mins = int((t % 3600) // 60)
                        secs = int(t % 60)
                        ms = int((t - int(t)) * 1000)
                        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"
                    srt_lines.append(f"{seg.get('id', 1)}\n{to_srt_tc(start_s)} --> {to_srt_tc(end_s)}\n{seg['text'].strip()}\n")
                zipf.writestr("subtitles.srt", "\n".join(srt_lines))

            # 5. Metadata and Review Audit Report
            report = {
                "job_id": job.job_id,
                "filename": job.source_filename,
                "total_duration": total_dur,
                "review_audit": job.review_data,
                "edit_plan": job.edit_plan,
            }
            zipf.writestr("audit_report.json", json.dumps(report, indent=2))

        logger.info(f"NLE ZIP package created: {output_zip_path} ({output_zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return output_zip_path
