"""AI Director service analyzing narrative beats and generating visual edit plans."""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from google import genai
from google.genai import types

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


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

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = model_name or Config.GEMINI_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning(f"Failed to initialize Gemini client for Director: {exc}")

    async def create_edit_plan(
        self,
        full_transcript: str,
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign_id: str = "default",
        curated_moment_id: Optional[str] = None,
        custom_hook: Optional[str] = None,
        user_topic_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete Visual Edit Plan respecting campaign-specific constraints and visual pacing."""
        from ai_broll_autopilot.campaigns import campaign_registry
        campaign = campaign_registry.get_campaign(campaign_id)

        logger.info(
            f"AI Director analyzing {len(segments)} segments for video length {video_duration:.1f}s "
            f"under campaign '{campaign.id}' (Target B-Roll: {campaign.max_broll_ratio*100:.0f}%)"
        )

        # Format segments for Director prompt
        formatted_segments = "\n".join([
            f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}"
            for seg in segments
        ])

        from ai_broll_autopilot.services.learning import feedback_engine
        learned_rules = feedback_engine.get_learned_instructions(full_transcript)

        import math
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

        # Target calculations: a reference style can intentionally override the
        # generic niche's conservative B-roll ratio.
        style_broll_ratio = getattr(style_profile, "broll_target_ratio", None)
        target_broll_ratio = (
            float(style_broll_ratio)
            if style_broll_ratio is not None
            else (niche.editing.max_broll_ratio if niche else campaign.max_broll_ratio)
        )

        target_broll_seconds = round(video_duration * target_broll_ratio, 1)
        target_aroll_seconds = round(video_duration - target_broll_seconds, 1)

        # The reference edit uses a handful of deliberate visual scenes rather than
        # a constant stream of 0.5s cuts. Keep roughly one visual opportunity per
        # 2.8s, while allowing a longer hero hold to carry the ending/payoff.
        avg_cut_seconds = 2.8 if not getattr(style_profile, "reference_style", False) else 2.6
        max_possible_shots = max(3, int(video_duration / avg_cut_seconds))
        target_shots = max(
            3,
            min(max_possible_shots, int(round(target_broll_seconds / (1.8 if getattr(style_profile, "reference_style", False) else 2.0))))
        )

        # Partition video duration into 3 narrative acts for uniform timeline distribution
        t_act1 = round(video_duration * 0.33, 1)
        t_act2 = round(video_duration * 0.66, 1)
        quota_act1 = max(1, target_shots // 3)
        quota_act2 = max(1, target_shots // 3)
        quota_act3 = max(1, target_shots - quota_act1 - quota_act2)

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

        user_context_block = ""
        if user_topic_context and user_topic_context.strip():
            user_context_block = f"""
USER-SPECIFIED TOPIC / VIDEO CONTEXT (HIGHEST PRIORITY):
The user explicitly specified the exact topic/subject of this clip:
"{user_topic_context.strip()}"
All selected B-roll cutaways MUST be directly relevant to this specific topic!
Never choose generic, sloppy, or unrelated footage. Every visual must specifically match this subject matter.
"""

        director_prompt = f"""You are the Master AI Video Director for high-retention viral short-form videos (TikTok, Reels, YouTube Shorts).
CAMPAIGN: {campaign.name}
CONTENT DOMAIN: {niche_desc}
RELEVANT VISUAL THEMES: {niche_keywords_hint}
{user_context_block}
MANDATORY DIRECTING OBJECTIVES:
1. RHYTHMIC EDITING, NOT A MECHANICAL GRID:
   - Total Video Duration: {video_duration:.2f} seconds.
   - Target Total B-Roll Duration: ~{target_broll_seconds:.1f} seconds (~{int(target_broll_ratio*100)}% of video).
   - Target Total Speaker (A-Roll) Duration: ~{target_aroll_seconds:.1f} seconds.
   - Generate EXACTLY {target_shots} contextual cutaways, but do NOT force equal spacing.
   - Build the sequence around the speech: setup -> literal context -> reaction/consequence -> narrative hold -> payoff.
   - For the reference treatment, favor 0.8-2.2s micro cutaways and permit occasional 3-8s hero holds when one visual can carry a whole thought or payoff.
   - Do not manufacture lots of tiny cuts just to hit a shot count.
   - When the reference treatment is active, the first visual can be B-roll immediately; a mandatory A-roll intro is NOT required.
   - Keep the speaker visible only where it strengthens authenticity, timing, or an emotional beat.
   - Avoid large digital zooms; use only restrained emphasis around important words.
   - Do not fire an SFX on every cut. Use sound accents for meaningful transitions/reveals only.

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
=== ACT 1 (HOOK & SETUP: 0.0s - {t_act1:.1f}s) — Place {quota_act1} cut(s) here ===
{act1_txt}

=== ACT 2 (BODY & DEVELOPMENT: {t_act1:.1f}s - {t_act2:.1f}s) — Place {quota_act2} cut(s) here ===
{act2_txt}

=== ACT 3 (CLIMAX & CONCLUSION: {t_act2:.1f}s - {video_duration:.1f}s) — Place {quota_act3} cut(s) here ===
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
  ]
}}"""

        models_to_try = [self.model_name] + [m for m in Config.GEMINI_FALLBACK_MODELS if m != self.model_name]
        plan_data = None

        if self.client:
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
        else:
            logger.warning("Gemini client not initialized for Director (no API key configured).")

        if not plan_data or "shots" not in plan_data or not plan_data["shots"]:
            logger.warning(f"AI Director failed to produce valid plan for '{campaign.id}'. Falling back to heuristic plan.")
            return self._create_heuristic_plan(
                segments, video_duration, campaign=campaign, custom_hook=chosen_hook or custom_hook, curated_moment_id=curated_moment_id,
                user_topic_context=user_topic_context
            )

        try:
            # Validate and clamp shot timestamps to video bounds and campaign constraints
            clean_shots = []
            last_end = 0.0
            reference_editing = bool(getattr(style_profile, "reference_style", False))
            configured_max_dur = float(Config.MAX_CLIP_DURATION_SECONDS)
            hero_max_dur = float(getattr(style_profile, "hero_broll_max_duration", configured_max_dur))
            max_dur = max(configured_max_dur, hero_max_dur) if reference_editing else configured_max_dur

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

                # Reference edits use two timing scales: short punctuation and rare
                # long hero holds. Other styles retain the campaign ceiling.
                style_max_cut = (
                    hero_max_dur
                    if reference_editing
                    else float(campaign.max_cutaway_seconds)
                )
                max_clip = min(style_max_cut, max_dur)
                min_clip = 0.8 if reference_editing else 1.2
                duration = min(max_clip, max(min_clip, float(shot.get("duration", 2.0))))
                if style == "meme":
                    duration = min(2.0, max(1.3, duration))
                end = min(video_duration, start + duration)
                duration = round(end - start, 2)

                if duration < 1.0:
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

            # Preserve or detect Level 3 typographic emphasis graphics
            emphasis_graphics = plan_data.get("text_emphasis_graphics", [])

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
                "user_topic_context": user_topic_context.strip() if user_topic_context else None,
            }

            logger.info(f"AI Director planned {len(clean_shots)} B-roll cutaways covering {total_broll_time:.1f}s ({coverage_pct}% of {video_duration:.1f}s)")
            return plan_result

        except Exception as e:
            logger.error(f"AI Director planning post-processing failed: {e}", exc_info=True)
            return self._create_heuristic_plan(
                segments, video_duration, campaign=campaign, custom_hook=chosen_hook or custom_hook, curated_moment_id=curated_moment_id,
                user_topic_context=user_topic_context
            )

    def _create_heuristic_plan(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        campaign: Optional[Any] = None,
        custom_hook: Optional[str] = None,
        curated_moment_id: Optional[str] = None,
        user_topic_context: Optional[str] = None,
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
            "user_topic_context": user_topic_context.strip() if user_topic_context else None,
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
        """Audit timeline for dead zones or front-loading and inject contextual shots across the full duration."""
        if not clean_shots and not segments:
            return clean_shots, 0.0

        from ai_broll_autopilot.styles import style_registry
        style_id = str(getattr(campaign, "editing_style", "") or "").strip()
        style_profile = style_registry.get_style(style_id) if style_id else None
        reference_style = bool(
            getattr(style_profile, "reference_style", False)
            or style_id in {"cinematic_social_editorial", "cinematic_editorial"}
        )

        min_speaker_gap = 0.15 if reference_style else 1.0
        max_gap_allowed = (
            float(getattr(style_profile, "max_continuous_aroll_seconds", 3.5))
            if reference_style and style_profile
            else 4.0
        )
        configured_max_clip = float(getattr(campaign, "max_cutaway_seconds", 2.5))
        style_max_clip = (
            float(getattr(style_profile, "hero_broll_max_duration", configured_max_clip))
            if reference_style and style_profile
            else configured_max_clip
        )
        max_clip = min(
            8.0 if reference_style else float(Config.MAX_CLIP_DURATION_SECONDS),
            style_max_clip,
        )
        min_clip = (
            float(getattr(style_profile, "broll_min_duration", 0.8))
            if reference_style and style_profile
            else 1.4
        )

        # 1. Clean and space existing shots
        sorted_shots = sorted(clean_shots, key=lambda s: float(s.get("start_time", 0.0)))
        cleaned = []
        last_end = 0.0

        for s in sorted_shots:
            st = max(0.0 if reference_style else 0.8, float(s.get("start_time", 0.0)))
            if st < last_end + min_speaker_gap:
                st = last_end + min_speaker_gap
            dur = min(max_clip, max(min_clip, float(s.get("duration", 2.0))))
            if st + dur > video_duration - 0.5:
                dur = max(min_clip, video_duration - 0.5 - st)
            if dur < 1.0 or st >= video_duration - 1.0:
                continue
            et = round(st + dur, 2)
            s["start_time"] = round(st, 2)
            s["end_time"] = et
            s["duration"] = round(et - st, 2)
            cleaned.append(s)
            last_end = et

        # 2. Open on a meaningful visual in reference mode instead of forcing
        # a talking-head intro.
        opening_threshold = 1.0 if reference_style else 4.5
        if segments and (not cleaned or cleaned[0]["start_time"] > opening_threshold):
            early_segs = (
                [s for s in segments if s.get("start", 0.0) >= 0.0 and s.get("end", 0.0) <= 4.2]
                if reference_style
                else [s for s in segments if s.get("start", 0.0) >= 0.8 and s.get("end", 0.0) <= 4.2]
            )
            if early_segs:
                seg = early_segs[0]
                ins_st = 0.0 if reference_style else 1.2
                ins_dur = min(max_clip, max(min_clip, 2.0))
                new_s = self._generate_contextual_shot_for_segment(seg, 1, ins_st, ins_dur, campaign, niche)
                cleaned.insert(0, new_s)
                if len(cleaned) > 1 and cleaned[1]["start_time"] < new_s["end_time"] + min_speaker_gap:
                    cleaned[1]["start_time"] = round(new_s["end_time"] + min_speaker_gap, 2)
                    cleaned[1]["end_time"] = round(cleaned[1]["start_time"] + cleaned[1]["duration"], 2)

        # 3. Check internal gaps between consecutive shots
        i = 0
        while i < len(cleaned) - 1:
            gap_start = cleaned[i]["end_time"]
            gap_end = cleaned[i + 1]["start_time"]
            gap = gap_end - gap_start
            if gap > max_gap_allowed and segments:
                matching = [s for s in segments if s.get("end", 0.0) > gap_start and s.get("start", 0.0) < gap_end]
                if matching:
                    seg = matching[0]
                    ins_st = round(gap_start + min_speaker_gap, 2)
                    ins_dur = min(max_clip, max(min_clip, round(gap - (2 * min_speaker_gap), 2)))
                    if ins_dur >= min_clip and ins_st + ins_dur <= gap_end - 0.5:
                        new_s = self._generate_contextual_shot_for_segment(seg, len(cleaned) + 1, ins_st, ins_dur, campaign, niche)
                        cleaned.insert(i + 1, new_s)
                        i += 1
            i += 1

        # 4. Check TAIL GAP (from last shot to video_duration) - GUARANTEES SECOND HALF IS COVERED
        last_end = cleaned[-1]["end_time"] if cleaned else 1.0
        tail_gap = video_duration - last_end
        if tail_gap >= 3.8 and segments:
            tail_segs = [s for s in segments if s.get("end", 0.0) > last_end + 0.2]
            if tail_segs:
                num_tail_shots = max(1, int(round((tail_gap - 0.8) / 3.4)))
                step = max(1, len(tail_segs) // num_tail_shots)
                cur_t = round(last_end + min_speaker_gap, 2)
                for k in range(num_tail_shots):
                    seg_idx = min(len(tail_segs) - 1, k * step)
                    seg = tail_segs[seg_idx]
                    rem_time = video_duration - 0.8 - cur_t
                    if rem_time < min_clip:
                        break
                    shot_dur = min(max_clip, max(min_clip, round(min(2.0, rem_time), 2)))
                    new_s = self._generate_contextual_shot_for_segment(seg, len(cleaned) + 1, cur_t, shot_dur, campaign, niche)
                    cleaned.append(new_s)
                    cur_t = round(new_s["end_time"] + min_speaker_gap, 2)

        # 5. Re-sort & Re-index shots sequentially
        cleaned = sorted(cleaned, key=lambda s: float(s.get("start_time", 0.0)))
        for idx, s in enumerate(cleaned):
            s["shot_id"] = f"broll_{idx+1}"

        # 6. Reference coverage balancing: expand useful visuals before trimming.
        style_ratio = getattr(style_profile, "broll_target_ratio", None)
        target_ratio = (
            float(style_ratio)
            if reference_style and style_ratio is not None
            else (niche.editing.max_broll_ratio if niche else campaign.max_broll_ratio)
        )
        target_broll_sec = video_duration * target_ratio
        total_broll = sum(float(s["duration"]) for s in cleaned)

        if reference_style and cleaned and total_broll < target_broll_sec:
            hero_cap = float(getattr(style_profile, "hero_broll_max_duration", 7.5))
            standard_cap = float(getattr(style_profile, "broll_max_duration", 2.2))
            for _ in range(4):
                if total_broll >= target_broll_sec:
                    break
                changed = False
                for idx, shot in enumerate(cleaned):
                    start_time = float(shot["start_time"])
                    current = float(shot["duration"])
                    impact = float(shot.get("impact_score", 0.0) or 0.0)
                    visual = float(shot.get("visualizability", 0.0) or 0.0)
                    cap = hero_cap if impact >= 85 and visual >= 85 else standard_cap
                    next_start = (
                        float(cleaned[idx + 1]["start_time"])
                        if idx + 1 < len(cleaned)
                        else video_duration
                    )
                    room = max(0.0, next_start - start_time - 0.08)
                    desired = min(
                        cap,
                        room,
                        current + max(0.0, target_broll_sec - total_broll),
                    )
                    if desired > current + 0.05:
                        shot["duration"] = round(desired, 2)
                        shot["end_time"] = round(start_time + desired, 2)
                        total_broll = sum(float(s["duration"]) for s in cleaned)
                        changed = True
                        if total_broll >= target_broll_sec:
                            break
                if not changed:
                    break

        if total_broll > target_broll_sec and cleaned:
            scale = target_broll_sec / total_broll
            floor = float(getattr(style_profile, "broll_min_duration", 0.8)) if reference_style else 1.3
            for s in cleaned:
                scaled_dur = round(max(floor, s["duration"] * scale), 2)
                s["duration"] = scaled_dur
                s["end_time"] = round(s["start_time"] + scaled_dur, 2)
            total_broll = sum(s["duration"] for s in cleaned)

        cov_pct = round((total_broll / video_duration) * 100, 1) if video_duration > 0 else 0.0
        logger.info(f"Timeline audit completed: {len(cleaned)} shots spanning 0s to {cleaned[-1]['end_time'] if cleaned else 0}s (coverage: {cov_pct}%)")
        return cleaned, cov_pct

