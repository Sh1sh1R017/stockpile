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
        video_duration: float
    ) -> Dict[str, Any]:
        """Generate a complete Visual Edit Plan targeting ~60% B-roll coverage and deep contextual accuracy."""
        logger.info(f"AI Director analyzing {len(segments)} segments for video length {video_duration}s (Target B-Roll: 60%)")

        # Format segments for Director prompt
        formatted_segments = "\n".join([
            f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}"
            for seg in segments
        ])

        from ai_broll_autopilot.services.learning import feedback_engine
        learned_rules = feedback_engine.get_learned_instructions(full_transcript)

        import math

        # Target calculations for 60% B-roll coverage
        target_broll_ratio = Config.TARGET_BROLL_RATIO  # 0.60
        target_broll_seconds = round(video_duration * target_broll_ratio, 1)
        target_aroll_seconds = round(video_duration - target_broll_seconds, 1)
        target_shots = max(2, int(math.ceil(target_broll_seconds / 3.0)))

        director_prompt = f"""You are the Master AI Video Director for ultra-high-retention viral short-form videos (TikTok, Reels, YouTube Shorts).

MANDATORY DIRECTING OBJECTIVES:
1. EXACT ~60% B-ROLL TIMELINE COVERAGE (CRITICAL USER MANDATE):
   - Total Video Duration: {video_duration:.2f} seconds.
   - Target Total B-Roll Duration: ~{target_broll_seconds:.1f} seconds (MUST BE ~60% of video).
   - Target Total Speaker (A-Roll) Duration: ~{target_aroll_seconds:.1f} seconds (approximately 40% of video).
   - Target Number of B-roll Shots: Generate EXACTLY {target_shots} shots (typically 2.8s to 3.8s each).
   - RHYTHMIC TIMELINE DISTRIBUTION:
     • Keep the speaker on screen (A-roll) for the first 1.0s to 1.8s opening hook.
     • Cut to engaging B-roll for 2.8s to 3.8s.
     • Cut back to speaker face for 0.8s to 1.5s for narrative connection or punchlines.
     • Distribute shots from the beginning all the way through the end of the video!
     • Cumulative B-roll duration MUST equal approximately {target_broll_seconds:.1f} seconds (~60% of total video)!

2. ACCURATE CONTEXTUAL MATCHING (CRITICAL):
   - The visuals MUST directly match and amplify the EXACT topic and words being spoken at each timestamp!
   - Analyze the true subject matter of the transcript:
     • FOCUS & DISCIPLINE: Deep focus at desk, writing on clipboard/checklist, intense concentration, athletic training.
     • WINNING vs LOSING: Contrast triumph, finish line victory, high-fives ("winners focus") with mindless phone doomscrolling on couch ("losers don't").
     • PARENT / MENTOR WISDOM: Father and son conversation, mentor guiding young student, warm wisdom.
     • HABITS / CLIPBOARDS: Handwriting on clipboard, checking off items on daily checklist, desk workflow.
     • BUSINESS & FINANCE: Bright modern office, charts, handshake, professional strategy.
     • TECH & CODING: Modern code editor on screen, developer with headphones.
   - STRICTLY FORBIDDEN:
     • NEVER show someone getting fired, packing a cardboard box, or having computer rage UNLESS the speaker explicitly discusses job loss or computer crashes!
     • DO NOT invent negative or irrelevant drama that contradicts the speaker's message.

3. OPTIMIZED STOCK FOOTAGE SEARCH PROMPTS:
   - "search_prompt" MUST be 2 to 4 clean, photogenic keywords optimized for Pexels 4K stock video search.
     Examples:
     • "focused man writing desk"
     • "runner winning finish line"
     • "person scrolling smartphone couch"
     • "father teaching son"
     • "businessman checking clipboard"
4. CONTEXTUAL MEME & CREATOR CUTAWAYS (PRIORITIZE FAMILIAR CREATOR FACES FOR MAXIMUM ATTENTION):
   - CRITICAL USER MANDATE: Familiar creator faces (IShowSpeed, CaseOh, Jynxzi) capture exponentially higher viewer retention than generic stock footages! Prioritize them over dry stock when high emotion occurs!
   - Whenever dialogue expresses intense emotion, shock, rage, disbelief, satire, or contrasted opinions, use "style": "meme"!
   - VIRAL CREATOR ARCHETYPES:
     • "ishowspeed_shock": Darren Watkins Jr (IShowSpeed) wide-eyed screaming shock & hype. Use for: intense hype, mind-blowing claims, screaming/shouting moments, crazy excitement, wild statements!
     • "caseoh_rage": CaseOh furious headset mic rage & screaming. Use for: outrage, frustrating fails, bad takes, calling someone out, getting roasted, heavy mistakes!
     • "jynxzi_freakout": Jynxzi controller-slam & disbelief scream. Use for: hilarious shock, absurdity, 'bro what' moments, clutch fails, gaming!
     • "the_trusted_doctor": Johnny Sins specialist/doctor cutaway. Use whenever an expert, specialist, doctor, or seasoned professional is mentioned (comment section magnet)!
     • "gigachad": Peak masculine discipline, sigma mindset, absolute winner triumph.
     • "hide_the_pain_harold": Strained smile, enduring awkwardness or inner panic.
     • "stepped_in_shit": For bad opinions, terrible takes, excuses, or distractions. Provide "meme_captions": {{"shoe_text": "The bad opinion / excuse"}}.
     • "drake": For contrasting a rejected bad option vs an accepted good option. Provide "meme_captions": {{"top_text": "Rejected option", "bottom_text": "Accepted option"}}.
     • "clown": For progressive foolish steps or clown logic. Provide "meme_captions": {{"step_1": "...", "step_2": "...", "step_3": "...", "step_4": "..."}}.
     • "same_picture": For comparing two identically bad or identical things.
   - For realistic scenes (workspace, athletics, mentor discussions), use "style": "stockpile".

VIDEO DURATION: {video_duration:.2f} seconds
TIMESTAMPED TRANSCRIPT:
{formatted_segments}

{learned_rules}

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "summary": "Short 1-sentence narrative arc summary",
  "shots": [
    {{
      "shot_id": "broll_1",
      "start_time": 1.5,
      "end_time": 4.8,
      "duration": 3.3,
      "style": "stockpile",
      "meme_template": "stepped_in_shit",
      "meme_captions": {{"shoe_text": "Bad opinion"}},
      "dialogue_quote": "Exact spoken line from transcript",
      "emotional_core": "Topic theme (e.g. Deep Focus, Victory, Bad Opinion)",
      "visceral_human_metaphor": "Exact contextual scene or meme description",
      "micro_prompts": [
        "focused professional writing on desk notes",
        "close up hands writing checklist with pen"
      ],
      "search_prompt": "focused person writing desk",
      "overlay_type": "cutaway",
      "narrative_reason": "Directly illustrates laser focus or humorous take spoken in the dialogue"
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
                    ),
                )
                raw_text = clean_json_string(response.text or "{}")
                plan_data = json.loads(raw_text)
                if plan_data and "shots" in plan_data and len(plan_data["shots"]) >= 2:
                    break
            except Exception as model_err:
                logger.warning(f"AI Director model {model_cand} failed: {model_err}. Trying next fallback...")
                continue

        if not plan_data or "shots" not in plan_data or not plan_data["shots"]:
            logger.warning("AI Director failed to produce valid plan. Falling back to heuristic plan.")
            return self._create_heuristic_plan(segments, video_duration)

        try:
            # Validate and clamp shot timestamps to video bounds and target ~60% duration
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
                if style not in ("stockpile", "collage", "meme"):
                    style = "stockpile"

                duration = min(max_dur, max(2.2, float(shot.get("duration", 3.2))))
                end = min(video_duration, start + duration)
                duration = round(end - start, 2)

                if duration < 1.5:
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
                        f"{base_prompt} detail",
                    ]

                shot_entry = {
                    "shot_id": shot.get("shot_id", f"broll_{len(clean_shots)+1}"),
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

            # Ensure at least 1 shot is a meme cutaway for viral retention and meme pack utilization
            has_meme = any(s.get("style") == "meme" for s in clean_shots)
            if not has_meme and clean_shots:
                target_idx = 1 if len(clean_shots) >= 2 else 0
                target_shot = clean_shots[target_idx]
                target_shot["style"] = "meme"
                diag = target_shot.get("dialogue_quote", "").strip()
                diag_lower = diag.lower()
                
                # Prioritize familiar creator faces over generic stock footages
                if any(w in diag_lower for w in ["speed", "crazy", "insane", "screaming", "shouting", "hype", "unbelievable", "huge", "bark", "omg"]):
                    target_shot["meme_template"] = "ishowspeed_shock"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "IShowSpeed Moment"}
                elif any(w in diag_lower for w in ["rage", "angry", "mad", "stupid", "dumb", "hate", "ban", "fail", "heavy", "terrible", "worst"]):
                    target_shot["meme_template"] = "caseoh_rage"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "CaseOh Rage"}
                elif any(w in diag_lower for w in ["controller", "game", "gaming", "disbelief", "aim", "bro", "no way", "jynx", "jynxzi", "clutch"]):
                    target_shot["meme_template"] = "jynxzi_freakout"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "Jynxzi Freakout"}
                elif any(w in diag_lower for w in ["doctor", "specialist", "expert", "hospital", "patient", "nurse", "surgery", "experienced"]):
                    target_shot["meme_template"] = "the_trusted_doctor"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "The Most Experienced Specialist"}
                elif any(w in diag_lower for w in ["chad", "sigma", "winner", "grind", "discipline", "hard work"]):
                    target_shot["meme_template"] = "gigachad"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "Average Consistency Enjoyer"}
                elif any(w in diag_lower for w in ["pain", "awkward", "fine", "smile", "pretend", "strained"]):
                    target_shot["meme_template"] = "hide_the_pain_harold"
                    target_shot["meme_captions"] = {"caption": diag[:45] if diag else "Smiling Through The Pain"}
                elif any(w in diag_lower for w in ["person", "meet", "talk", "real", "truth", "good", "better", "shake", "dinner"]):
                    target_shot["meme_template"] = "drake"
                    target_shot["meme_captions"] = {
                        "top_text": "15-minute Zoom interview",
                        "bottom_text": diag[:45] if diag else "Meet in person & have dinner"
                    }
                else:
                    target_shot["meme_template"] = "ishowspeed_shock"
                    target_shot["meme_captions"] = {
                        "caption": diag[:45] if diag else "High Retention Reaction"
                    }
                logger.info(f"Auto-injected meme cutaway on [{target_shot['shot_id']}] ({target_shot['meme_template']}) for viral retention.")

            total_broll_time = sum(s["duration"] for s in clean_shots)
            coverage_pct = round((total_broll_time / video_duration) * 100, 1) if video_duration > 0 else 0

            # 1. Expand shots if coverage is below 58%
            if coverage_pct < 58.0 and clean_shots:
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

            # 2. If still below 55% and there is an uncovered window at the end or in a wide gap, add a contextual shot
            if coverage_pct < 56.0 and segments:
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

            plan_result = {
                "total_duration": video_duration,
                "broll_shot_count": len(clean_shots),
                "broll_coverage_seconds": round(total_broll_time, 2),
                "broll_coverage_percentage": coverage_pct,
                "summary": plan_data.get("summary", "Contextual B-Roll Edit Plan"),
                "shots": clean_shots,
            }

            logger.info(f"AI Director planned {len(clean_shots)} B-roll cutaways covering {total_broll_time:.1f}s ({coverage_pct}% of {video_duration:.1f}s)")
            return plan_result


        except Exception as e:
            logger.error(f"AI Director planning post-processing failed: {e}", exc_info=True)
            return self._create_heuristic_plan(segments, video_duration)

    def _create_heuristic_plan(self, segments: List[Dict[str, Any]], video_duration: float) -> Dict[str, Any]:
        """Deterministic fallback edit plan ensuring ~60% B-roll coverage and contextual keywords."""
        shots = []
        target_broll_dur = video_duration * Config.TARGET_BROLL_RATIO
        shot_dur = 3.0
        num_shots = max(2, int(round(target_broll_dur / shot_dur)))

        # Distribute shots across available segments
        step = max(1, len(segments) // (num_shots + 1))
        chosen_indices = [min(len(segments) - 1, (i + 1) * step) for i in range(num_shots)]
        chosen_indices = sorted(list(set(chosen_indices)))

        last_end = 1.0  # leave 1.0s speaker hook

        for idx in chosen_indices:
            seg = segments[idx]
            start = max(last_end + 0.5, seg["start"])
            if start >= video_duration - 1.5:
                break

            dur = min(3.8, max(2.5, seg.get("duration", 3.0)))
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
                f"{search_prompt} workflow",
            ]

            # In heuristic plan, designate the 2nd shot as a viral meme cutaway
            is_meme = (len(shots) == 1)
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
                "narrative_reason": f"Contextual illustration of: {seg_text[:40]}",
            }
            if is_meme:
                seg_lower = seg_text.lower()
                if any(w in seg_lower for w in ["speed", "crazy", "insane", "screaming", "shouting", "hype", "bark", "omg", "huge"]):
                    shot_data["meme_template"] = "ishowspeed_shock"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "IShowSpeed Moment"}
                elif any(w in seg_lower for w in ["rage", "angry", "mad", "stupid", "dumb", "hate", "ban", "fail", "heavy"]):
                    shot_data["meme_template"] = "caseoh_rage"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "CaseOh Rage"}
                elif any(w in seg_lower for w in ["controller", "game", "gaming", "disbelief", "aim", "bro", "no way", "jynx", "jynxzi"]):
                    shot_data["meme_template"] = "jynxzi_freakout"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "Jynxzi Freakout"}
                elif any(w in seg_lower for w in ["doctor", "specialist", "expert", "hospital", "patient", "experienced"]):
                    shot_data["meme_template"] = "the_trusted_doctor"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "The Experienced Specialist"}
                elif any(w in seg_lower for w in ["chad", "sigma", "winner", "grind", "discipline"]):
                    shot_data["meme_template"] = "gigachad"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "Average Consistency Enjoyer"}
                else:
                    shot_data["meme_template"] = "ishowspeed_shock"
                    shot_data["meme_captions"] = {"caption": seg.get("text", "")[:45] or "High Retention Creator Reaction"}

            shots.append(shot_data)
            last_end = end

        total_broll = sum(s["duration"] for s in shots)
        coverage_pct = round((total_broll / video_duration) * 100, 1) if video_duration > 0 else 0

        return {
            "total_duration": video_duration,
            "broll_shot_count": len(shots),
            "broll_coverage_seconds": round(total_broll, 2),
            "broll_coverage_percentage": coverage_pct,
            "summary": "Heuristic contextual edit plan (~60% coverage)",
            "shots": shots,
        }
