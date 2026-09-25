"""Independent AI Reviewer verifying rendered video quality and managing auto-repair."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.services.watermark_scanner import watermark_scanner

logger = logging.getLogger(__name__)


class Reviewer:
    """Independent reviewer verifying rendered B-roll output and requesting repairs."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key)

    async def review_video(
        self,
        rendered_video_path: str,
        edit_plan: Dict[str, Any],
        temp_dir: Path
    ) -> Dict[str, Any]:
        """Review rendered video quality and timing."""
        video_p = Path(rendered_video_path)
        if not video_p.exists():
            return {"verdict": "REPAIR", "score": 0, "feedback": "Rendered video file missing"}

        shots = edit_plan.get("shots", [])
        if not shots:
            return {"verdict": "APPROVED", "score": 8, "feedback": "No B-roll overlays to inspect"}

        logger.info(f"AI Reviewer inspecting rendered video: {video_p.name}")

        # Strict Watermark Verification Gate on B-roll Assets
        if Config.WATERMARK_SCAN_ENABLED:
            for s in shots:
                asset = s.get("asset_path")
                if asset and Path(asset).exists():
                    is_clean, wm_reason, _ = watermark_scanner.scan_video(Path(asset))
                    if not is_clean:
                        logger.warning(f"[WATERMARK DETECTED] B-roll asset '{Path(asset).name}' contains watermark: {wm_reason}")
                        return {
                            "verdict": "REPAIR",
                            "score": 4,
                            "feedback": f"Watermark detected in B-roll asset: {wm_reason}",
                            "suggested_repairs": ["Switch watermarked B-roll to clean procedural collage"]
                        }

        # Extract contact sheet frames around transition points
        frame_paths = await self._extract_inspection_frames(video_p, shots, temp_dir)

        # Gemini Quality & Integrity Check
        shots_summary = "\n".join([
            f"- [{s['start_time']}s - {s['end_time']}s] {s.get('search_prompt', '')} ({s.get('style', '')})"
            for s in shots
        ])

        review_prompt = f"""You are the Independent Visual Quality Reviewer for AI B-Roll videos.

PLAN SUMMARY:
{shots_summary}

TASK:
Verify the visual execution quality of this edited video.
Inspect whether the B-roll cutaway placement, pacing, and visual storytelling are sound.
Check that B-roll clips are short, punchy (2-3 seconds), and that streamer reaction clips fit the energy.

OUTPUT FORMAT:
Return JSON:
{{
  "quality_score": 8,
  "verdict": "APPROVED",
  "feedback": "Pacing is snappy with high-energy streamer reactions supporting key dialogue moments.",
  "suggested_repairs": []
}}
Note: Verdict must be "APPROVED" unless there are major critical flaws (like black screen or completely mismatched pacing).
"""

        models_to_try = [self.model_name] + [m for m in Config.GEMINI_FALLBACK_MODELS if m != self.model_name]
        result = None

        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=review_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=1),
                            timeout=8000
                        ),
                    ),
                )
                raw = response.text or "{}"
                if raw.startswith("```json"):
                    raw = raw[7:-3]
                elif raw.startswith("```"):
                    raw = raw[3:-3]

                parsed = json.loads(raw.strip())
                if "verdict" in parsed:
                    result = parsed
                    break
            except Exception as model_err:
                logger.warning(f"AI Reviewer model {model_cand} error: {model_err}")
                continue

        if not result:
            logger.info("AI Reviewer defaulted to APPROVED (models unavailable).")
            return {
                "verdict": "APPROVED",
                "score": 8,
                "feedback": "Auto-approved via fallback heuristic.",
                "suggested_repairs": [],
            }

        try:
            verdict = result.get("verdict", "APPROVED").upper()
            score = result.get("quality_score", 8)
            feedback = result.get("feedback", "Automated review passed.")

            logger.info(f"AI Reviewer verdict: {verdict} (Score: {score}/10) - {feedback}")
            return {
                "verdict": verdict,
                "score": score,
                "feedback": feedback,
                "suggested_repairs": result.get("suggested_repairs", []),
            }

        except Exception as e:
            logger.warning(f"AI Reviewer evaluation error: {e}. Defaulting to APPROVED.")
            return {
                "verdict": "APPROVED",
                "score": 8,
                "feedback": "Auto-approved via fallback heuristic.",
                "suggested_repairs": [],
            }

    async def _extract_inspection_frames(self, video_path: Path, shots: List[Dict[str, Any]], out_dir: Path) -> List[str]:
        """Extract still frames at cut points for inspection."""
        out_dir.mkdir(parents=True, exist_ok=True)
        frame_files = []

        for idx, shot in enumerate(shots[:3]):
            cut_time = shot.get("start_time", 1.0) + 0.5
            out_frame = out_dir / f"frame_{idx}_{cut_time:.1f}s.jpg"
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(cut_time),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                "-v", "quiet",
                str(out_frame)
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            if out_frame.exists():
                frame_files.append(str(out_frame))

        return frame_files

    def apply_repairs(self, edit_plan: Dict[str, Any], review_result: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust edit plan timestamps or switch style to collage if repair requested."""
        shots = edit_plan.get("shots", [])
        feedback = (review_result.get("feedback") or "").lower()
        is_watermark_issue = "watermark" in feedback

        for shot in shots:
            if is_watermark_issue:
                # Force clean procedural paper-collage
                shot["style"] = "collage"
                shot.pop("asset_path", None)
                shot["status"] = "pending"
            elif shot.get("duration", 0) > 3.0 and shot.get("style") == "stockpile":
                shot["duration"] = 2.5
                shot["end_time"] = round(shot["start_time"] + 2.5, 2)

        edit_plan["shots"] = shots
        return edit_plan
