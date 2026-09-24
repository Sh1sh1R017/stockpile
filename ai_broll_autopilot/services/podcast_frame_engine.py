"""Podcast Frame Engine generating authentic torn-paper framing, duotone hook headers,
and safe-zone watermarking matching the Curious Mike / MPJ benchmark.
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageFont, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

WHITE = (255, 255, 255, 255)
YELLOW = (254, 230, 20, 255)   # Canary yellow #FEE614
PINK = (255, 0, 85, 255)       # Hot pink / Magenta #FF0055

KNOWN_ENTITIES = {
    "trae", "trae's", "trae young", "mpj", "mpj's", "knicks", "knicks fans", "nba",
    "jokic", "wemby", "kawhi", "dillon brooks", "pat bev", "tatum",
    "booker", "ant", "sga", "curry", "luka", "lebron", "giannis",
    "collin", "sexton", "jaylen", "hands",
    "aau", "mokan", "team usa", "hawks", "clippers", "nuggets", "new york"
}

DRAMA_KEYWORDS = {
    "rivalry", "rivalry.", "regular guy", "regular guy.", "roommates",
    "roommates.", "argument", "fight", "beef", "benched", "punishment",
    "ranked", "ranking", "rankings", "high school", "school", "cut", "lock", "disrespect", "superteam", "foul-baiting",
    "started", "quit", "insane", "crazy", "truth", "personal"
}


def find_font(font_size: int = 52, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Find the best available bold sans font on the system."""
    candidates = []
    if italic:
        candidates = [
            "C:/Windows/Fonts/ariblk.ttf",
            "assets/fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/arialbi.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/ariblk.ttf",
            "assets/fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/impact.ttf"
        ]

    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(str(p), size=font_size)
            except Exception:
                continue

    return ImageFont.load_default()


class PodcastFrameEngine:
    """Generates composite framing overlays with authentic torn paper edges,
    2-line duotone hook titles, and burned-in podcast watermarks."""

    def __init__(self, template_path: Optional[str] = None):
        default_tpl = (
            Path(__file__).resolve().parent.parent.parent
            / "assets" / "campaigns" / "curious_mike" / "curious_mike_torn_paper_frame.png"
        )
        self.template_path = Path(template_path) if template_path else default_tpl

    def format_hook_lines(self, hook_text: str) -> Tuple[str, str]:
        """Split a hook into two balanced lines for header display."""
        clean = hook_text.strip()
        if "\n" in clean:
            parts = [line.strip() for line in clean.split("\n") if line.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]

        if not clean.endswith((".", "?", "!")):
            clean += "?" if any(clean.lower().startswith(q) for q in ["who", "what", "why", "how", "where", "is", "does"]) else "."

        words = clean.split()
        if len(words) <= 4:
            return clean, ""

        # Midpoint split
        mid = len(words) // 2
        # Try to balance character lengths
        best_split = mid
        min_diff = 999
        for i in range(max(1, mid - 1), min(len(words), mid + 2)):
            l1 = " ".join(words[:i])
            l2 = " ".join(words[i:])
            diff = abs(len(l1) - len(l2))
            if diff < min_diff:
                min_diff = diff
                best_split = i

        return " ".join(words[:best_split]), " ".join(words[best_split:])

    def render_duotone_line(
        self,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        text: str,
        start_x: int,
        start_y: int,
        is_second_line: bool = False
    ):
        """Render a single line with smart keyword color-coding."""
        words = text.split()
        current_x = start_x
        is_all_caps = text.isupper()

        for idx, w in enumerate(words):
            clean_w = re.sub(r"[^\w\s']", "", w.lower()).strip()
            next_clean = re.sub(r"[^\w\s']", "", words[idx+1].lower()).strip() if idx < len(words) - 1 else ""
            prev_clean = re.sub(r"[^\w\s']", "", words[idx-1].lower()).strip() if idx > 0 else ""
            two_word_fwd = f"{clean_w} {next_clean}" if next_clean else ""
            two_word_back = f"{prev_clean} {clean_w}" if prev_clean else ""

            # Color decision
            color = WHITE
            if clean_w in KNOWN_ENTITIES or (two_word_fwd and two_word_fwd in KNOWN_ENTITIES) or (two_word_back and two_word_back in KNOWN_ENTITIES):
                color = YELLOW
            elif clean_w in DRAMA_KEYWORDS or (two_word_fwd and two_word_fwd in DRAMA_KEYWORDS) or (two_word_back and two_word_back in DRAMA_KEYWORDS) or (is_second_line and idx >= len(words) - 2 and clean_w not in {"in", "on", "at", "the", "a"}):
                # The climax words on line 2 (e.g. HIGH SCHOOL?) are Hot Pink
                color = PINK

            # Typography casing matching Curious Mike benchmark:
            # - Pink climax words are always UPPERCASE (e.g. HIGH SCHOOL?, RIVALRY., GUY.)
            # - Entities are Title Case (or UPPERCASE for acronyms like MPJ, NBA)
            # - Neutral words are Mixed Case / Sentence case
            punct_match = re.search(r"([^\w\s']+)$", w)
            punct = punct_match.group(1) if punct_match else ""
            stem = w[:-len(punct)] if punct else w

            if color == PINK:
                display_word = stem.upper() + punct
            elif color == YELLOW:
                if clean_w in {"mpj", "nba", "aau", "sga", "usa"}:
                    display_word = stem.upper() + punct
                else:
                    display_word = stem.title() + punct
            else:
                if idx == 0 and not is_second_line:
                    display_word = stem.capitalize() + punct
                else:
                    display_word = stem.lower() + punct

            w_with_space = display_word + (" " if idx < len(words) - 1 else "")

            # Render word
            draw.text((current_x, start_y), w_with_space, font=font, fill=color)
            bbox = font.getbbox(w_with_space)
            current_x += (bbox[2] - bbox[0])

    def generate_frame_overlay(
        self,
        hook_text: str,
        output_path: Path,
        watermark_text: str = "YT: @mpj"
    ) -> Path:
        """Create a complete composite 1080x1920 overlay PNG."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.template_path.exists():
            raise FileNotFoundError(f"Torn paper template not found at: {self.template_path}")

        frame = Image.open(self.template_path).convert("RGBA")
        draw = ImageDraw.Draw(frame)

        # 1. Render Hook Header
        if hook_text and hook_text.strip():
            font = find_font(font_size=52, italic=False)
            line1, line2 = self.format_hook_lines(hook_text)

            x_start = 55
            y_line1 = 225
            y_line2 = 295

            self.render_duotone_line(draw, font, line1, x_start, y_line1, is_second_line=False)
            if line2:
                self.render_duotone_line(draw, font, line2, x_start, y_line2, is_second_line=True)

        # 2. Render Watermark at Bottom
        if watermark_text and watermark_text.strip():
            wm_font = find_font(font_size=42, italic=True)
            bbox = wm_font.getbbox(watermark_text)
            wm_w = bbox[2] - bbox[0]
            wm_x = (1080 - wm_w) // 2
            wm_y = 1575

            # Shadow layer
            shadow = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(shadow)
            s_draw.text((wm_x + 3, wm_y + 3), watermark_text, font=wm_font, fill=(0, 0, 0, 180))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
            frame = Image.alpha_composite(frame, shadow)

            draw = ImageDraw.Draw(frame)
            draw.text((wm_x, wm_y), watermark_text, font=wm_font, fill=WHITE)

        frame.save(output_path, "PNG")
        logger.info(f"Generated podcast frame overlay at: {output_path}")
        return output_path
