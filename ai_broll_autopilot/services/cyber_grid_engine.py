"""Cyber Grid Before/After Layout Engine.

Replicates the viral CapCut Before & After showcase editing style:
- Deep forest green radial gradient vignette canvas (1080x1920)
- Neon green cyber grid lines
- Floating Left card: "BEFORE" (raw footage, standard color, 352x600, rounded corners)
- Floating Right card: "AFTER" (punch-in zoom, vibrant color grading, cutaway B-roll overlays, 600x1060, rounded corners)
- Bold neon cyan headers ("BEFORE" and "AFTER")
- Kinetic cyan / golden amber / white typography centered inside the AFTER card.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

logger = logging.getLogger(__name__)


class CyberGridEngine:
    """Manages backdrop synthesis, mask generation, and filtergraph configuration
    for the Before & After Cyber Grid editing style.
    """

    TARGET_WIDTH = 1080
    TARGET_HEIGHT = 1920

    # Layout geometries
    BEFORE_BOX = {"x": 64, "y": 550, "w": 352, "h": 600, "radius": 32}
    AFTER_BOX = {"x": 440, "y": 320, "w": 600, "h": 1060, "radius": 40}

    # Visual constants
    HEADER_COLOR = (0, 255, 224, 255)  # Neon Cyan
    HEADER_SHADOW = (0, 30, 15, 230)
    GRID_LINE_COLOR = (42, 218, 85, 160)  # Luminous Green
    COLOR_GRADE_FILTER = "eq=contrast=1.20:saturation=1.28:brightness=-0.02,unsharp=5:5:0.8:5:5:0.0"
    AFTER_ZOOM_FACTOR = 1.38

    def __init__(self, templates_dir: Path = None):
        if templates_dir is None:
            self.templates_dir = (
                Path(__file__).resolve().parent.parent.parent
                / "assets"
                / "templates"
                / "cyber_grid"
            )
        else:
            self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self.backdrop_path = self.templates_dir / "cyber_grid_backdrop.png"
        self.mask_before_path = self.templates_dir / "mask_before.png"
        self.mask_after_path = self.templates_dir / "mask_after.png"

    def ensure_assets(self) -> Tuple[Path, Path, Path]:
        """Ensure backdrop and window mask PNG assets exist on disk."""
        if (
            not self.backdrop_path.exists()
            or not self.mask_before_path.exists()
            or not self.mask_after_path.exists()
        ):
            self.generate_assets()
        return self.backdrop_path, self.mask_before_path, self.mask_after_path

    def generate_assets(self):
        """Generate high-resolution cyber grid backdrop and rounded corner masks."""
        logger.info(f"Generating Cyber Grid template assets in {self.templates_dir}...")
        w, h = self.TARGET_WIDTH, self.TARGET_HEIGHT

        # 1. Base Gradient (Deep forest green vignette)
        y_coords, x_coords = np.ogrid[:h, :w]
        cx, cy = 540, 1050
        dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2) / 1050.0
        dist = np.clip(dist, 0.0, 1.0)
        top_factor = y_coords / h

        r = (14 * (1 - dist * 0.8) * (0.35 + 0.65 * top_factor)).astype(np.uint8)
        g = (120 * (1 - dist * 0.75) * (0.38 + 0.62 * top_factor)).astype(np.uint8)
        b = (28 * (1 - dist * 0.8) * (0.35 + 0.65 * top_factor)).astype(np.uint8)

        base_arr = np.dstack([r, g, b])
        canvas = Image.fromarray(base_arr, "RGB").convert("RGBA")

        # 2. Cyber Grid Lines
        grid_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_grid = ImageDraw.Draw(grid_layer)
        step_x = 90
        step_y = 92
        start_x = (w % step_x) // 2
        start_y = (h % step_y) // 2

        for x in range(start_x, w, step_x):
            draw_grid.line([(x, 0), (x, h)], fill=self.GRID_LINE_COLOR, width=2)
        for y in range(start_y, h, step_y):
            draw_grid.line([(0, y), (w, y)], fill=self.GRID_LINE_COLOR, width=2)

        canvas = Image.alpha_composite(canvas, grid_layer)

        # 3. Card Drop Shadows (Ambient Occlusion)
        b = self.BEFORE_BOX
        a = self.AFTER_BOX
        shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d_sh = ImageDraw.Draw(shadow_layer)
        d_sh.rounded_rectangle(
            [b["x"] - 8, b["y"] - 6, b["x"] + b["w"] + 8, b["y"] + b["h"] + 16],
            radius=b["radius"] + 6,
            fill=(0, 0, 0, 180),
        )
        d_sh.rounded_rectangle(
            [a["x"] - 10, a["y"] - 8, a["x"] + a["w"] + 14, a["y"] + a["h"] + 22],
            radius=a["radius"] + 6,
            fill=(0, 0, 0, 220),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(18))
        canvas = Image.alpha_composite(canvas, shadow_layer)

        # 4. Badges: "BEFORE" and "AFTER" in bold neon cyan
        text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d_txt = ImageDraw.Draw(text_layer)

        # Search for available bold sans font
        font = None
        for p in [
            "C:/Windows/Fonts/ariblk.ttf",
            "assets/fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/impact.ttf",
        ]:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, size=60)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        def draw_header(text: str, center_x: int, bottom_y: int):
            d_txt.text((center_x + 3, bottom_y + 3), text, font=font, fill=self.HEADER_SHADOW, anchor="mb")
            d_txt.text((center_x, bottom_y), text, font=font, fill=self.HEADER_COLOR, anchor="mb")

        # Draw headers cleanly above the cards matching reference short positioning
        draw_header("BEFORE", b["x"] + b["w"] // 2, b["y"] - 12)  # bottom at y=538, gap 12px
        draw_header("AFTER", a["x"] + a["w"] // 2, a["y"] - 22)   # bottom at y=298, gap 22px

        canvas = Image.alpha_composite(canvas, text_layer)
        canvas.save(str(self.backdrop_path))
        logger.info(f"Saved cyber grid backdrop to {self.backdrop_path}")

        # 5. Save Alpha Masks
        def save_mask(mw: int, mh: int, radius: int, out_p: Path):
            m = Image.new("L", (mw, mh), 0)
            d = ImageDraw.Draw(m)
            d.rounded_rectangle([0, 0, mw, mh], radius=radius, fill=255)
            m.save(str(out_p))

        save_mask(b["w"], b["h"], b["radius"], self.mask_before_path)
        save_mask(a["w"], a["h"], a["radius"], self.mask_after_path)
        logger.info(f"Saved card window masks to {self.mask_before_path} and {self.mask_after_path}")


# Global singleton instance
cyber_grid_engine = CyberGridEngine()
