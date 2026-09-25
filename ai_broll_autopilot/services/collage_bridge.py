"""Integration bridge to gbro-collage-broll editorial animation engine."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

from ai_broll_autopilot.config import Config

logger = logging.getLogger(__name__)


class CollageBridge:
    """Bridge for generating editorial paper-collage animation B-roll."""

    def __init__(self):
        self.script_path = Config.COLLAGE_DIR / "scripts" / "generate_video.py"

    async def generate_collage_clip(self, prompt: str, output_path: str, duration: int = 4) -> Optional[str]:
        """Generate a paper-collage animation B-roll clip using Gemini Omni Flash or fallback."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating Collage B-roll for prompt: '{prompt}'")

        if self.script_path.exists() and Config.GEMINI_API_KEY:
            try:
                # Try calling gbro-collage-broll script
                python_exe = str(Config.PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
                cmd = [
                    python_exe,
                    str(self.script_path),
                    f"Editorial halftone paper collage stop-motion assembly of {prompt}, clean, solid flat background, no text, no watermarks",
                    "--aspect-ratio", "9:16",
                    "--duration", str(duration),
                    "--output", str(out_p),
                    "--api-key", Config.GEMINI_API_KEY,
                ]

                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=14),
                        timeout=15.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Gemini Omni Flash API call timed out (>15s), using instant procedural collage fallback")

                if out_p.exists() and out_p.stat().st_size > 1000:
                    logger.info(f"Collage B-roll generated via Omni Flash: {out_p.name}")
                    return str(out_p)

            except Exception as e:
                logger.warning(f"Gemini Omni Flash collage generation failed: {e}. Using animated collage fallback.")

        # Robust stylized paper-collage fallback using FFmpeg generator
        return await self._generate_fallback_collage(prompt, out_p, duration)

    async def _generate_fallback_collage(self, prompt: str, out_p: Path, duration: int) -> Optional[str]:
        """Create a clean, stylized paper-collage graphic clip using Pillow and FFmpeg."""
        logger.info(f"Rendering stylized paper-collage motion graphic for: '{prompt}'")
        try:
            from PIL import Image, ImageDraw

            width, height = Config.TARGET_WIDTH, Config.TARGET_HEIGHT
            # Dark editorial background
            bg_color = (25, 27, 36)
            img = Image.new("RGB", (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Paper card boundaries
            paper_rect = [100, 600, width - 100, height - 600]
            # Shadow card
            draw.rectangle(
                [paper_rect[0] + 15, paper_rect[1] + 15, paper_rect[2] + 15, paper_rect[3] + 15],
                fill=(12, 12, 16)
            )
            # Main torn paper card (warm cream)
            draw.rectangle(paper_rect, fill=(245, 240, 230), outline=(20, 20, 20), width=8)

            # Halftone dot pattern across the paper card
            for y in range(paper_rect[1] + 40, paper_rect[3] - 40, 36):
                for x in range(paper_rect[0] + 40, paper_rect[2] - 40, 36):
                    dot_rad = 3 + ((x * y) % 4)
                    draw.ellipse([x - dot_rad, y - dot_rad, x + dot_rad, y + dot_rad], fill=(175, 170, 155))

            # Inner cutout illustration frame
            inner_rect = [paper_rect[0] + 40, paper_rect[1] + 120, paper_rect[2] - 40, paper_rect[3] - 60]
            draw.rectangle(inner_rect, fill=(35, 38, 50), outline=(20, 20, 20), width=4)

            p_low = prompt.lower()
            # Theme 1: Cardboard Box / Packing / Fired
            if any(k in p_low for k in ["cardboard", "box", "pack", "fired", "leaving", "layoff"]):
                # Draw Cardboard Box Graphic
                box_w = 420
                box_h = 320
                box_x = (width - box_w) // 2
                box_y = inner_rect[1] + 280

                # Items sticking out of box (plant, mug, paper)
                # Plant leaf
                draw.ellipse([box_x + 60, box_y - 120, box_x + 130, box_y - 20], fill=(70, 160, 95), outline=(20, 20, 20), width=3)
                draw.ellipse([box_x + 110, box_y - 150, box_x + 180, box_y - 40], fill=(90, 185, 115), outline=(20, 20, 20), width=3)
                # Coffee mug
                draw.rectangle([box_x + 240, box_y - 80, box_x + 320, box_y], fill=(235, 95, 85), outline=(20, 20, 20), width=3)
                draw.arc([box_x + 300, box_y - 70, box_x + 350, box_y - 20], -90, 90, fill=(235, 95, 85), width=8)

                # Cardboard box body (kraft brown)
                draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(195, 145, 95), outline=(30, 25, 20), width=5)
                # Box flaps
                draw.polygon([
                    (box_x, box_y), (box_x - 30, box_y - 60), (box_x + 180, box_y - 40), (box_x + 180, box_y)
                ], fill=(175, 125, 80), outline=(30, 25, 20))
                draw.polygon([
                    (box_x + 240, box_y), (box_x + 240, box_y - 40), (box_x + box_w + 30, box_y - 60), (box_x + box_w, box_y)
                ], fill=(175, 125, 80), outline=(30, 25, 20))
                # Packing tape across middle
                draw.rectangle([box_x, box_y + 120, box_x + box_w, box_y + 170], fill=(155, 110, 70))

            # Theme 2: Frustration / Computer / Stress
            elif any(k in p_low for k in ["frustrat", "slow", "rage", "stress", "behind", "drown", "overwhelm"]):
                # Clock / stress graphic
                cx = width // 2
                cy = inner_rect[1] + 400
                rad = 180
                draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(245, 240, 230), outline=(20, 20, 20), width=8)
                # Rapid clock hands
                draw.line([(cx, cy), (cx + 100, cy - 80)], fill=(225, 45, 35), width=10)
                draw.line([(cx, cy), (cx - 70, cy + 90)], fill=(20, 20, 20), width=8)
                draw.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(20, 20, 20))

            # Theme 3: Empty Office / Desks
            else:
                # Minimalist office cubicle desk and chair
                cx = width // 2
                cy = inner_rect[1] + 420
                draw.rectangle([cx - 240, cy, cx + 240, cy + 30], fill=(160, 165, 175), outline=(20, 20, 20), width=4)
                draw.line([(cx - 200, cy + 30), (cx - 200, cy + 200)], fill=(40, 45, 55), width=8)
                draw.line([(cx + 200, cy + 30), (cx + 200, cy + 200)], fill=(40, 45, 55), width=8)
                # Monitor on desk
                draw.rectangle([cx - 100, cy - 140, cx + 100, cy - 20], fill=(25, 28, 38), outline=(20, 20, 20), width=4)
                draw.line([(cx, cy - 20), (cx, cy)], fill=(40, 45, 55), width=10)

            temp_frame = out_p.parent / f"{out_p.stem}_frame.png"
            img.save(temp_frame)

            # Convert to video with subtle slow zoompan motion using FFmpeg
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(temp_frame),
                "-vf", f"scale={width}:{height},zoompan=z='min(zoom+0.0006,1.04)':d={duration * 25}:s={width}x{height}:fps=25",
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-v", "quiet",
                str(out_p),
            ]
            res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.warning(f"FFmpeg collage render error: {res.stderr}")

            if temp_frame.exists():
                temp_frame.unlink()

            if out_p.exists() and out_p.stat().st_size > 1000:
                logger.info(f"Rendered procedural paper-collage clip: {out_p.name}")
                return str(out_p)

        except Exception as e:
            logger.warning(f"Procedural collage rendering error: {e}")

        return None
