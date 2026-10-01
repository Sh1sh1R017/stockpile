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
                except Exception as exc:
                    logger.debug("Suppressed optional failure: %s", exc)
            try:
                audio_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.debug("Suppressed optional failure: %s", exc)

    def apply_to_plan(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        video_duration: float,
    ) -> Dict[str, Any]:
        """Enrich existing B-roll decisions without creating or retiming shots.

        B-roll timing and eligibility belong to the canonical editorial planner.
        The Super Director may add contextual search/semantic metadata to an
        existing shot, but it cannot create placeholders, change intervals, or
        chase a coverage percentage.
        """
        moments = [
            m for m in (analysis.get("moments") or [])
            if m.get("best_for_broll", True)
        ]
        existing = [dict(shot) for shot in (plan.get("shots") or [])]
        if not existing or not moments:
            plan["broll_super_analysis"] = analysis
            return plan

        def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
            return max(0.0, min(a_end, b_end) - max(a_start, b_start))

        used = set()
        enriched: List[Dict[str, Any]] = []
        for shot in existing:
            start = float(shot.get("start_time", 0.0) or 0.0)
            end = float(shot.get("end_time", start) or start)

            candidates = []
            for index, moment in enumerate(moments):
                if index in used:
                    continue
                try:
                    m_start = float(moment.get("start", 0.0) or 0.0)
                    m_end = float(moment.get("end", m_start) or m_start)
                except (TypeError, ValueError):
                    continue
                candidates.append((
                    overlap(start, end, m_start, m_end),
                    -abs(start - m_start),
                    float(moment.get("broll_priority", 0) or 0),
                    index,
                    moment,
                ))

            if candidates:
                _, _, _, index, moment = max(candidates)
                used.add(index)
                shot["dialogue_quote"] = moment.get("anchor_quote") or shot.get("dialogue_quote", "")
                shot["emotional_core"] = moment.get("emotion") or shot.get("emotional_core", "context")
                shot["emotion"] = moment.get("emotion", shot.get("emotion", "neutral"))
                shot["sentiment"] = moment.get("sentiment", shot.get("sentiment", "neutral"))
                shot["tone_of_voice"] = moment.get("tone_of_voice", shot.get("tone_of_voice", "neutral"))
                shot["tone_intensity"] = float(moment.get("tone_intensity", shot.get("tone_intensity", 0)) or 0)
                shot["impact_score"] = float(moment.get("impact_score", shot.get("impact_score", 0)) or 0)
                shot["visualizability"] = float(moment.get("visualizability", shot.get("visualizability", 0)) or 0)
                shot["broll_priority"] = float(moment.get("broll_priority", shot.get("broll_priority", 0)) or 0)
                shot["visual_strategy"] = moment.get("visual_strategy", shot.get("visual_strategy", "literal contextual scene"))
                shot["avoid_visuals"] = list(moment.get("avoid_visuals") or shot.get("avoid_visuals") or [])[:6]
                queries = [
                    str(q).strip()
                    for q in (moment.get("search_queries") or [])
                    if str(q).strip()
                ][:6]
                if queries:
                    shot["broll_search_queries"] = queries
                    shot["search_prompt"] = queries[0]
                    shot["micro_prompts"] = queries[:5]
                shot["super_director_moment_id"] = moment.get("moment_id") or f"super_{index}"

            # Preserve the canonical approved interval exactly.
            enriched.append(shot)

        plan["shots"] = enriched
        plan["broll_shot_count"] = len(enriched)
        total = sum(
            max(0.0, float(shot.get("end_time", 0)) - float(shot.get("start_time", 0)))
            for shot in enriched
            if shot.get("asset_path")
        )
        plan["broll_coverage_seconds"] = round(total, 2)
        plan["broll_coverage_percentage"] = round(
            (total / max(float(video_duration), 0.001)) * 100.0,
            1,
        )
        plan["broll_super_analysis"] = analysis
        plan["broll_selection_model"] = analysis.get("model", self.model_name)
        plan["broll_selection_policy"] = "metadata-enrichment-only"
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
        reference_mode = str(style).strip().lower() in {
            "cinematic social editorial",
            "cinematic_social_editorial",
            "cinematic editorial",
        }
        reference_rules = ""
        if reference_mode:
            reference_rules = """
REFERENCE EDITING MODE:
- Use B-roll only where the existing editorial plan already identifies a strong,
  truthful visual opportunity.
- Coverage is telemetry, not a quota.
- Do not invent timing roles or duration targets downstream.
- Preserve the canonical A-roll/B-roll interval decisions made by the editor.
"""

        return f"""You are the B-ROLL SUPER DIRECTOR for an AI short-form editor.

LISTEN TO THE ATTACHED AUDIO. Do not treat the transcript as sufficient evidence.
{reference_rules}

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
- Recommend visual context and searchable subjects, but never dictate approved timing
  or extend an existing interval.
- Timing is owned by the canonical editorial decision; use the supplied moment only
  as semantic context.
- Avoid redundant concepts, not close timestamps.

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
      "cadence_role": "micro",
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
