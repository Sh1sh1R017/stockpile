"""AI Director service analyzing narrative beats and generating visual edit plans."""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)

_UNSET_API_KEY = object()


def clean_json_string(text: str) -> str:
    """Clean markdown markers and trailing noise from model responses."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class Director:
    """Creative Director engine using Gemini to plan visual B-roll sequences."""

    def __init__(self, api_key: Optional[str] = _UNSET_API_KEY, model_name: Optional[str] = None):
        # Omitted api_key means "use configured key"; explicit None means offline.
        self.api_key = Config.GEMINI_API_KEY if api_key is _UNSET_API_KEY else api_key
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def create_edit_plan(
        self,
        full_transcript: str,
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign_id: str = "default",
        curated_moment_id: Optional[str] = None,
        custom_hook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete Visual Edit Plan respecting campaign-specific constraints and visual pacing."""
        from ai_broll_autopilot.campaigns import campaign_registry
        campaign = campaign_registry.get_campaign(campaign_id)

        logger.info(
            f"AI Director analyzing {len(segments)} segments for video length {video_duration:.1f}s "
            f"under campaign '{campaign.id}' (relevance-first visual planning)"
        )

        # Format segments for Director prompt
        formatted_segments = "\n".join([
            f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}"
            for seg in segments
        ])

        from ai_broll_autopilot.services.learning import feedback_engine
        learned_rules = feedback_engine.get_learned_instructions(full_transcript)

        chosen_hook = custom_hook

        # Resolve active niche profile
        from ai_broll_autopilot.niches import niche_registry
        niche = None
        if getattr(campaign, "niche_id", None) and campaign.niche_id != "generic":
            niche = niche_registry.get_profile(campaign.niche_id)
        if not niche or niche.id == "generic":
            from ai_broll_autopilot.services.niche_detector import niche_detector
            niche_res = niche_detector._detect_heuristic(full_transcript)
            # Require high confidence (>= 0.75) and multiple distinct keywords to override generic default
            if (
                niche_res
                and niche_res.niche_id != "generic"
                and niche_res.confidence >= 0.75
                and len(niche_res.detected_keywords) >= 3
            ):
                niche = niche_registry.get_profile(niche_res.niche_id)
            else:
                niche = niche_registry.get_profile("generic")

        # Resolve the visual treatment independently from the subtitle preset.
        # An explicit campaign editing_style is an editorial contract and must
        # override the niche's default style.
        from ai_broll_autopilot.services.niche_detector import NICHE_TO_STYLE_MAP
        from ai_broll_autopilot.styles import style_registry
        campaign_style_id = str(getattr(campaign, "editing_style", "") or "").strip()
        style_id = (
            campaign_style_id
            or NICHE_TO_STYLE_MAP.get(
                niche.id if niche else "generic",
                "cinematic_social_editorial",
            )
            or "cinematic_social_editorial"
        )
        style_profile = style_registry.get_style(style_id)

        # Relevance-first planning: visual coverage is telemetry, not a quota.
        # Give the Director a bounded opportunity budget without requiring all slots
        # to be used. Each slot must still earn its place semantically.
        reference_mode = bool(getattr(style_profile, "reference_style", False))
        max_visual_slots = (
            max(2, min(14, int(video_duration / (1.45 if reference_mode else 2.0))))
            if video_duration > 0
            else 0
        )
        max_visual_slots = min(max_visual_slots, len(segments)) if segments else 0

        # Partition video duration into 3 narrative acts for uniform timeline distribution
        t_act1 = round(video_duration * 0.33, 1)
        t_act2 = round(video_duration * 0.66, 1)
        quota_act1 = max(0, max_visual_slots // 3)
        quota_act2 = max(0, max_visual_slots // 3)
        quota_act3 = max(0, max_visual_slots - quota_act1 - quota_act2)

        # Segment grouping by act for explicit LLM awareness
        act1_segs = []
        act2_segs = []
        act3_segs = []
        for s in segments:
            st = float(s.get("start", 0.0))
            if st < t_act1:
                act1_segs.append(s)
            elif st < t_act2:
                act2_segs.append(s)
            else:
                act3_segs.append(s)

        act1_txt = "\n".join(f"[{s.get('start', 0.0):.2f}s - {s.get('end', 0.0):.2f}s]: {s.get('text', '')}" for s in act1_segs) or "No dialogue in this section."
        act2_txt = "\n".join(f"[{s.get('start', 0.0):.2f}s - {s.get('end', 0.0):.2f}s]: {s.get('text', '')}" for s in act2_segs) or "No dialogue in this section."
        act3_txt = "\n".join(f"[{s.get('start', 0.0):.2f}s - {s.get('end', 0.0):.2f}s]: {s.get('text', '')}" for s in act3_segs) or "No dialogue in this section."
        allow_memes = bool(campaign.allow_ai_broll and getattr(niche.editing, "meme_cutaways", False))

        # Match curated moment if specified (works for any campaign with curated_moments)
        matched_moment = None
        if curated_moment_id and hasattr(campaign, "curated_moments"):
            for m in campaign.curated_moments:
                if m.moment_id.lower() == curated_moment_id.lower():
                    matched_moment = m
                    break

        chosen_hook = custom_hook or (matched_moment.screen_hook if matched_moment else None)

        if niche and niche.id != "generic":
            niche_desc = f"{niche.name} ({niche.description})"
            niche_keywords_hint = ", ".join(niche.visual_keywords[:8])
        else:
            niche_desc = "General Video & Podcast (General dialogue, stories, real-world events, discussions)"
            niche_keywords_hint = "real-world context matching spoken dialogue literally (people, places, objects, actions)"

        meme_instructions = ""
        if allow_memes:
            meme_instructions = """
4. CONTEXTUAL MEME CUTAWAYS (OPTIONAL FOR HIGH-ENERGY COMEDY / STREAMER MOMENTS):
   - You may designate up to 1-2 shots as "style": "meme" if a wild claim, rage outburst, or high-energy reaction occurs.
   - For all other shots, use real stock footage ("style": "stockpile")."""

        director_prompt = f"""You are the Master AI Video Director for high-retention viral short-form videos (TikTok, Reels, YouTube Shorts).
CAMPAIGN: {campaign.name}
CONTENT DOMAIN: {niche_desc}
RELEVANT VISUAL THEMES: {niche_keywords_hint}

MANDATORY DIRECTING OBJECTIVES:
1. RHYTHMIC EDITING, NOT A MECHANICAL GRID:
   - Total Video Duration: {video_duration:.2f} seconds.
   - B-ROLL COVERAGE IS NOT A TARGET. There is no required percentage or minimum number of cutaways.
   - You may use up to {max_visual_slots} contextual cutaways only when each one materially reinforces the spoken idea.
   - Do NOT fill unused visual slots and do NOT force equal spacing.
   - Build the sequence around the speech: setup -> literal context -> reaction/consequence -> narrative hold -> payoff.
   - REFERENCE CADENCE:
     • MICRO burst: 0.45-0.85s. Use for a short phrase, list, escalation, object swap, reaction, or rapid visual punctuation.
     • STANDARD hold: 0.90-2.20s. Use for the main contextual idea.
     • HERO moments are still short: use the same 0.65-1.8s render contract; create emphasis through a stronger visual, not a long hold.
     • A reference-style short should usually contain 2-4 micro/standard visual changes inside a larger semantic beat, then return to speaker footage.
   - Cut on meaning, phrase boundaries, visual reveals, reaction changes, or a change in visual metaphor — NEVER on a metronome.
   - Keep adjacent micro shots closely related to the same spoken idea; use them as a visual montage, not unrelated stock spam.
   - The first 1-2 seconds may be B-roll immediately when the opening words have a concrete visual metaphor.
   - Keep the speaker visible only where it strengthens authenticity, timing, or an intentional return beat.
   - Use restrained punch-ins only; NEVER solve pacing by zooming the same source repeatedly.
   - Use a maximum of 1-2 abstract/title-card visual moments for a short unless the story explicitly becomes conceptual.
   - For REFERENCE-STYLE TEXT, output up to 4 semantic emphasis callouts: a meaningful noun/phrase such as a concept, location, value, person, or consequence. These are editorial typography, not duplicate subtitles.
   - Do not fire an SFX on every cut. Use sound accents for meaningful reveals/typographic entrances only.

2. REFERENCE VISUAL LANGUAGE:
   - {style_profile.name}: {style_profile.description}
   - Reference-style settings: reference_style={getattr(style_profile, "reference_style", False)}, target_broll_ratio={getattr(style_profile, "broll_target_ratio", None)}, hero_broll_max_duration={getattr(style_profile, "hero_broll_max_duration", 2.6)}
   - {chr(10).join(f"- {g}" for g in style_profile.editorial_guidelines)}

3. ACCURATE CONTEXTUAL MATCHING (CRITICAL):
   - Visuals MUST directly amplify the EXACT topic and words being spoken at each timestamp!
   - Select real, photogenic visual metaphors directly tied to the spoken words.
   - ABSOLUTE PROHIBITION ON UNRELATED SPORTS / BASKETBALL:
     • DO NOT default to sports, basketball, courts, athletes, hoops, or jerseys unless the dialogue explicitly talks about sports or basketball!
     • If the dialogue is about military, guns, danger, or borders: show dramatic real-world security, checkpoints, documents, or conflict scenes.
     • If the dialogue is about work, business, science, legal, family, or travel: show those exact real-world scenes.
     • NEVER substitute basketball or athletic scenes for unrelated narrative themes!
   - STRICTLY FORBIDDEN:
     • DO NOT invent negative or irrelevant drama unless the speaker explicitly describes it!
     • All visual shots must have "style": "stockpile" (real-world stock footage) unless memes are allowed.
{meme_instructions}

3. OPTIMIZED STOCK FOOTAGE SEARCH PROMPTS — RETRIEVAL, NOT VAGUE CONCEPTS:
   - "search_prompt" MUST describe a concrete, observable shot: subject + physical action + relevant object/context.
   - "micro_prompts" MUST be 3-5 alternate retrieval queries for the SAME visual event, not generic emotion synonyms.
   - Use 4-8 natural stock-search words. Prefer "person reading search results laptop" over "person feeling insecure".
   - Every shot must be specific enough that a human editor could visualize the exact 1.5-2.4 second clip before searching.
   - BAD: "concerned person laptop", "show embarrassment", "human consequence", "frustrated professional".
   - GOOD: "young adult reading search results laptop", "close up typing name search bar", "person closes laptop embarrassed".
   - For digital actions, show the digital action literally. For emotional consequences, show an observable physical reaction.
   - Do not invent drama, props, locations, brands, or events not supported by the dialogue.

VIDEO DURATION: {video_duration:.2f} seconds
TIMESTAMPED TRANSCRIPT (DIVIDED INTO 3 ACTS):
=== ACT 1 (HOOK & SETUP: 0.0s - {t_act1:.1f}s) — Optional context window ===
{act1_txt}

=== ACT 2 (BODY & DEVELOPMENT: {t_act1:.1f}s - {t_act2:.1f}s) — Optional context window ===
{act2_txt}

=== ACT 3 (CLIMAX & CONCLUSION: {t_act2:.1f}s - {video_duration:.1f}s) — Optional context window ===
{act3_txt}

{learned_rules}

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "summary": "Short 1-sentence narrative arc summary",
  "hook_text": "{chosen_hook or 'BOLD PUNCHY ALL-CAPS HOOK FROM TRANSCRIPT'}",
  "shots": [
    {{
      "shot_id": "broll_1",
      "start_time": 1.2,
      "end_time": 3.2,
      "duration": 2.0,
      "cadence_role": "micro|standard|hero",
      "style": "stockpile",
      "dialogue_quote": "Exact spoken line from transcript",
      "emotional_core": "Underlying human meaning, not the visual itself",
      "visceral_human_metaphor": "Concrete observable scene; never an abstract emotion",
      "visual_subject": "Specific person/object being shown",
      "visual_action": "Specific physical action visible on camera",
      "visual_setting": "Specific supported environment",
      "key_object": "Object or interface that anchors the scene",
      "shot_composition": "Specific wide/medium/close-up/over-shoulder framing",
      "micro_prompts": [
        "literal stock-search query 1",
        "literal stock-search query 2",
        "literal stock-search query 3"
      ],
      "search_prompt": "Best concrete stock-search query",
      "overlay_type": "cutaway",
      "narrative_reason": "Why this exact visible action communicates the spoken line"
    }}
  ],
  "text_emphasis_graphics": [
    {{
      "graphic_id": "emphasis_1",
      "primary_text": "ONE",
      "secondary_text": "",
      "start_time": 1.0,
      "duration": 1.4,
      "position": {{ "x_percent": 50, "y_percent": 58 }},
      "graphic_type": "semantic_callout",
      "animation_in": "pop_spring",
      "accent_color": "{style_profile.highlight_color}",
      "reason": "Why this phrase deserves visual emphasis"
    }}
  ]
}}"""

        models_to_try = [self.model_name] + [m for m in Config.GEMINI_FALLBACK_MODELS if m != self.model_name]
        plan_data = None

        for model_cand in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_cand,
                    contents=director_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                        http_options=types.HttpOptions(
                            retry_options=types.HttpRetryOptions(attempts=1),
                            timeout=15000
                        ),
                    ),
                )
                raw_text = clean_json_string(response.text or "{}")
                plan_data = json.loads(raw_text)
                min_shots = 1 if campaign.max_broll_ratio <= 0.35 else 2
                if plan_data and "shots" in plan_data and len(plan_data["shots"]) >= min_shots:
                    break
            except Exception as model_err:
                logger.warning(f"AI Director model {model_cand} failed: {model_err}. Trying next fallback...")
                continue

        if not plan_data or "shots" not in plan_data or not plan_data["shots"]:
            logger.warning(f"AI Director failed to produce valid plan for '{campaign.id}'. Falling back to heuristic plan.")
            return self._create_heuristic_plan(
                segments, video_duration, campaign=campaign, custom_hook=chosen_hook or custom_hook, curated_moment_id=curated_moment_id
            )

        try:
            # Validate and clamp shot timestamps to video bounds and campaign constraints
            clean_shots = []
            last_end = 0.0
            reference_editing = bool(getattr(style_profile, "reference_style", False))
            configured_max_dur = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", Config.MAX_CLIP_DURATION_SECONDS))
            max_dur = configured_max_dur

            for shot in plan_data.get("shots", []):
                # Strictly filter out any A-roll / speaker shots
                shot_id_str = str(shot.get("shot_id", "")).lower()
                ov_type = str(shot.get("overlay_type", "")).lower()
                if "aroll" in shot_id_str or ov_type == "speaker":
                    continue

                start = max(0.0, float(shot.get("start_time", 0.0)))
                reference_gap = 0.15 if reference_editing else 0.4
                if start < last_end + reference_gap:
                    start = last_end + reference_gap

                if start >= video_duration - (0.2 if reference_editing else 0.8):
                    break

                style = shot.get("style", "stockpile").lower()
                if not campaign.allow_ai_broll or style not in ("stockpile", "collage", "meme"):
                    style = "stockpile"

                # Reference edits intentionally use three timing scales so a
                # semantic burst can contain sub-second visual punctuation without
                # turning the entire short into a rapid-fire montage.
                requested_role = str(
                    shot.get("cadence_role", shot.get("visual_role", ""))
                ).lower().strip()
                requested_duration = float(shot.get("duration", 1.5) or 1.5)
                if reference_editing:
                    if requested_role not in {"micro", "standard", "hero"}:
                        requested_role = (
                            "hero"
                            if requested_duration >= float(getattr(style_profile, "hero_broll_min_duration", 3.0))
                            else "micro"
                            if requested_duration <= float(getattr(style_profile, "micro_broll_max_duration", 0.85))
                            else "standard"
                        )
                    min_clip = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
                    max_clip = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8))
                else:
                    requested_role = "standard"
                    min_clip = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
                    max_clip = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8))
                max_clip = min(max_clip, max_dur)
                duration = min(max_clip, max(min_clip, requested_duration))
                if style == "meme":
                    duration = min(
                        float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8)),
                        max(float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65)), duration),
                    )
                end = min(video_duration, start + duration)
                duration = round(end - start, 2)

                min_valid_duration = (
                    float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
                    if reference_editing and requested_role == "micro"
                    else float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65)) if reference_editing
                    else 1.0
                )
                if duration < min_valid_duration:
                    continue

                # Extract and clean micro_prompts (3-5 rapid cuts)
                raw_micro = shot.get("micro_prompts", [])
                clean_micro = []
                if isinstance(raw_micro, list):
                    for mp in raw_micro:
                        if isinstance(mp, str) and mp.strip():
                            cleaned_mp = mp.strip()
                            for gw in ["streamer", "twitch", "gameplay", "walkthrough"]:
                                cleaned_mp = re.sub(rf"\b{gw}\b", "", cleaned_mp, flags=re.IGNORECASE).strip()
                            if cleaned_mp:
                                clean_micro.append(cleaned_mp)

                base_prompt = shot.get("search_prompt", "focused person working")
                if not clean_micro:
                    clean_micro = [
                        base_prompt,
                        f"{base_prompt} close up",
                        f"{base_prompt} hands",
                        f"{base_prompt} action",
                    ]

                shot_entry = {
                    "shot_id": f"broll_{len(clean_shots)+1}",
                    "start_time": round(start, 2),
                    "end_time": round(end, 2),
                    "duration": duration,
                    "style": style,
                    "dialogue_quote": shot.get("dialogue_quote", ""),
                    "emotional_core": shot.get("emotional_core", "Contextual Focus"),
                    "visceral_human_metaphor": shot.get("visceral_human_metaphor", "Topic illustration"),
                    "micro_prompts": clean_micro[:5],
                    "search_prompt": base_prompt,
                    "overlay_type": "cutaway",
                    "cadence_role": requested_role,
                    "narrative_reason": shot.get("narrative_reason", "Narrative reinforcement"),
                }
                if style == "meme":
                    shot_entry["meme_template"] = shot.get("meme_template", "stepped_in_shit")
                    shot_entry["meme_captions"] = shot.get("meme_captions", {})

                clean_shots.append(shot_entry)
                last_end = end

            # Meme assignment is explicitly disabled for the reference treatment.
            if campaign.allow_ai_broll and allow_memes and not reference_editing:
                from ai_broll_autopilot.services.meme_engine import MemeEngine
                if clean_shots:
                    clean_shots[0]["style"] = "meme"
                    if clean_shots[0].get("start_time", 0.0) > 2.0:
                        clean_shots[0]["start_time"] = 1.2
                    clean_shots[0]["duration"] = min(2.2, max(1.5, float(clean_shots[0].get("duration", 2.0))))
                    clean_shots[0]["end_time"] = round(clean_shots[0]["start_time"] + clean_shots[0]["duration"], 2)

                meme_shots = [s for s in clean_shots if s.get("style") == "meme"]
                target_meme_count = 2 if len(clean_shots) >= 4 and video_duration >= 15.0 else 1

                while len(meme_shots) < target_meme_count and clean_shots:
                    cand = None
                    for idx in [2, 1, 3]:
                        if idx < len(clean_shots) and clean_shots[idx] not in meme_shots:
                            cand = clean_shots[idx]
                            break
                    if not cand:
                        break
                    cand["style"] = "meme"
                    meme_shots.append(cand)

                for ms in meme_shots:
                    caps = ms.get("meme_captions", {})
                    is_generic = False
                    if caps:
                        c_str = str(caps).lower()
                        if any(g in c_str for g in ("high retention", "ishowspeed moment", "caseoh rage", "zoom interview", "what people say", "bad opinion")):
                            is_generic = True
                    if not caps or is_generic or not ms.get("meme_template"):
                        ms = MemeEngine.generate_unique_contextual_meme(ms, full_transcript, client=self.client)
                        logger.info(f"AI Director autonomous meme cutaway generated on [{ms['shot_id']}] ({ms.get('meme_template')}): {ms.get('meme_captions')}")

            # Audit and fill timeline gaps across the ENTIRE video (ensures uniform coverage)
            clean_shots, coverage_pct = self._audit_and_fill_timeline_distribution(
                clean_shots=clean_shots,
                segments=segments,
                video_duration=video_duration,
                campaign=campaign,
                niche=niche,
            )
            total_broll_time = round(sum(s["duration"] for s in clean_shots), 2)

            # Normalize semantic callouts into deliberate editorial graphics.
            # These are separate from word-by-word captions and are capped so the
            # reference treatment never becomes an always-on text wall.
            emphasis_graphics = plan_data.get("text_emphasis_graphics", [])
            if reference_editing:
                normalized_graphics = []
                seen_graphic_text = set()
                max_graphics = int(getattr(style_profile, "semantic_callout_max", 4))
                min_graphic_duration = float(
                    getattr(style_profile, "semantic_callout_min_duration", 0.7)
                )
                max_graphic_duration = float(
                    getattr(style_profile, "semantic_callout_max_duration", 2.8)
                )
                for graphic in emphasis_graphics if isinstance(emphasis_graphics, list) else []:
                    if len(normalized_graphics) >= max_graphics or not isinstance(graphic, dict):
                        break
                    primary = str(
                        graphic.get("primary_text")
                        or graphic.get("text")
                        or ""
                    ).strip()
                    if not primary:
                        continue
                    normalized_key = re.sub(r"\s+", " ", primary.lower())
                    if normalized_key in seen_graphic_text:
                        continue
                    # Semantic callouts should be compact; long prose remains in captions.
                    if len(primary.split()) > 6:
                        continue

                    try:
                        graph_start = max(0.0, float(graphic.get("start_time", 0.0)))
                        graph_duration = max(
                            min_graphic_duration,
                            min(
                                max_graphic_duration,
                                float(graphic.get("duration", 1.2) or 1.2),
                            ),
                        )
                    except (TypeError, ValueError):
                        continue
                    if graph_start >= video_duration:
                        continue
                    graph_duration = min(graph_duration, video_duration - graph_start)
                    if graph_duration < min_graphic_duration:
                        continue

                    normalized = {
                        "graphic_id": str(
                            graphic.get(
                                "graphic_id",
                                f"semantic_{len(normalized_graphics)+1}",
                            )
                        ),
                        "primary_text": primary,
                        "secondary_text": str(graphic.get("secondary_text", "") or "").strip(),
                        "start_time": round(graph_start, 2),
                        "duration": round(graph_duration, 2),
                        "position": graphic.get(
                            "position",
                            {"x_percent": 50, "y_percent": getattr(style_profile, "caption_y_percent", 58.0)},
                        ),
                        "graphic_type": "semantic_callout",
                        "animation_in": graphic.get("animation_in", "pop_spring"),
                        "accent_color": graphic.get("accent_color", style_profile.highlight_color),
                        "reason": graphic.get(
                            "reason",
                            "Semantic phrase deserves dedicated visual emphasis.",
                        ),
                    }
                    normalized_graphics.append(normalized)
                    seen_graphic_text.add(normalized_key)
                emphasis_graphics = normalized_graphics
            else:
                emphasis_graphics = emphasis_graphics if isinstance(emphasis_graphics, list) else []

            plan_result = {
                "total_duration": video_duration,
                "broll_shot_count": len(clean_shots),
                "broll_coverage_seconds": round(total_broll_time, 2),
                "broll_coverage_percentage": coverage_pct,
                "summary": plan_data.get("summary", f"{campaign.name} Contextual Edit Plan"),
                "hook_text": chosen_hook or plan_data.get("hook_text"),
                "campaign_id": campaign.id,
                "niche": niche.to_dict() if niche and hasattr(niche, "to_dict") else {"id": "generic", "name": "General Video & Podcast"},
                "style": style_profile.to_dict(),
                "editing_style": style_profile.id,
                "reference_editing": bool(getattr(style_profile, "reference_style", False)),
                "style_guidelines": list(getattr(style_profile, "editorial_guidelines", [])),
                "shots": clean_shots,
                "text_emphasis_graphics": emphasis_graphics,
            }

            logger.info(f"AI Director planned {len(clean_shots)} B-roll cutaways covering {total_broll_time:.1f}s ({coverage_pct}% of {video_duration:.1f}s)")
            return plan_result

        except Exception as e:
            logger.error(f"AI Director planning post-processing failed: {e}", exc_info=True)
            return self._create_heuristic_plan(
                segments, video_duration, campaign=campaign, custom_hook=chosen_hook or custom_hook, curated_moment_id=curated_moment_id
            )

    def _create_heuristic_plan(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign: Optional[Any] = None,
        custom_hook: Optional[str] = None,
        curated_moment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deterministic fallback edit plan ensuring campaign constraints and contextual keywords."""
        shots = []
        style_id = str(((campaign.__dict__ if campaign else {}) or {}).get("editing_style") or "")
        from ai_broll_autopilot.styles import style_registry
        style_profile = style_registry.get_style(style_id) if style_id else None
        style_ratio = getattr(style_profile, "broll_target_ratio", None) if style_profile else None
        target_ratio = (
            float(style_ratio)
            if style_ratio is not None
            else (campaign.max_broll_ratio if campaign else Config.TARGET_BROLL_RATIO)
        )
        target_broll_dur = video_duration * target_ratio
        shot_dur = 2.0
        is_low_broll = campaign and campaign.max_broll_ratio <= 0.35
        num_shots = max(1, min(2, int(round(target_broll_dur / shot_dur)))) if is_low_broll else max(3, int(round(target_broll_dur / shot_dur)))

        # Distribute shots across available segments
        step = max(1, len(segments) // (num_shots + 1)) if segments else 1
        chosen_indices = [min(len(segments) - 1, (i + 1) * step) for i in range(num_shots)] if segments else []
        chosen_indices = sorted(list(set(chosen_indices)))

        last_end = 0.8  # leave 0.8s speaker hook

        for idx in chosen_indices:
            seg = segments[idx]
            start = max(last_end + 0.4, seg["start"])
            if start >= video_duration - 1.2:
                break

            dur = min(2.4, max(1.4, seg.get("duration", 2.0)))
            end = min(video_duration, start + dur)
            dur = round(end - start, 2)
            seg_text = seg.get("text", "").lower()

            # Contextual keyword detection
            if any(w in seg_text for w in ["focus", "disciplin", "work", "habit", "lesson"]):
                search_prompt = "focused person writing desk"
                emotional_core = "Deep Focus and Discipline"
            elif any(w in seg_text for w in ["win", "winner", "success", "goal", "champion"]):
                search_prompt = "runner winning finish line"
                emotional_core = "Triumph and Victory"
            elif any(w in seg_text for w in ["lose", "loser", "distract", "phone"]):
                search_prompt = "person scrolling smartphone couch"
                emotional_core = "Distraction and Unfocused Routine"
            elif any(w in seg_text for w in ["dad", "father", "mother", "parent", "mentor"]):
                search_prompt = "father teaching son"
                emotional_core = "Mentorship and Wisdom"
            elif any(w in seg_text for w in ["clipboard", "office", "desk", "front"]):
                search_prompt = "businessman clipboard checklist"
                emotional_core = "Organization and Routine"
            else:
                words = [w for w in re.findall(r"\b[a-z0-9]+\b", seg_text) if len(w) > 3 and w not in ["that", "this", "what", "with", "have"]]
                search_prompt = " ".join(words[:2]) if words else "business success"
                emotional_core = "Contextual Narrative"

            micro_prompts = [
                search_prompt,
                f"{search_prompt} close up",
                f"{search_prompt} detail",
                f"{search_prompt} action",
            ]

            # In heuristic plan, memes only if campaign allows AI/meme B-roll and niche enables memes
            allow_heuristic_memes = bool(campaign and campaign.allow_ai_broll)
            if campaign and getattr(campaign, "niche_id", None):
                from ai_broll_autopilot.niches import niche_registry
                n = niche_registry.get_profile(campaign.niche_id)
                if not getattr(n.editing, "meme_cutaways", False):
                    allow_heuristic_memes = False
            else:
                allow_heuristic_memes = False

            is_meme = allow_heuristic_memes and ((len(shots) == 0) or (len(shots) == 2 and video_duration >= 15.0))
            if is_meme and len(shots) == 0:
                start = 1.2
                dur = min(2.2, max(1.5, dur))
                end = round(start + dur, 2)
            shot_style = "meme" if is_meme else "stockpile"

            shot_data = {
                "shot_id": f"broll_{len(shots)+1}",
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "duration": dur,
                "style": shot_style,
                "dialogue_quote": seg.get("text", ""),
                "emotional_core": emotional_core,
                "visceral_human_metaphor": f"Visualizing {search_prompt}",
                "micro_prompts": micro_prompts,
                "search_prompt": search_prompt,
                "overlay_type": "cutaway",
                "narrative_reason": "Compulsory viral hook meme in first 5s" if is_meme else f"Contextual illustration of: {seg_text[:40]}",
            }
            if is_meme:
                from ai_broll_autopilot.services.meme_engine import MemeEngine
                full_t = " ".join(s.get("text", "") for s in segments)
                shot_data = MemeEngine.generate_unique_contextual_meme(shot_data, full_t, client=self.client)

            shots.append(shot_data)
        # Audit and fill timeline gaps across the ENTIRE video (ensures uniform coverage)
        shots, coverage_pct = self._audit_and_fill_timeline_distribution(
            clean_shots=shots,
            segments=segments,
            video_duration=video_duration,
            campaign=campaign,
            niche=None,
        )
        total_broll = round(sum(s["duration"] for s in shots), 2)

        emphasis_graphics = []

        resolved_hook = custom_hook
        if not resolved_hook and campaign and campaign.curated_moments:
            if curated_moment_id:
                for m in campaign.curated_moments:
                    if m.moment_id.lower() == curated_moment_id.lower():
                        resolved_hook = m.screen_hook
                        break
            if not resolved_hook and len(campaign.curated_moments) > 0:
                resolved_hook = campaign.curated_moments[0].screen_hook
        if not resolved_hook:
            if segments:
                first_text = segments[0].get("text", "").strip()
                resolved_hook = first_text[:45].upper() if first_text else "KEY TAKEAWAY"
            else:
                resolved_hook = "KEY TAKEAWAY"

        style_payload = style_profile.to_dict() if style_profile else {}
        return {
            "total_duration": video_duration,
            "broll_shot_count": len(shots),
            "broll_coverage_seconds": round(total_broll, 2),
            "broll_coverage_percentage": coverage_pct,
            "summary": f"{campaign.name if campaign else 'Heuristic'} Contextual Edit Plan",
            "hook_text": resolved_hook,
            "campaign_id": campaign.id if campaign else "default",
            "niche": {"id": "generic", "name": "General Video & Podcast"},
            "style": style_payload,
            "editing_style": style_profile.id if style_profile else (campaign.editing_style if campaign else "clean_podcast"),
            "reference_editing": bool(getattr(style_profile, "reference_style", False)) if style_profile else False,
            "style_guidelines": list(getattr(style_profile, "editorial_guidelines", [])) if style_profile else [],
            "shots": shots,
            "text_emphasis_graphics": emphasis_graphics,
        }

    def _detect_emphasis_graphics(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Detect Level 3 typographic emphasis moments from transcript keywords."""
        emphasis_list = []
        if campaign_id != "curious_mike":
            return emphasis_list

        last_t = -10.0

        target_triggers = [
            (["colin", "collin", "sexton"], "COLLIN\nSEXTON", "yellow"),
            (["jalen", "jaylen", "hands"], "JALEN\nHANDS", "yellow"),
            (["chip", "shoulder"], "CHIP ON\nMY SHOULDER", "pink"),
            (["regular guy"], "REGULAR\nGUY", "pink"),
            (["jokic", "nikola"], "NIKOLA\nJOKIC", "yellow"),
            (["knicks"], "KNICKS\nFANS", "pink"),
            (["roommate", "roommates"], "ROOMMATES", "yellow"),
            (["my bad"], "MY BAD", "pink"),
            (["quit", "quitting"], "WANTED TO\nQUIT", "pink"),
        ]

        for seg in segments:
            words = seg.get("words", [])
            seg_text = seg.get("text", "").lower()

            for keywords, display_text, color in target_triggers:
                if any(k in seg_text for k in keywords):
                    match_time = float(seg.get("start", 0.0))
                    if words:
                        for w_obj in words:
                            w_clean = re.sub(r"[^\w\s']", "", w_obj.get("word", "").lower()).strip()
                            if any(w_clean == k or (len(w_clean) >= 3 and (k.startswith(w_clean) or w_clean.startswith(k))) for k in keywords):
                                match_time = float(w_obj.get("start", match_time))
                                break

                    if "SEXTON" in display_text:
                        match_time = max(0.4, round(match_time - 0.16, 2))
                    elif "HANDS" in display_text:
                        match_time = round(match_time, 2)
                    elif "SHOULDER" in display_text:
                        match_time = round(max(0.0, match_time - 0.5), 2)

                    # Ensure at least 4.0 seconds between graphics and not right at the end
                    if match_time - last_t >= 4.0 and match_time < max(0.0, video_duration - 1.5):
                        emphasis_list.append({
                            "text": display_text,
                            "start_time": round(match_time, 2),
                            "duration": 1.2,
                            "color": color
                        })
                        last_t = match_time
                        break

        # Fallback for curious_mike only if no triggers found
        if not emphasis_list and video_duration >= 10.0:
            emphasis_list.append({
                "text": "HIGH SCHOOL\nRANKINGS",
                "start_time": 0.8,
                "duration": 1.2,
                "color": "yellow"
            })
            if video_duration >= 25.0:
                emphasis_list.append({
                    "text": "CHIP ON\nSHOULDER",
                    "start_time": round(video_duration * 0.75, 2),
                    "duration": 1.2,
                    "color": "pink"
                })

        return emphasis_list

    def _generate_contextual_shot_for_segment(
        self,
        seg: Dict[str, Any],
        shot_idx: int,
        start_t: float,
        dur: float,
        campaign: Any,
        niche: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate a contextually relevant B-roll shot specification for a transcript segment."""
        text = seg.get("text", "").lower()

        # Contextual domain mappings for rich visual storytelling
        if any(w in text for w in ["analytic", "data", "metric", "chart", "report", "screen", "kpi"]):
            prompt = "business analytics dashboard computer monitor"
            core = "Data Analytics & Metrics"
        elif any(w in text for w in ["supply chain", "logistic", "ship", "warehouse", "freight", "inventory"]):
            prompt = "modern logistics warehouse supply chain"
            core = "Supply Chain & Operations"
        elif any(w in text for w in ["ad ", "ads", "advertis", "campaign", "marketing"]):
            prompt = "digital advertising marketing strategy"
            core = "Advertising & Marketing"
        elif any(w in text for w in ["innovat", "product", "design", "make", "prototype", "iron", "engineer"]):
            prompt = "product development innovation workshop"
            core = "Product Innovation"
        elif any(w in text for w in ["experience", "learn", "grow", "growth", "advice", "career"]):
            prompt = "entrepreneur business leadership growth"
            core = "Executive Growth & Learning"
        elif any(w in text for w in ["e-commerce", "amazon", "tiktok", "shopify", "sales", "revenue"]):
            prompt = "ecommerce digital revenue operations"
            core = "Digital E-Commerce"
        elif any(w in text for w in ["focus", "disciplin", "work", "routine", "habit"]):
            prompt = "focused professional working desk"
            core = "Deep Focus & Execution"
        elif any(w in text for w in ["win", "winner", "success", "goal", "champion"]):
            prompt = "business team victory celebration"
            core = "Achievement & Success"
        elif any(w in text for w in ["team", "meeting", "collaborat", "office", "brainstorm"]):
            prompt = "startup team meeting collaboration"
            core = "Teamwork & Collaboration"
        else:
            if niche and getattr(niche, "visual_keywords", None):
                prompt = f"{niche.visual_keywords[0]} professional"
                core = f"{niche.name} Focus"
            else:
                words = [w for w in re.findall(r"\b[a-z]{4,}\b", text) if w not in ["what", "with", "from", "this", "that", "know", "like", "they", "have", "been"]]
                prompt = (" ".join(words[:2]) + " modern office") if words else "business modern office workspace"
                core = "Contextual Narrative"

        return {
            "shot_id": f"broll_{shot_idx}",
            "start_time": round(start_t, 2),
            "end_time": round(start_t + dur, 2),
            "duration": round(dur, 2),
            "style": "stockpile",
            "dialogue_quote": seg.get("text", ""),
            "emotional_core": core,
            "visceral_human_metaphor": f"Visualizing {prompt}",
            "micro_prompts": [prompt, f"{prompt} close up", f"{prompt} hands", f"{prompt} action"],
            "search_prompt": prompt,
            "overlay_type": "cutaway",
            "cadence_role": "standard",
            "narrative_reason": f"Contextual reinforcement of: {seg.get('text', '')[:45]}",
        }

    def _audit_and_fill_timeline_distribution(
        self,
        clean_shots: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign: Any,
        niche: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Validate approved B-roll intervals, with an explicit reference-style cadence pass.

        Normal campaigns are strict: invalid intervals are dropped and approved timing
        is never expanded. The reference cinematic treatment additionally permits
        short-to-standard normalization and adjacent whitespace expansion because its
        visual language depends on sustained, meaning-driven cutaway coverage.
        """
        if not clean_shots or video_duration <= 0:
            return [], 0.0

        reference_mode = str(getattr(campaign, "editing_style", "") or "").lower() in {
            "cinematic_social_editorial",
            "cinematic_editorial",
        }
        if reference_mode:
            from ai_broll_autopilot.styles import style_registry
            reference_style = style_registry.get_style("cinematic_social_editorial")
        else:
            reference_style = None

        default_min = float(getattr(Config, "BROLL_MIN_RENDER_DURATION", 0.65))
        default_max = float(getattr(Config, "BROLL_MAX_RENDER_DURATION", 1.8))
        min_duration = (
            float(getattr(reference_style, "micro_broll_min_duration", 0.45))
            if reference_mode else default_min
        )
        max_duration = (
            float(getattr(reference_style, "hero_broll_max_duration", 7.5))
            if reference_mode else default_max
        )
        min_start = 0.0 if reference_mode else 1.2

        cleaned: List[Dict[str, Any]] = []
        last_end = 0.0

        for source_shot in sorted(
            clean_shots,
            key=lambda shot: float(shot.get("start_time", 0.0)),
        ):
            shot = dict(source_shot)
            try:
                start = max(0.0, float(shot.get("start_time", 0.0)))
                end = float(shot.get("end_time", start))
                duration = float(shot.get("duration", end - start))
            except (TypeError, ValueError):
                logger.warning("Dropping malformed B-roll interval: %s", source_shot)
                continue

            interval_duration = end - start
            if abs(interval_duration - duration) > 0.05:
                logger.warning(
                    "Dropping inconsistent B-roll interval [%s]: start=%.2f end=%.2f duration=%.2f",
                    shot.get("shot_id", "unknown"), start, end, duration,
                )
                continue

            if start < last_end:
                logger.warning(
                    "Dropping overlapping B-roll interval [%s] rather than shifting it.",
                    shot.get("shot_id", "unknown"),
                )
                continue

            if start < min_start:
                logger.warning(
                    "Dropping B-roll interval [%s] before the %ss opening boundary.",
                    shot.get("shot_id", "unknown"), min_start,
                )
                continue

            if start >= video_duration or end > video_duration or duration <= 0:
                continue

            role = str(shot.get("cadence_role", "") or "").lower().strip()
            if reference_mode:
                if role == "micro":
                    role_min = float(getattr(reference_style, "micro_broll_min_duration", 0.45))
                    role_max = float(getattr(reference_style, "micro_broll_max_duration", 0.85))
                elif role == "hero":
                    role_min = float(getattr(reference_style, "hero_broll_min_duration", 3.0))
                    role_max = float(getattr(reference_style, "hero_broll_max_duration", 7.5))
                else:
                    role_min = float(getattr(reference_style, "broll_min_duration", 0.65))
                    role_max = float(getattr(reference_style, "broll_max_duration", 2.2))
            else:
                role_min = min_duration
                role_max = max_duration

            if duration < role_min or duration > role_max:
                logger.warning(
                    "Dropping out-of-contract B-roll interval [%s] (%.2fs, role=%s).",
                    shot.get("shot_id", "unknown"), duration, role or "standard",
                )
                continue

            duration = round(end - start, 2)
            if duration < role_min:
                continue

            shot["start_time"] = round(start, 2)
            shot["end_time"] = round(end, 2)
            shot["duration"] = duration
            cleaned.append(shot)
            last_end = end

        if reference_mode and cleaned:
            # Reference treatment: fill only the whitespace already bounded by
            # approved starts. The final implicit shot can become a hero hold.
            cleaned.sort(key=lambda s: float(s.get("start_time", 0.0)))
            for i, shot in enumerate(cleaned):
                st = float(shot["start_time"])
                current_end = float(shot["end_time"])
                next_start = (
                    float(cleaned[i + 1]["start_time"])
                    if i + 1 < len(cleaned) else float(video_duration)
                )
                role = str(shot.get("cadence_role", "") or "").lower()
                was_explicit_role = role in {"micro", "standard", "hero"}
                if not role:
                    role = "standard"
                    shot["cadence_role"] = role

                if i == len(cleaned) - 1 and not was_explicit_role:
                    role = "hero"
                    shot["cadence_role"] = "hero"

                role_max = (
                    float(getattr(reference_style, "hero_broll_max_duration", 7.5))
                    if role == "hero"
                    else float(getattr(reference_style, "micro_broll_max_duration", 0.85))
                    if role == "micro"
                    else float(getattr(reference_style, "broll_max_duration", 2.2))
                )
                if role == "hero":
                    role_min = float(getattr(reference_style, "hero_broll_min_duration", 3.0))
                    desired_end = min(video_duration, st + max(role_min, current_end - st))
                else:
                    role_min = float(getattr(reference_style, "micro_broll_min_duration", 0.45)) if role == "micro" else float(getattr(reference_style, "broll_min_duration", 0.65))
                    desired_end = current_end

                allowable_end = min(video_duration, next_start, st + role_max)
                if allowable_end <= current_end:
                    continue

                # Expand existing contextual holds into adjacent whitespace, but
                # never cross another approved shot or invent a new interval.
                if role == "hero":
                    desired_end = min(allowable_end, max(current_end, st + role_min))
                else:
                    desired_end = allowable_end

                if desired_end > current_end and (
                    role != "micro" or was_explicit_role
                ):
                    shot["end_time"] = round(desired_end, 2)
                    shot["duration"] = round(desired_end - st, 2)
                last_end = float(shot["end_time"])

        total_broll = sum(float(shot["duration"]) for shot in cleaned)
        coverage_pct = (total_broll / video_duration) * 100 if video_duration > 0 else 0.0
        logger.info(
            "Timeline audit completed: %d shots, %.4fs B-roll (%.4f%% coverage, reference=%s)",
            len(cleaned), total_broll, coverage_pct, reference_mode,
        )
        return cleaned, coverage_pct


def explicit_role_for_shot(shot: Dict[str, Any]) -> bool:
    """Return whether cadence_role was explicitly supplied by the Director."""
    return bool(str(shot.get("cadence_role", "") or "").lower().strip())