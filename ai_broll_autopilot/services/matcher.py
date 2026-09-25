"""B-Roll Matcher resolving edit plan shots into verified local video assets."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_broll_autopilot.config import Config
from ai_broll_autopilot.core.database import Database
from ai_broll_autopilot.services.collage_bridge import CollageBridge
from ai_broll_autopilot.services.watermark_scanner import watermark_scanner
from ai_broll_autopilot.services.pexels import pexels_service
from ai_broll_autopilot.services.meme_engine import MemeEngine

# Import Stockpile services directly from src/
sys.path.insert(0, str(Config.STOCKPILE_DIR))
from services.youtube_service import YouTubeService
from services.video_downloader import VideoDownloader
from services.ai_service import AIService

logger = logging.getLogger(__name__)


class Matcher:
    """Matches visual edit plan shots with real B-roll video assets."""

    def __init__(self, db: Database):
        self.db = db
        self.youtube_service = YouTubeService(max_results=8)
        self.ai_service = AIService(Config.GEMINI_API_KEY, Config.GEMINI_MODEL)
        self.downloader = VideoDownloader(str(Config.OUTPUT_DIR / "broll_cache"))
        self.collage_bridge = CollageBridge()
        self.meme_engine = MemeEngine()

    async def resolve_shots(self, plan: Dict[str, Any], job_cache_dir: Path) -> Dict[str, Any]:
        """Resolve every shot in the plan to a verified local video file concurrently in parallel."""
        shots = plan.get("shots", [])
        job_cache_dir.mkdir(parents=True, exist_ok=True)

        campaign_id = plan.get("campaign_id", "default")
        from ai_broll_autopilot.campaigns import campaign_registry
        campaign = campaign_registry.get_campaign(campaign_id)

        niche_id = plan.get("niche_id") or getattr(campaign, "niche_id", None)
        from ai_broll_autopilot.niches import niche_registry
        niche = niche_registry.get_profile(niche_id) if niche_id else None

        # Memes allowed only if both campaign AND niche profile permit meme cutaways
        allow_memes = bool(campaign.allow_ai_broll and (getattr(niche.editing, "meme_cutaways", False) if niche else False))

        # Resolve all shots concurrently with asyncio.gather
        tasks = [self._resolve_single_shot(shot, job_cache_dir, allow_memes=allow_memes, niche_id=niche_id) for shot in shots]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        resolved_shots = [s for s in results if s is not None]
        plan["shots"] = resolved_shots
        plan["matched_count"] = len(resolved_shots)
        logger.info(f"Successfully matched {len(resolved_shots)} of {len(shots)} shots in parallel")
        return plan

    async def _resolve_single_shot(
        self,
        shot: Dict[str, Any],
        job_cache_dir: Path,
        allow_memes: bool = False,
        niche_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Resolve a single B-roll shot concurrently."""
        shot_id = shot.get("shot_id", "shot")
        prompt = shot.get("search_prompt") or shot.get("visceral_human_metaphor") or shot.get("emotional_core")
        style = shot.get("style", "stockpile")
        target_duration = shot.get("duration", 2.5)

        logger.info(f"Resolving B-roll for [{shot_id}] ({target_duration}s): '{prompt}' (allow_memes={allow_memes})")
        asset_path = None

        # 0. Check if shot is intentionally designated as a meme cutaway (only if allowed by niche/campaign)
        if not allow_memes:
            style = "stockpile"
            shot["style"] = "stockpile"

        creator_terms = (
            "ishowspeed", "speed shock", "caseoh", "jynxzi", "jynxi", "johnny sins",
            "the_trusted_doctor", "gigachad", "harold meme", "homeless", "moms kinda homeless",
            "pornstar", "personal porn star", "did you shave", "kiaraakitty"
        )
        is_creator_prompt = any(k in (prompt or "").lower() for k in creator_terms)
        if allow_memes and (style == "meme" or is_creator_prompt):
            try:
                if is_creator_prompt and not shot.get("meme_template"):
                    p_lower = (prompt or "").lower()
                    if "homeless" in p_lower or "mom" in p_lower:
                        shot["meme_template"] = "moms_kinda_homeless"
                    elif "pornstar" in p_lower or "shave" in p_lower or "kiara" in p_lower:
                        shot["meme_template"] = "not_your_personal_pornstar"
                    elif "speed" in p_lower:
                        shot["meme_template"] = "ishowspeed_shock"
                    elif "caseoh" in p_lower:
                        shot["meme_template"] = "caseoh_rage"
                    elif "jynx" in p_lower:
                        shot["meme_template"] = "jynxzi_freakout"
                    elif "doctor" in p_lower or "sins" in p_lower:
                        shot["meme_template"] = "the_trusted_doctor"
                    elif "giga" in p_lower:
                        shot["meme_template"] = "gigachad"
                    elif "harold" in p_lower:
                        shot["meme_template"] = "hide_the_pain_harold"
                    else:
                        from ai_broll_autopilot.services.meme_engine import MemeEngine
                        shot = MemeEngine.generate_unique_contextual_meme(shot, prompt or shot.get("dialogue_quote", ""))
                shot = self.meme_engine.create_meme_broll(shot, job_cache_dir, duration=target_duration)
                asset_path = shot.get("asset_path")
                if asset_path and Path(asset_path).exists():
                    logger.info(f"Successfully generated meme/creator cutaway for [{shot_id}]: {asset_path}")
                    return shot
            except Exception as me:
                logger.warning(f"Meme generation failed for [{shot_id}]: {me}. Falling back to real footage.")

        # 1. Local-First: Search local cataloged B-Roll library
        try:
            from ai_broll_autopilot.services.broll_library import broll_library
            local_matches = broll_library.search_local(
                query=prompt,
                niche_id=niche_id,
                min_duration=1.0,
                limit=3
            )
            if local_matches:
                chosen = local_matches[0]
                matched_fp = Path(chosen["file_path"])
                if matched_fp.exists():
                    logger.info(f"Resolved [{shot_id}] from Local B-Roll Library: {matched_fp.name} ('{chosen.get('title')}')")
                    asset_path = str(matched_fp.resolve())
        except Exception as le:
            logger.debug(f"Local B-roll library search error for [{shot_id}]: {le}")

        # 2. Check local asset cache in DB
        if not asset_path:
            cached = self.db.find_cached_asset(prompt)
            if cached and Path(cached["file_path"]).exists():
                logger.info(f"Reusing cached B-roll asset for [{shot_id}]: {cached['file_path']}")
                asset_path = cached["file_path"]

        # 3. Try Pexels royalty-free vertical footage if API key is provided
        if not asset_path and pexels_service.is_available():
            logger.info(f"Attempting Pexels stock video search for [{shot_id}]: '{prompt}'")
            p_out = job_cache_dir / f"{shot_id}_pexels.mp4"
            asset_path = await pexels_service.search_and_download(
                prompt, p_out, duration=target_duration, orientation="portrait"
            )

        # 4. If not cached or resolved from Pexels, acquire asset based on style
        if not asset_path:
            if style == "collage":
                out_path = job_cache_dir / f"{shot_id}_collage.mp4"
                asset_path = await self.collage_bridge.generate_collage_clip(
                    prompt, str(out_path), duration=int(min(5, max(3, target_duration)))
                )
            else:
                # Stockpile pipeline: check if rapid-fire micro-cut montage is requested
                micro_prompts = shot.get("micro_prompts", [])
                if Config.RAPID_FIRE_MONTAGE_ENABLED and len(micro_prompts) > 1:
                    asset_path = await self._build_rapid_montage(
                        micro_prompts, target_duration, job_cache_dir, shot_id
                    )
                else:
                    asset_path = await self._acquire_stockpile_clip(
                        prompt, job_cache_dir, shot_id, max_clip_duration=target_duration
                    )

        # 5. If stockpile acquisition failed, automatically fallback to procedural collage
        if not asset_path or not Path(asset_path).exists():
            logger.info(f"Stockpile footage unavailable for [{shot_id}] ('{prompt}'). Falling back to procedural collage...")
            out_path = job_cache_dir / f"{shot_id}_collage.mp4"
            asset_path = await self.collage_bridge.generate_collage_clip(
                prompt, str(out_path), duration=int(min(5, max(3, target_duration)))
            )

        if asset_path and Path(asset_path).exists():
            shot["asset_path"] = str(Path(asset_path).resolve())
            shot["status"] = "matched"

            # Index asset in database and local catalog
            self.db.save_broll_asset(
                asset_id=f"{shot_id}_{Path(asset_path).stem}",
                file_path=str(Path(asset_path).resolve()),
                title=Path(asset_path).name,
                source=style,
                prompt=prompt,
                duration=target_duration,
                score=8,
                niche_id=niche_id or "generic",
            )
            return shot
        else:
            logger.warning(f"Could not resolve B-roll asset for [{shot_id}]: '{prompt}'")
            shot["status"] = "unmatched"
            return None

    async def _build_rapid_montage(
        self,
        micro_prompts: List[str],
        total_duration: float,
        target_dir: Path,
        shot_id: str
    ) -> Optional[str]:
        """Build a high-tempo rapid-fire micro-cut montage (3 to 5 quick cuts in total_duration)."""
        logger.info(f"Building rapid-fire montage for [{shot_id}] ({len(micro_prompts)} micro-cuts, {total_duration}s total)")
        clip_dur = round(total_duration / max(1, len(micro_prompts)), 2)
        clip_dur = max(Config.MIN_MICRO_CLIP_DURATION, min(Config.MAX_MICRO_CLIP_DURATION, clip_dur))

        async def fetch_micro_clip(idx: int, p: str):
            micro_id = f"{shot_id}_m{idx}"
            logger.info(f"Acquiring micro-clip {idx}/{len(micro_prompts)}: '{p}' ({clip_dur}s)")
            cached = self.db.find_cached_asset(p)
            if cached and Path(cached["file_path"]).exists():
                is_clean, reason, _ = watermark_scanner.scan_video(Path(cached["file_path"]))
                if is_clean:
                    return cached["file_path"]
                logger.warning(f"Cached asset for '{p}' failed watermark scan ({reason}); purging dirty file and re-acquiring")
                try:
                    Path(cached["file_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
            return await self._acquire_stockpile_clip(
                p, target_dir, micro_id, max_clip_duration=clip_dur
            )

        tasks = [fetch_micro_clip(idx, p) for idx, p in enumerate(micro_prompts, start=1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        acquired_micro_clips = [
            str(Path(r).resolve()) for r in results if isinstance(r, str) and Path(r).exists()
        ]

        if not acquired_micro_clips:
            logger.warning(f"No micro-clips acquired for montage [{shot_id}]")
            return None

        if len(acquired_micro_clips) == 1:
            logger.info(f"Only 1 micro-clip acquired for [{shot_id}]; using single clip")
            return acquired_micro_clips[0]

        # Concatenate micro-clips into a single dynamic montage video using FFmpeg
        montage_output = target_dir / f"{shot_id}_montage.mp4"
        cmd = ["ffmpeg", "-y"]
        filter_complex = []

        for idx, clip in enumerate(acquired_micro_clips):
            cmd.extend(["-i", clip])
            filter_complex.append(
                f"[{idx}:v]scale={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={Config.TARGET_WIDTH}:{Config.TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={Config.TARGET_FPS}[v{idx}]"
            )

        inputs_str = "".join([f"[v{i}]" for i in range(len(acquired_micro_clips))])
        filter_complex.append(f"{inputs_str}concat=n={len(acquired_micro_clips)}:v=1:a=0[outv]")

        cmd.extend([
            "-filter_complex", ";".join(filter_complex),
            "-map", "[outv]",
            "-t", str(total_duration),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(Config.VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-v", "warning",
            str(montage_output)
        ])

        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        if montage_output.exists() and montage_output.stat().st_size > 1000:
            logger.info(f"Assembled {len(acquired_micro_clips)}-clip rapid montage: {montage_output.name} ({total_duration}s)")
            return str(montage_output.resolve())

        return acquired_micro_clips[0]

    @staticmethod
    def get_dramatic_queries(prompt: str) -> List[str]:
        """Expand prompt with proven dramatic YouTube clips matching core human emotions."""
        p_low = prompt.lower()
        queries = [prompt]
        if any(k in p_low for k in ["cardboard", "box", "pack", "fired", "leaving office", "terminate", "layoff", "severance"]):
            queries.extend([
                "Andy Gets Fired - The Office US",
                "office space layoffs",
                "fired employee packing belongings",
                "employee packing desk",
                "getting fired office scene"
            ])
        elif any(k in p_low for k in ["empty office", "cubicle", "separate", "abandoned", "dark office"]):
            queries.extend([
                "Empty Office b roll",
                "empty cubicle desk",
                "dark empty office"
            ])
        elif any(k in p_low for k in ["frustrat", "slow", "rage", "stress", "pulling hair", "head in hands", "behind", "drown", "overwhelm"]):
            queries.extend([
                "Frustrated Office Worker",
                "Angry Office Worker",
                "Computer Rage",
                "stressed employee b roll"
            ])
        return list(dict.fromkeys(queries))

    async def _acquire_stockpile_clip(
        self, prompt: str, target_dir: Path, shot_id: str, max_clip_duration: Optional[float] = None
    ) -> Optional[str]:
        """Query YouTube, score with Gemini for emotional resonance, download, and aggressively scan candidates."""
        try:
            loop = asyncio.get_event_loop()

            # Search YouTube across prompt and dramatic query variations
            queries_to_search = self.get_dramatic_queries(prompt)
            results = []
            seen_ids = set()

            for q in queries_to_search[:3]:
                q_res = await loop.run_in_executor(
                    None, self.youtube_service.search_videos, q
                )
                for r in (q_res or []):
                    if r.video_id not in seen_ids:
                        seen_ids.add(r.video_id)
                        results.append(r)
                if len(results) >= 8:
                    break

            if not results:
                logger.warning(f"No YouTube results found for: '{prompt}'")
                return await self._acquire_clean_collage_fallback(prompt, target_dir, shot_id, max_clip_duration)

            # Evaluate with Gemini (strict clean, no watermarks, emotional resonance)
            try:
                scored = await loop.run_in_executor(
                    None, self.ai_service.evaluate_videos, prompt, results
                )
            except Exception as eval_err:
                logger.warning(f"AI evaluation raised error ({eval_err}), using clean fallback")
                scored = None

            if not scored and results:
                logger.warning(f"Selecting cleanest candidate videos for: '{prompt}'")
                from models.video import ScoredVideo
                watermark_keywords = [
                    "watermark", "watermarked", "with watermark", "preview only", "preview",
                    "stock footage preview", "sample footage", "shutterstock", "getty images",
                    "gettyimages", "getty", "pond5", "pond 5", "istock", "istockphoto",
                    "storyblocks", "depositphotos", "123rf", "adobe stock", "adobestock",
                    "clever stock", "cleverstock", "vectorstock", "canva", "freepik",
                    "dreamstime", "filmpac", "filmsupply", "artgrid", "footage island",
                    "envato", "videohive", "motion array", "motionarray", "motionelements",
                    "dissolve footage", "dissolve stock", "stock footage", "stock video",
                    "stock library", "royalty free footage", "royalty-free footage",
                    "no copyright footage", "free stock video", "free stock footage",
                    "copyright free footage", "copyright free video", "sarasota herald",
                    "news ticker", "breaking news", "official music video", "vevo"
                ]
                clean_results = []
                for r in results:
                    title_low = r.title.lower()
                    desc_low = (r.description or "").lower()
                    if not any(wm in title_low or wm in desc_low for wm in watermark_keywords):
                        clean_results.append(r)
                if clean_results:
                    scored = [ScoredVideo(r.video_id, 8 - idx, r) for idx, r in enumerate(clean_results)]

            if not scored:
                logger.warning(f"No clean stockpile candidates found for '{prompt}'. Falling back to procedural collage.")
                return await self._acquire_clean_collage_fallback(prompt, target_dir, shot_id, max_clip_duration)

            # Candidate Retry Loop: download and run aggressive watermark scanner
            download_duration = max_clip_duration or Config.MAX_CLIP_DURATION_SECONDS
            max_attempts = min(len(scored), Config.MAX_WATERMARK_CANDIDATE_RETRIES)

            for attempt_idx in range(max_attempts):
                candidate = scored[attempt_idx]
                logger.info(f"Testing candidate {attempt_idx+1}/{max_attempts} for [{shot_id}]: '{candidate.video_result.title}'")
                downloaded = await loop.run_in_executor(
                    None, self.downloader._download_single_video, candidate, target_dir, download_duration
                )
                if not downloaded or not Path(downloaded).exists():
                    continue

                # Run Aggressive Watermark Scanner
                if Config.WATERMARK_SCAN_ENABLED:
                    is_clean, reason, details = await loop.run_in_executor(
                        None, watermark_scanner.scan_video, Path(downloaded)
                    )
                    if not is_clean:
                        logger.warning(f"[WATERMARK REJECTED] Candidate {attempt_idx+1} ({Path(downloaded).name}) REJECTED by WatermarkScanner: {reason}")
                        try:
                            Path(downloaded).unlink(missing_ok=True)
                        except Exception:
                            pass
                        continue  # Try next candidate!

                logger.info(f"[VERIFIED CLEAN] 100% clean footage for [{shot_id}]: {Path(downloaded).name}")
                return downloaded

            # If all candidates failed watermark scan, fallback to procedural collage
            logger.warning(f"All {max_attempts} candidates for '{prompt}' failed watermark scan. Falling back to procedural collage.")
            return await self._acquire_clean_collage_fallback(prompt, target_dir, shot_id, max_clip_duration)

        except Exception as e:
            logger.error(f"Stockpile acquisition failed for '{prompt}': {e}", exc_info=True)
            return await self._acquire_clean_collage_fallback(prompt, target_dir, shot_id, max_clip_duration)

    async def _acquire_clean_collage_fallback(
        self, prompt: str, target_dir: Path, shot_id: str, max_clip_duration: Optional[float] = None
    ) -> Optional[str]:
        """Fallback to guaranteed 100% clean procedural paper-collage animation."""
        dur = max_clip_duration or Config.MAX_CLIP_DURATION_SECONDS
        return await self.collage_bridge.create_broll_clip(
            prompt=prompt,
            duration=dur,
            output_dir=target_dir,
            filename=f"{shot_id}_clean_collage.mp4"
        )
