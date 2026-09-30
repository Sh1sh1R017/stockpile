"""Audio-aware, sentiment-driven B-roll selection brain for Stockpile."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class BrollSuperDirector:
    """Listens to source audio and ranks dialogue moments worth visualizing."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or getattr(
            Config, "GEMINI_BROLL_SUPER_MODEL", "gemini-2.5-pro"
        )
        self.fallback_models = list(dict.fromkeys([
            self.model_name,
            *getattr(Config, "GEMINI_BROLL_SUPER_FALLBACK_MODELS", []),
            Config.GEMINI_MODEL,
            *Config.GEMINI_FALLBACK_MODELS,
        ]))
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("B-roll Super Director client init failed: %s", exc)

    async def analyze(
        self,
        source_video: str,
        transcript_segments: List[Dict[str, Any]],
        video_duration: float,
        output_dir: Path,
        niche: str = "generic",
        style: str = "clean_podcast",
        target_shots: Optional[int] = None,
    ) -> Dict[str, Any]:
        requested = target_shots or max(3, min(12, int(round(video_duration / 3.0))))
        output_dir.mkdir(parents=True, exist_ok=True)
        if not self.client:
            return {"model": "fallback", "moments": [], "reason": "GEMINI_API_KEY unavailable"}

        audio_path = output_dir / "broll_super_audio.mp3"
        uploaded = None
        try:
            await asyncio.to_thread(self._extract_audio, source_video, audio_path)
            uploaded = await asyncio.to_thread(self.client.files.upload, file=str(audio_path))
            prompt = self._build_prompt(
                self._format_transcript(transcript_segments),
                video_duration,
                niche,
                style,
                requested,
            )

            response_text = None
            used_model = self.model_name
            for model_name in self.fallback_models:
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=model_name,
                        contents=[uploaded, prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.15,
                            response_mime_type="application/json",
                            max_output_tokens=12000,
                        ),
                    )
                    if response and response.text:
                        response_text = response.text
                        used_model = model_name
                        break
                except Exception as exc:
                    logger.warning(
                        "B-roll Super Director model %s failed: %s",
                        model_name,
                        exc,
                    )

            if not response_text:
                return {
                    "model": used_model,
                    "moments": [],
                    "reason": "All super-model attempts failed",
                }

            analysis = self._parse_json(response_text)
            analysis["model"] = used_model
            analysis["moments"] = self._normalize_moments(
                analysis.get("moments", []),
                video_duration,
                max(requested * 2, requested),
            )
            analysis["selection_policy"] = (
                "tone_of_voice + dialogue_impact + visualizability + narrative_need"
            )
            return analysis
        except Exception as exc:
            logger.warning("B-roll Super Director analysis failed: %s", exc)
            return {"model": "fallback", "moments": [], "reason": str(exc)}
        finally:
            if uploaded is not None:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded.name)
                except Exception:
                    pass
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass

    def apply_to_plan(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        video_duration: float,
    ) -> Dict[str, Any]:
        """Retimes existing B-roll around the strongest emotional dialogue."""
        moments = [
            m for m in (analysis.get("moments") or [])
            if m.get("best_for_broll", True)
        ]
        if not moments:
            plan["broll_super_analysis"] = analysis
            return plan

        existing = list(plan.get("shots") or [])
        if not existing:
            existing = [{} for _ in range(min(8, len(moments)))]

        moments.sort(
            key=lambda m: (
                float(m.get("broll_priority", 0)),
                float(m.get("impact_score", 0)),
                float(m.get("visualizability", 0)),
            ),
            reverse=True,
        )

        selected: List[Dict[str, Any]] = []
        for moment in moments:
            start = float(moment["start"])
            if start < 0.8 and video_duration > 3:
                start = 0.8
            if any(abs(start - x["start"]) < 1.0 for x in selected):
                continue
            item = dict(moment)
            item["start"] = start
            selected.append(item)
            if len(selected) >= len(existing):
                break

        selected.sort(key=lambda m: float(m["start"]))
        merged: List[Dict[str, Any]] = []
        for idx, original in enumerate(existing):
            if idx >= len(selected):
                # Do not preserve low-value Director filler when the super model
                # explicitly found fewer strong visual opportunities.
                continue

            moment = selected[idx]
            shot = dict(original)
            start = float(moment["start"])
            duration = min(
                float(shot.get("duration", 2.0) or 2.0),
                float(moment.get("recommended_duration", 2.2) or 2.2),
                2.6,
            )
            duration = max(1.2, duration)
            end = min(video_duration, start + duration)
            if end - start < 1.0:
                continue

            shot.update({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "duration": round(end - start, 2),
                "dialogue_quote": moment.get("anchor_quote") or shot.get("dialogue_quote", ""),
                "emotional_core": moment.get("emotion") or shot.get("emotional_core", "context"),
                "emotion": moment.get("emotion", "neutral"),
                "sentiment": moment.get("sentiment", "neutral"),
                "tone_of_voice": moment.get("tone_of_voice", "neutral"),
                "tone_intensity": float(moment.get("tone_intensity", 0) or 0),
                "impact_score": float(moment.get("impact_score", 0) or 0),
                "visualizability": float(moment.get("visualizability", 0) or 0),
                "broll_priority": float(moment.get("broll_priority", 0) or 0),
                "visual_strategy": moment.get("visual_strategy", "literal contextual scene"),
                "avoid_visuals": moment.get("avoid_visuals", []),
                "broll_search_queries": moment.get("search_queries", [])[:6],
                "narrative_reason": moment.get(
                    "why_broll",
                    "High-impact dialogue with strong visual interpretation.",
                ),
            })

            if shot["broll_search_queries"]:
                shot["search_prompt"] = shot["broll_search_queries"][0]
                shot["micro_prompts"] = shot["broll_search_queries"][:5]
            merged.append(shot)

        merged.sort(key=lambda s: float(s.get("start_time", 0)))
        cleaned: List[Dict[str, Any]] = []
        last_end = 0.0
        for shot in merged:
            start = max(float(shot.get("start_time", 0)), last_end + 0.15)
            end = min(video_duration, float(shot.get("end_time", start + 1.2)))
            if end - start < 1.0:
                continue
            shot["start_time"] = round(start, 2)
            shot["end_time"] = round(end, 2)
            shot["duration"] = round(end - start, 2)
            cleaned.append(shot)
            last_end = end

        total = round(sum(float(s.get("duration", 0)) for s in cleaned), 2)
        plan["shots"] = cleaned
        plan["broll_shot_count"] = len(cleaned)
        plan["broll_coverage_seconds"] = total
        plan["broll_coverage_percentage"] = round(
            (total / max(video_duration, 0.001)) * 100,
            1,
        )
        plan["broll_super_analysis"] = analysis
        plan["broll_selection_model"] = analysis.get("model", self.model_name)
        plan["broll_selection_policy"] = "emotion-first"
        return plan

    @staticmethod
    def _extract_audio(source_video: str, output_path: Path):
        cmd = [
            "ffmpeg", "-y", "-i", source_video, "-vn",
            "-ac", "1", "-ar", "16000", "-b:a", "48k",
            "-map", "0:a:0?", "-f", "mp3", str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                result.stderr[-1200:] if result.stderr
                else "Audio extraction failed"
            )

    @staticmethod
    def _format_transcript(segments: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"[{float(seg.get('start', 0)):.2f}-{float(seg.get('end', 0)):.2f}] "
            f"{str(seg.get('text', '')).strip()}"
            for seg in segments
        )

    @staticmethod
    def _build_prompt(
        transcript_text: str,
        video_duration: float,
        niche: str,
        style: str,
        requested_shots: int,
    ) -> str:
        return f"""You are the B-ROLL SUPER DIRECTOR for an AI short-form editor.

LISTEN TO THE ATTACHED AUDIO. Do not treat the transcript as sufficient evidence.

Find the dialogue moments where B-roll adds the most emotional and narrative
value. Do not force B-roll onto every sentence.

Use BOTH:
1. WHAT is said: exact impactful dialogue and story meaning.
2. HOW it is said: tone, vocal intensity, pauses, acceleration, hesitation,
   confidence, disbelief, sarcasm, excitement, anger, fear, vulnerability,
   curiosity, humor, relief, sadness, reflection.
3. WHY it matters: reveal, claim, tension, conflict, punchline, consequence,
   realization, surprising fact, vivid story, decisive action, emotional turn.
4. WHETHER a concrete visual can communicate the idea better than text alone.

TONE-FIRST RULES:
- A quiet serious line can outrank a loud generic line.
- Listen for meaningful changes in delivery.
- Sarcasm should visualize the underlying meaning, not a literal keyword.
- Vulnerability should prefer intimate human situations.
- Anger/frustration should prefer human pressure, struggle, conflict, or consequence.
- Surprise/disbelief should prefer reactions, contrast, reveals, or unexpected situations.
- Excitement should prefer movement, achievement, celebration, launches, or visible action.
- Confidence/authority should prefer evidence, expertise, action, or status.
- Sadness/loss should prefer restrained contextual human visuals.

B-ROLL RULES:
- Never choose a sentence only because it contains a keyword.
- Prefer high-impact AND highly visualizable dialogue.
- Choose the MOST IMPACTFUL DIALOGUE for each visual opportunity.
- Do not repeat the same visual concept when another useful angle exists.
- Search queries must describe exactly what should be visible, not just the emotion.
- Use 3-6 concrete words per query and provide 2-4 visual angles.
- Never invent negative drama.
- Never use sports, basketball, streamers, memes, or generic podcast footage unless the dialogue genuinely calls for it.

TIMING:
- Anchor around the strongest phrase.
- Typical opportunity is 0.8-3.0 seconds around the anchor dialogue.
- B-roll may begin slightly before the key phrase for a natural cut.
- Avoid overlapping moments unless they are distinct visual beats.

RANK EACH MOMENT 0-100:
impact_score = importance of the dialogue to the story
visualizability = how strongly the idea can be shown
tone_intensity = strength/change in vocal delivery
broll_priority = final value of inserting B-roll

NICHE: {niche}
STYLE: {style}
VIDEO LENGTH: {video_duration:.2f}s
TARGET USEFUL MOMENTS: {requested_shots}

RETURN ONLY VALID JSON:
{{
  "emotional_arc": ["setup", "tension", "turn", "payoff"],
  "global_tone": "brief description",
  "moments": [
    {{
      "start": 12.4,
      "end": 15.1,
      "anchor_quote": "exact impactful dialogue",
      "emotion": "frustration",
      "sentiment": "negative",
      "tone_of_voice": "urgent",
      "tone_intensity": 87,
      "impact_score": 94,
      "visualizability": 96,
      "broll_priority": 95,
      "best_for_broll": true,
      "visual_strategy": "show the human consequence of the line",
      "search_queries": [
        "employee packing office belongings",
        "person leaving office with box",
        "worker packing desk items"
      ],
      "avoid_visuals": ["generic office exterior", "random business meeting"],
      "recommended_duration": 2.1,
      "why_broll": "high-impact dialogue with strong visual consequence and a vocal shift"
    }}
  ]
}}

TRANSCRIPT CONTEXT:
{transcript_text}
"""

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        fence = chr(96) * 3
        if text.startswith(fence):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith(fence):
                text = text[:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise

    @staticmethod
    def _normalize_moments(
        moments: List[Dict[str, Any]],
        video_duration: float,
        max_items: int,
    ) -> List[Dict[str, Any]]:
        cleaned = []
        for raw in moments or []:
            try:
                start = max(
                    0.0,
                    min(float(raw.get("start", 0)), video_duration),
                )
                end = min(
                    video_duration,
                    max(
                        start + 0.5,
                        float(raw.get("end", start + 1.5)),
                    ),
                )
            except (TypeError, ValueError):
                continue

            item = dict(raw)
            item["start"] = round(start, 3)
            item["end"] = round(end, 3)
            for key in (
                "impact_score",
                "visualizability",
                "tone_intensity",
                "broll_priority",
            ):
                item[key] = max(
                    0.0,
                    min(float(item.get(key, 0) or 0), 100.0),
                )

            # Recompute the final B-roll priority from the model's evidence.
            # This prevents a single arbitrary model score from dominating:
            # dialogue impact > visualizability > tone intensity.
            evidence_priority = (
                item["impact_score"] * 0.48
                + item["visualizability"] * 0.32
                + item["tone_intensity"] * 0.12
            )
            model_priority = item["broll_priority"]
            item["broll_priority"] = round(
                max(evidence_priority, model_priority * 0.85),
                2,
            )

            item["search_queries"] = [
                str(q).strip()
                for q in (item.get("search_queries") or [])
                if str(q).strip()
            ][:6]
            item["avoid_visuals"] = [
                str(v).strip()
                for v in (item.get("avoid_visuals") or [])
                if str(v).strip()
            ][:6]
            item["best_for_broll"] = bool(item.get("best_for_broll", True))
            cleaned.append(item)

        cleaned.sort(
            key=lambda x: (
                x["broll_priority"],
                x["impact_score"],
                x["visualizability"],
            ),
            reverse=True,
        )
        return cleaned[:max_items]


broll_super_director = BrollSuperDirector()
