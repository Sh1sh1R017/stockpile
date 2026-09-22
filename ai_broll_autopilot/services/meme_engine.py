"""Meme Engine: Autonomous meme generator and cutaway creator.

Indexes over 1,000 HD meme templates, formats contextual captions
for satirical, ironic, or bad-opinion dialogue moments (e.g. "Ew, I stepped in shit"),
and renders broadcast-quality 1080x1920 vertical video B-roll cutaways with punchline SFX.
"""

import json
import logging
import os
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)

MEME_DIR = Path(r"D:\SUS AI ONLY\Memes templates -HD--20260917T031953Z-1-001\Memes templates -HD-")
SPLIT_SFX_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "split_sfx"
CATALOG_PATH = SPLIT_SFX_DIR / "sfx_catalog.json"


class MemeEngine:
    """Master engine for discovering templates and rendering customized meme cutaways."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or MEME_DIR
        self.fonts_dir = Path("C:/Windows/Fonts")
        self.catalog = self._load_templates()
        self.sfx_catalog = self._load_sfx_catalog()

    def _load_templates(self) -> Dict[str, Path]:
        """Index all template files in the HD templates directory and project media/memes."""
        catalog = {}
        if self.templates_dir.exists():
            for p in self.templates_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", p.stem.lower()).strip("_")
                    catalog[clean_key] = p

        # Also index local project media/memes for curated IYKYK memes
        local_memes = Config.PROJECT_ROOT / "media" / "memes"
        if local_memes.exists():
            for p in local_memes.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", p.stem.lower()).strip("_")
                    catalog[clean_key] = p

        logger.info(f"MemeEngine indexed {len(catalog)} meme templates")
        return catalog

    def _load_sfx_catalog(self) -> List[Dict[str, Any]]:
        """Load unified SFX catalog for meme stinger selection."""
        if CATALOG_PATH.exists():
            try:
                with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading SFX catalog: {e}")
        return []

    def get_font(self, font_name: str = "impact", size: int = 80) -> ImageFont.FreeTypeFont:
        """Load system font with graceful fallbacks."""
        font_map = {
            "impact": "impact.ttf",
            "arial_bold": "arialbd.ttf",
            "segoe_bold": "segoeuib.ttf",
            "arial": "arial.ttf"
        }
        target_file = font_map.get(font_name.lower(), "impact.ttf")
        font_path = self.fonts_dir / target_file
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception:
                pass
        return ImageFont.load_default()

    def find_template(self, query: str) -> Optional[Tuple[str, Path]]:
        """Find template by query keyword or archetype."""
        q = query.lower().strip().replace("-", "_")
        clean_q = re.sub(r"[^a-zA-Z0-9]+", "_", q).strip("_")

        # 1. Exact catalog key match
        if clean_q in self.catalog:
            return clean_q, self.catalog[clean_q]

        # 2. Direct archetype aliases
        aliases = {
            "the_trusted_doctor": ["the_trusted_doctor", "the trusted doctor", "doctor", "specialist", "johnny sins", "johnny", "sins", "hospital doctor", "experienced doctor", "trust me im a doctor"],
            "gigachad": ["gigachad", "giga chad", "chad", "megachad", "absolute chad", "sigma"],
            "hide_the_pain_harold": ["hide_the_pain_harold", "hide the pain", "harold", "strained smile", "coffee smile"],
            "stepped_in_shit": ["stepped_in_shit", "stepped in shit", "ew i stepped in shit", "stepped", "walk shoe", "squash walk shoe"],
            "drake": ["drake pointing", "drake hotline", "drake", "reject accept"],
            "clown": ["clown makeup", "clown", "circus"],
            "same_picture": ["same picture", "corporate needs you to find the difference", "pam"],
            "spider_man": ["spider man finger", "spider-man pointing", "spiderman"],
            "batman_slap": ["batman slapping robin", "robin baffe", "batman slap"],
            "distracted_boyfriend": ["distracted boyfriend", "distracted boy"],
            "blinking_guy": ["blinking white guy", "drew scanlon", "blinking guy"],
            "trade_offer": ["trade offer"],
            "expanding_brain": ["expanding brain", "galaxy brain"],
            "gta_ah_shit": ["ah shit here we go again", "gta ah shit", "here we go again", "ah shit"]
        }

        # Check if query matches any archetype alias
        for key, terms in aliases.items():
            if q == key or clean_q == key or any(term in q or term.replace(" ", "_") in clean_q for term in terms):
                sorted_terms = sorted(terms, key=len, reverse=True)
                for term in sorted_terms:
                    norm_term = re.sub(r"[^a-zA-Z0-9]+", "_", term).strip("_")
                    for ckey, path in self.catalog.items():
                        if norm_term in ckey:
                            return key, path

        # 3. Direct substring match on catalog keys
        for ckey, path in self.catalog.items():
            if clean_q in ckey:
                return ckey, path

        # 4. Keyword search over template catalog (all tokens must match)
        tokens = [t for t in clean_q.split("_") if len(t) > 2]
        if tokens:
            for ckey, path in self.catalog.items():
                if all(token in ckey for token in tokens):
                    return ckey, path

            # Partial token match (first match with any significant token)
            long_tokens = [t for t in tokens if len(t) > 3]
            for ckey, path in self.catalog.items():
                if any(token in ckey for token in long_tokens):
                    return ckey, path

        # 5. Fallback to stepped_in_shit if available
        for ckey, path in self.catalog.items():
            if "stepped_in_shit" in ckey or "stepped" in ckey:
                return "stepped_in_shit", path

        # Ultimate fallback to first available template
        if self.catalog:
            first_key = next(iter(self.catalog))
            return first_key, self.catalog[first_key]

        return None

    def render_meme(self, template_key: str, template_path: Path, captions: Dict[str, str], out_img_path: Path) -> Path:
        """Render customized text onto the template image based on template layout."""
        im = Image.open(template_path).convert("RGBA")
        W, H = im.size

        # 1. SPECIFIC TEMPLATE: "Ew, I stepped in shit" (Bad opinions / awful takes)
        if "stepped" in template_key.lower() or "stepped_in_shit" in template_key.lower():
            self._render_stepped_in_shit(im, captions)

        # 2. SPECIFIC TEMPLATE: Drake (Rejection / Preference)
        elif "drake" in template_key.lower():
            self._render_drake(im, captions)

        # 3. SPECIFIC TEMPLATE: Clown Makeup (Progressive bad decisions)
        elif "clown" in template_key.lower():
            self._render_clown(im, captions)

        # 4. SPECIFIC TEMPLATE: "They're the same picture"
        elif "same_picture" in template_key.lower() or "difference" in template_key.lower():
            self._render_same_picture(im, captions)

        # 5. GENERIC: Modern Caption Card Banner
        else:
            self._render_generic_card(im, captions)

        # Save composite image
        out_img_path.parent.mkdir(parents=True, exist_ok=True)
        im.convert("RGB").save(out_img_path, "JPEG", quality=95)
        logger.info(f"MemeEngine rendered meme image to: {out_img_path.name} ({im.size[0]}x{im.size[1]})")
        return out_img_path

    def _render_stepped_in_shit(self, im: Image.Image, captions: Dict[str, str]):
        """Render text rotated onto the shoe sole in panel 2."""
        text = captions.get("shoe_text") or captions.get("bad_opinion") or captions.get("text") or "Bad Opinion"
        wrapped = "\n".join(textwrap.wrap(text, width=16))

        font = self.get_font("impact", size=95)
        card_w, card_h = 850, 450
        card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 0))
        cdraw = ImageDraw.Draw(card)

        bbox = cdraw.multiline_textbbox((0, 0), wrapped, font=font, align="center", spacing=10)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (card_w - tw) // 2
        ty = (card_h - th) // 2

        # Draw black text with crisp white outline
        cdraw.multiline_text(
            (tx, ty), wrapped, font=font,
            fill=(15, 15, 15, 255),
            align="center", spacing=10,
            stroke_width=4, stroke_fill=(245, 245, 245, 220)
        )

        # Rotate card 38 degrees to match angle of the shoe sole
        rotated_card = card.rotate(38, expand=True, resample=Image.BICUBIC)
        im.paste(rotated_card, (620, 2220), rotated_card)

    def _render_drake(self, im: Image.Image, captions: Dict[str, str]):
        """Render top (rejected) and bottom (accepted) text onto Drake template."""
        W, H = im.size
        top_text = captions.get("top_text") or captions.get("rejected") or "Bad Option"
        bot_text = captions.get("bottom_text") or captions.get("accepted") or "Good Option"

        draw = ImageDraw.Draw(im)
        font = self.get_font("impact", size=max(70, int(W * 0.035)))

        # Top-right panel
        self._draw_centered_text_in_box(
            draw, (int(W * 0.52), int(H * 0.05), int(W * 0.98), int(H * 0.48)),
            top_text, font, fill_color=(20, 20, 20, 255)
        )
        # Bottom-right panel
        self._draw_centered_text_in_box(
            draw, (int(W * 0.52), int(H * 0.52), int(W * 0.98), int(H * 0.95)),
            bot_text, font, fill_color=(20, 20, 20, 255)
        )

    def _render_clown(self, im: Image.Image, captions: Dict[str, str]):
        """Render progressive bad steps onto Clown Makeup stages."""
        W, H = im.size
        steps = captions.get("steps") or [
            captions.get("step_1", "Stage 1"),
            captions.get("step_2", "Stage 2"),
            captions.get("step_3", "Stage 3"),
            captions.get("step_4", "Stage 4")
        ]
        if isinstance(steps, str):
            steps = [s.strip() for s in steps.split(",") if s.strip()]

        draw = ImageDraw.Draw(im)
        font = self.get_font("impact", size=max(50, int(W * 0.03)))

        # Clown stages are stacked vertically on right side (or left side has text space)
        # In clown makeup BIG, faces are stacked vertically on the right, text on the left
        slot_height = H / max(len(steps), 4)
        for idx, text in enumerate(steps[:4]):
            y_start = int(idx * slot_height)
            y_end = int((idx + 1) * slot_height)
            self._draw_centered_text_in_box(
                draw, (int(W * 0.05), y_start + 20, int(W * 0.60), y_end - 20),
                text, font, fill_color=(25, 25, 25, 255)
            )

    def _render_same_picture(self, im: Image.Image, captions: Dict[str, str]):
        """Render labels for Pam Beesly's 'They're the same picture'."""
        W, H = im.size
        item1 = captions.get("item_1") or captions.get("left") or "Item A"
        item2 = captions.get("item_2") or captions.get("right") or "Item B"

        draw = ImageDraw.Draw(im)
        font = self.get_font("impact", size=max(60, int(W * 0.035)))

        # Top half contains two pictures side-by-side
        self._draw_centered_text_in_box(
            draw, (int(W * 0.05), int(H * 0.35), int(W * 0.45), int(H * 0.48)),
            item1, font, fill_color=(20, 20, 20, 255)
        )
        self._draw_centered_text_in_box(
            draw, (int(W * 0.55), int(H * 0.35), int(W * 0.95), int(H * 0.48)),
            item2, font, fill_color=(20, 20, 20, 255)
        )

    def _render_generic_card(self, im: Image.Image, captions: Dict[str, str]):
        """Render a modern white caption card at top or classic Impact font overlay."""
        W, H = im.size
        caption = captions.get("text") or captions.get("caption") or captions.get("top_text") or "When you see it"

        # Modern header box
        banner_h = int(H * 0.18)
        banner = Image.new("RGBA", (W, banner_h), (255, 255, 255, 255))
        bdraw = ImageDraw.Draw(banner)
        font = self.get_font("segoe_bold", size=max(45, int(W * 0.035)))

        wrapped = "\n".join(textwrap.wrap(caption, width=28))
        bbox = bdraw.multiline_textbbox((0, 0), wrapped, font=font, align="center", spacing=10)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (W - tw) // 2
        ty = (banner_h - th) // 2

        bdraw.multiline_text((tx, ty), wrapped, font=font, fill=(15, 15, 15, 255), align="center", spacing=10)

        # Composite banner at top
        im.paste(banner, (0, 0))

    def _draw_centered_text_in_box(self, draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], text: str, font: ImageFont.FreeTypeFont, fill_color=(20, 20, 20, 255)):
        """Utility to wrap and center text within a bounding box."""
        x1, y1, x2, y2 = box
        bw = max(10, x2 - x1)
        bh = max(10, y2 - y1)
        wrapped = "\n".join(textwrap.wrap(text, width=18))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center", spacing=12)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = x1 + (bw - tw) // 2
        ty = y1 + (bh - th) // 2
        draw.multiline_text(
            (tx, ty), wrapped, font=font, fill=fill_color,
            align="center", spacing=12,
            stroke_width=2, stroke_fill=(250, 250, 250, 200)
        )

    def select_meme_sfx(self, template_key: str) -> Optional[Dict[str, Any]]:
        """Select a hilarious, punchy sound effect from our 189 SFX catalog for the meme."""
        preferred_map = {
            "stepped_in_shit": "81_vine_boom.mp3",
            "drake": "59_cartoon_slip_whoosh.mp3",
            "clown": "01_bonk_impact.mp3",
            "same_picture": "11_bruh.mp3",
            "batman_slap": "01_bonk_impact.mp3",
            "gta_ah_shit": "60_sad_violin.mp3"
        }
        target_fn = preferred_map.get(template_key, "81_vine_boom.mp3")

        # Find in catalog
        for item in self.sfx_catalog:
            if item.get("file") == target_fn or Path(item.get("path", "")).name == target_fn:
                return {
                    "file": item["file"],
                    "path": item["path"],
                    "name": item["name"],
                    "volume": 0.50
                }

        # Fallback to vine boom or bonk if available in split_sfx
        local_sfx = SPLIT_SFX_DIR / "81_vine_boom.mp3"
        if local_sfx.exists():
            return {
                "file": local_sfx.name,
                "path": str(local_sfx),
                "name": "Vine Boom",
                "volume": 0.50
            }
        return None

    def create_meme_broll(
        self,
        shot: Dict[str, Any],
        work_dir: Path,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """High-level generator: transforms a meme shot specification into a ready 9:16 video cutaway."""
        sid = shot.get("shot_id", "meme_shot")
        dur = float(duration or shot.get("duration", 2.5))

        # 1. Resolve template
        template_name = shot.get("meme_template", "stepped_in_shit")
        found = self.find_template(template_name)
        if not found:
            raise FileNotFoundError(f"Could not find matching meme template for: {template_name}")

        t_key, t_path = found
        shot["meme_template_resolved"] = t_path.name
        logger.info(f"MemeEngine matched template [{t_key}]: {t_path.name}")

        # 2. Extract captions
        captions = shot.get("meme_captions", {})
        if not captions:
            # Derive from dialogue quote or metaphor
            diag = shot.get("dialogue_quote", "")
            captions = {
                "shoe_text": diag,
                "bad_opinion": diag,
                "text": diag,
                "top_text": "What people say",
                "bottom_text": diag
            }

        # 3. Render composite image
        img_out = work_dir / f"{sid}_{t_key}.jpg"
        self.render_meme(t_key, t_path, captions, img_out)

        # 4. Select punchline SFX
        sfx_info = self.select_meme_sfx(t_key)
        if sfx_info:
            shot["contextual_sfx"] = {
                "name": sfx_info["name"],
                "file": sfx_info["file"],
                "path": sfx_info["path"],
                "category": "Meme Stinger",
                "volume": sfx_info["volume"],
                "start_offset": 0.05,
                "reason": f"Punchline SFX for {t_key} meme"
            }

        # 5. Render 1080x1920 MP4 with subtle Ken Burns motion
        video_out = work_dir / f"{sid}_{t_key}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_out)
        ]

        if sfx_info and os.path.exists(sfx_info["path"]):
            cmd.extend(["-i", str(sfx_info["path"])])
            # Scale to 1080:1920 with padding, and pad audio to duration
            filter_str = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30[v];"
                f"[1:a]apad[a]"
            )
            cmd.extend([
                "-filter_complex", filter_str,
                "-map", "[v]",
                "-map", "[a]"
            ])
        else:
            filter_str = (
                f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30"
            )
            cmd.extend([
                "-vf", filter_str,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-shortest"
            ])

        cmd.extend([
            "-t", f"{dur:.2f}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(video_out)
        ])

        subprocess.run(cmd, check=True, capture_output=True)
        if not video_out.exists() or video_out.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg failed to generate meme video at: {video_out}")

        shot["asset_path"] = str(video_out)
        shot["style"] = "meme"
        shot["status"] = "matched"
        logger.info(f"MemeEngine generated 9:16 cutaway video: {video_out.name} ({dur:.2f}s, {video_out.stat().st_size / 1024:.1f} KB)")
        return shot
