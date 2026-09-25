"""AI Director service analyzing narrative beats and generating visual edit plans."""

import json
import logging
import re
from typing import Dict, Any, List, Optional
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
        self.client = genai.Client(api_key=self.api_key)

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
        if getattr(campaign, "niche_id", None):
            niche = niche_registry.get_profile(campaign.niche_id)
        if not niche or niche.id == "generic":
            from ai_broll_autopilot.services.niche_detector import niche_detector
            niche_res = niche_detector._detect_heuristic(full_transcript)
            if niche_res and niche_res.niche_id != "generic":
                niche = niche_registry.get_profile(niche_res.niche_id)
            else:
                niche = niche_registry.get_profile("generic")

        # Target calculations based on campaign or niche rules
        if campaign.id == "curious_mike":
            target_broll_ratio = campaign.max_broll_ratio  # 0.33 for Curious Mike
        else:
            target_broll_ratio = niche.editing.max_broll_ratio if niche else campaign.max_broll_ratio

        target_broll_seconds = round(video_duration * target_broll_ratio, 1)
        target_aroll_seconds = round(video_duration - target_broll_seconds, 1)
        target_shots = max(1, min(6, int(round(target_broll_seconds / 2.2))))
        allow_memes = bool(campaign.allow_ai_broll and getattr(niche.editing, "meme_cutaways", False))

        if campaign.id == "curious_mike":
            # Match curated moment if specified
            matched_moment = None
            if curated_moment_id:
                for m in campaign.curated_moments:
                    if m.moment_id.lower() == curated_moment_id.lower():
                        matched_moment = m
                        break

            chosen_hook = custom_hook or (matched_moment.screen_hook if matched_moment else None)

            director_prompt = f"""You are the Master AI Video Director for the CURIOUS MIKE podcast clipping campaign (hosted by Michael Porter Jr. @curiousmike / @mpj).

MANDATORY CAMPAIGN DIRECTING OBJECTIVES:
1. FORMAT & SPEAKER COVERAGE (CRITICAL CAMPAIGN RULE):
   - Format 1 (Straight Talking Head) or Format 2 (Talking Head + Real Sports B-Roll).
   - NEVER cover the speaker for more than 1/3 (33%) of the video duration!
   - Total Video Duration: {video_duration:.2f} seconds. Max B-roll duration: ~{target_broll_seconds:.1f}s total.
   - The speaker's face and reactions MUST be on screen for at least 67% of the clip duration.
   - Any cutaways MUST be short (1.0s to 2.5s each), cutting in directly on the spoken keyword (e.g. named player, arena, team, Knicks, Pat Bev, Jokic).
   - Cut back to the speaker immediately.
   - Generate at most {target_shots} focused, high-relevance cutaway(s).

2. ZERO AI VIDEO POLICY (INSTANT REJECTION RULE):
   - STRICTLY NO AI-generated video, AI avatars, cartoon memes, or fictional visuals.
   - All visual B-roll MUST be real footage (NBA basketball highlights, press conferences, arena footage, or training).
   - "style" MUST be "stockpile".

3. HOOK REQUIREMENT:
   - Provide a bold, punchy, all-caps screen hook in "hook_text" (e.g. "HE REALLY SAID THIS ABOUT KNICKS FANS").
   {f'Target Hook: "{chosen_hook}"' if chosen_hook else ''}

4. LEVEL 3 LARGE TYPOGRAPHIC EMPHASIS GRAPHICS:
   - Identify 2 to 4 high-impact keywords, player names, or punchy phrases (e.g., "COLLIN\\nSEXTON", "JAYLEN\\nHANDS", "TOOK THAT\\nPERSONAL") spoken in the clip.
   - Format: 1-3 uppercase words, stacked with \\n.
   - Color: "yellow" for player names/rankings/facts, "pink" for dramatic hot-takes/climax phrases.
   - Duration: 1.0 to 1.4 seconds.

VIDEO DURATION: {video_duration:.2f} seconds
TIMESTAMPED TRANSCRIPT:
{formatted_segments}

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "summary": "Short 1-sentence description of the moment",
  "hook_text": "{chosen_hook or 'TRAE DID NOT HOLD BACK'}",
  "text_emphasis_graphics": [
    {{
      "text": "COLLIN\\nSEXTON",
      "start_time": 0.6,
      "duration": 1.2,
      "color": "yellow"
    }}
  ],
  "shots": [
    {{
      "shot_id": "broll_1",
      "start_time": 2.5,
      "end_time": 4.5,
      "duration": 2.0,
      "style": "stockpile",
      "dialogue_quote": "Exact spoken line from transcript",
      "emotional_core": "NBA rivalry or basketball discussion",
      "visceral_human_metaphor": "Real basketball action or arena atmosphere",
      "micro_prompts": ["nba basketball game action", "basketball arena court crowd"],
      "search_prompt": "nba basketball game",
      "overlay_type": "cutaway",
      "narrative_reason": "Contextual sports illustration on keyword"
    }}
  ]
}}"""
        else:
            niche_desc = f"{niche.name} ({niche.description})" if niche else "General Podcast & Video"
            niche_keywords_hint = ", ".join(niche.visual_keywords[:8]) if niche else "focus, desk, laptop, discussion"

            meme_instructions = ""
            if allow_memes:
                meme_instructions = """
4. CONTEXTUAL MEME CUTAWAYS (OPTIONAL FOR HIGH-ENERGY COMEDY / STREAMER MOMENTS):
   - You may designate up to 1-2 shots as "style": "meme" if a wild claim, rage outburst, or high-energy reaction occurs.
   - For all other shots, use real stock footage ("style": "stockpile")."""

            director_prompt = f"""You are the Master AI Video Director for high-retention viral short-form videos (TikTok, Reels, YouTube Shorts).
CONTENT DOMAIN: {niche_desc}
RELEVANT VISUAL THEMES: {niche_keywords_hint}

MANDATORY DIRECTING OBJECTIVES:
1. BALANCED PACING & CONTEXTUAL B-ROLL COVERAGE:
   - Total Video Duration: {video_duration:.2f} seconds.
   - Target Total B-Roll Duration: ~{target_broll_seconds:.1f} seconds (~{int(target_broll_ratio*100)}% of video).
   - Target Total Speaker (A-Roll) Duration: ~{target_aroll_seconds:.1f} seconds.
   - Generate {target_shots} rapid, snappy cuts (1.5s to 2.4s each).
   - Keep speaker on screen for the first 0.8s to 1.5s opening hook.
   - NEVER let any cutaway drag out longer than 2.5 seconds! Cut back to the speaker smoothly.

2. ACCURATE CONTEXTUAL MATCHING (CRITICAL):
   - Visuals MUST directly amplify the EXACT topic and words being spoken at each timestamp!
   - Select real, photogenic visual metaphors directly tied to the spoken words.
   - For business, marketing, or tech: modern clean office, charts, hands on laptop/phone, analytics, presentation, whiteboard.
   - For lifestyle, self-improvement: focused workout, runner, journaling, deep concentration, conversation.
   - STRICTLY FORBIDDEN:
     • DO NOT invent negative or irrelevant drama (e.g. fired employee, computer rage) unless the speaker explicitly describes it!
     • All visual shots must have "style": "stockpile" (real-world stock footage).

3. OPTIMIZED STOCK FOOTAGE SEARCH PROMPTS:
   - "search_prompt" MUST be 2 to 4 clean, photogenic keywords optimized for stock video search.
{meme_instructions}

VIDEO DURATION: {video_duration:.2f} seconds
TIMESTAMPED TRANSCRIPT:
{formatted_segments}

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
      "emotional_core": "Topic theme (e.g. Marketing Strategy, Deep Focus, Tech Innovation)",
      "visceral_human_metaphor": "Realistic contextual scene matching the quote",
      "micro_prompts": [
        "marketer working on laptop with charts",
        "close up hands typing on modern keyboard"
      ],
      "search_prompt": "digital marketing business strategy",
      "overlay_type": "cutaway",
      "narrative_reason": "Contextual visual amplification of spoken concept"
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
                min_shots = 1 if campaign.id == "curious_mike" else 2
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
            max_dur = float(Config.MAX_CLIP_DURATION_SECONDS)

            for shot in plan_data.get("shots", []):
                # Strictly filter out any A-roll / speaker shots
                shot_id_str = str(shot.get("shot_id", "")).lower()
                ov_type = str(shot.get("overlay_type", "")).lower()
                if "aroll" in shot_id_str or ov_type == "speaker":
                    continue

                start = max(0.0, float(shot.get("start_time", 0.0)))
                # Prevent overlap with previous shot (keep minimum 0.4s speaker gap)
                if start < last_end + 0.4:
                    start = last_end + 0.4

                if start >= video_duration - 0.8:
                    break

                style = shot.get("style", "stockpile").lower()
                if not campaign.allow_ai_broll or style not in ("stockpile", "collage", "meme"):
                    style = "stockpile"

                # Fast-paced short-form duration: 1.4s to 2.4s (snappy cuts)
                max_clip = min(campaign.max_cutaway_seconds, max_dur)
                duration = min(max_clip, max(1.2, float(shot.get("duration", 2.0))))
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

            # Memes assignment only for campaigns that allow AI/meme B-roll
            if campaign.allow_ai_broll:
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

            total_broll_time = sum(s["duration"] for s in clean_shots)
            coverage_pct = round((total_broll_time / video_duration) * 100, 1) if video_duration > 0 else 0

            # Expand coverage only for default viral campaign (~60% target)
            if campaign.allow_ai_broll and coverage_pct < 58.0 and clean_shots:
                logger.info(f"B-roll coverage ({coverage_pct}%) below 58%. Expanding shot durations toward ~60%...")
                for idx, s in enumerate(clean_shots):
                    next_start = clean_shots[idx + 1]["start_time"] if idx + 1 < len(clean_shots) else (video_duration - 0.5)
                    avail = next_start - s["start_time"] - 0.4  # preserve 0.4s gap
                    if avail > s["duration"]:
                        add = min(avail - s["duration"], max_dur - s["duration"])
                        if add > 0:
                            s["duration"] = round(s["duration"] + add, 2)
                            s["end_time"] = round(s["start_time"] + s["duration"], 2)

                total_broll_time = sum(s["duration"] for s in clean_shots)
                coverage_pct = round((total_broll_time / video_duration) * 100, 1)

            # Clamp coverage if campaign enforces max_broll_ratio (e.g. Curious Mike <= 33%)
            if not campaign.allow_ai_broll and coverage_pct > (campaign.max_broll_ratio * 100):
                logger.info(f"Clamping B-roll coverage ({coverage_pct}%) to campaign limit {campaign.max_broll_ratio*100}%...")
                max_total_sec = video_duration * campaign.max_broll_ratio
                cur_total = 0.0
                clamped_shots = []
                for s in clean_shots:
                    if cur_total + s["duration"] <= max_total_sec:
                        clamped_shots.append(s)
                        cur_total += s["duration"]
                    elif cur_total < max_total_sec:
                        rem = round(max_total_sec - cur_total, 2)
                        if rem >= 1.0:
                            s["duration"] = rem
                            s["end_time"] = round(s["start_time"] + rem, 2)
                            clamped_shots.append(s)
                            cur_total += rem
                        break
                clean_shots = clamped_shots
                total_broll_time = sum(s["duration"] for s in clean_shots)
                coverage_pct = round((total_broll_time / video_duration) * 100, 1)

            # 2. If still below 55% and there is an uncovered window at the end or in a wide gap, add a contextual shot (Default campaign only)
            if campaign.allow_ai_broll and campaign.id != "curious_mike" and coverage_pct < 56.0 and segments:
                last_shot_end = clean_shots[-1]["end_time"] if clean_shots else 1.0
                if (video_duration - last_shot_end) >= 3.0:
                    start = round(last_shot_end + 0.6, 2)
                    dur = min(max_dur, round(video_duration - start - 0.5, 2))
                    if dur >= 2.0:
                        # Find overlapping segment at the end
                        end_seg = segments[-1]
                        seg_text = end_seg.get("text", "").lower()
                        if any(w in seg_text for w in ["focus", "disciplin", "work", "routine", "go by"]):
                            prompt = "focused professional determined"
                        elif any(w in seg_text for w in ["win", "winner", "success", "goal"]):
                            prompt = "business victory celebration"
                        else:
                            prompt = "confident professional modern office"

                        clean_shots.append({
                            "shot_id": f"broll_{len(clean_shots)+1}",
                            "start_time": start,
                            "end_time": round(start + dur, 2),
                            "duration": dur,
                            "style": "stockpile",
                            "dialogue_quote": end_seg.get("text", ""),
                            "emotional_core": "Closing Determination",
                            "visceral_human_metaphor": f"Visualizing {prompt}",
                            "micro_prompts": [prompt, f"{prompt} close up", f"{prompt} hands", f"{prompt} modern"],
                            "search_prompt": prompt,
                            "overlay_type": "cutaway",
                            "narrative_reason": "Closing beat visual reinforcement",
                        })
                        total_broll_time = sum(s["duration"] for s in clean_shots)
                        coverage_pct = round((total_broll_time / video_duration) * 100, 1)

            if campaign.id == "curious_mike":
                # Ensure all shots are strictly real basketball footage (no corporate stock, no memes)
                for s in clean_shots:
                    s["style"] = "stockpile"
                    sp = s.get("search_prompt", "").lower()
                    if not any(k in sp for k in ("basketball", "nba", "court", "hoop", "dunk", "guard", "sexton", "hands")):
                        s["search_prompt"] = f"basketball player {s.get('search_prompt', 'game action')}"
                # Enforce Curious Mike 33% max B-roll rule (max 3 punchy cuts)
                if len(clean_shots) > 3:
                    clean_shots = clean_shots[:3]
                total_broll_time = sum(s["duration"] for s in clean_shots)
                coverage_pct = round((total_broll_time / video_duration) * 100, 1)

            # Preserve or detect Level 3 typographic emphasis graphics
            emphasis_graphics = plan_data.get("text_emphasis_graphics", [])
            if not emphasis_graphics and campaign and campaign.id == "curious_mike":
                emphasis_graphics = self._detect_curious_mike_emphasis(segments, video_duration)

            plan_result = {
                "total_duration": video_duration,
                "broll_shot_count": len(clean_shots),
                "broll_coverage_seconds": round(total_broll_time, 2),
                "broll_coverage_percentage": coverage_pct,
                "summary": plan_data.get("summary", f"{campaign.name} Contextual Edit Plan"),
                "hook_text": chosen_hook or plan_data.get("hook_text"),
                "campaign_id": campaign.id,
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
        is_curious_mike = bool(campaign and campaign.id == "curious_mike")
        target_ratio = campaign.max_broll_ratio if campaign else Config.TARGET_BROLL_RATIO
        target_broll_dur = video_duration * target_ratio
        shot_dur = 2.0
        num_shots = max(1, min(2, int(round(target_broll_dur / shot_dur)))) if is_curious_mike else max(3, int(round(target_broll_dur / shot_dur)))

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
            if is_curious_mike:
                search_prompt = "nba basketball player court"
                emotional_core = "NBA Basketball Conversation"
            elif any(w in seg_text for w in ["focus", "disciplin", "work", "habit", "lesson"]):
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
            last_end = end

        total_broll = sum(s["duration"] for s in shots)
        coverage_pct = round((total_broll / video_duration) * 100, 1) if video_duration > 0 else 0

        emphasis_graphics = []
        if campaign and campaign.id == "curious_mike":
            emphasis_graphics = self._detect_curious_mike_emphasis(segments, video_duration)

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

        return {
            "total_duration": video_duration,
            "broll_shot_count": len(shots),
            "broll_coverage_seconds": round(total_broll, 2),
            "broll_coverage_percentage": coverage_pct,
            "summary": f"{campaign.name if campaign else 'Heuristic'} Contextual Edit Plan",
            "hook_text": resolved_hook,
            "campaign_id": campaign.id if campaign else "default",
            "shots": shots,
            "text_emphasis_graphics": emphasis_graphics,
        }

    def _detect_curious_mike_emphasis(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """Detect signature Level 3 typographic emphasis moments for Curious Mike."""
        emphasis_list = []
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

        # Fallback if no triggers found
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

