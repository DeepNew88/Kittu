import os
from io import BytesIO
import httpx
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import logger, config
from anony.helpers import Track


def load_fonts():
    try:
        return {
            "title": ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 40),
            "artist": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 26),
            "small": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 22),
        }
    except:
        return {
            "title": ImageFont.load_default(),
            "artist": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }


FONTS = load_fonts()


async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=6)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            return ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
        except:
            return Image.new("RGBA", (1280, 720), (20, 20, 30, 255))


class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}_perfect.png"

            thumb = await fetch_image(song.thumbnail)

            width, height = 1280, 720

            # ===== STRONG BACKGROUND BLUR =====
            bg = thumb.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(70))
            bg = ImageEnhance.Brightness(bg).enhance(0.7)

            # Warm tint
            tint = Image.new("RGBA", (width, height), (25, 18, 18, 130))
            bg = Image.alpha_composite(bg.convert("RGBA"), tint)

            # ===== BIGGER PANEL =====
            panel_w, panel_h = 960, 560
            panel_x = (width - panel_w) // 2
            panel_y = (height - panel_h) // 2

            # ===== HEAVY SHADOW =====
            shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 240))
            shadow_mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(shadow_mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=60,
                fill=255
            )
            shadow.putalpha(shadow_mask)
            bg.paste(shadow, (panel_x + 25, panel_y + 40), shadow)

            # ===== GLASS CARD =====
            glass = Image.new("RGBA", (panel_w, panel_h), (38, 38, 38, 160))
            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=60,
                fill=255
            )
            glass.putalpha(mask)
            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== COVER =====
            cover = ImageOps.fit(
                thumb, (250, 250), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (250, 250), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 250, 250), radius=40, fill=255
            )
            cover.putalpha(cover_mask)

            bg.paste(cover, (panel_x + 90, panel_y + 110), cover)

            # ===== TEXT =====
            title = (song.title or "Unknown Title")[:42]
            artist = (song.channel_name or "Unknown Artist")[:38]

            draw.text(
                (panel_x + 420, panel_y + 130),
                title,
                fill="white",
                font=FONTS["title"],
            )

            draw.text(
                (panel_x + 420, panel_y + 185),
                artist,
                fill=(210, 210, 210),
                font=FONTS["artist"],
            )

            # ===== MAIN PROGRESS =====
            bar_x1 = panel_x + 420
            bar_x2 = panel_x + 900
            bar_y = panel_y + 260

            draw.line(
                [(bar_x1, bar_y), (bar_x2, bar_y)],
                fill=(170, 170, 170),
                width=6,
            )

            progress = bar_x1 + 260
            draw.line(
                [(bar_x1, bar_y), (progress, bar_y)],
                fill="white",
                width=6,
            )

            draw.text(
                (bar_x1, bar_y - 30),
                "0:24",
                fill="white",
                font=FONTS["small"],
            )

            draw.text(
                (bar_x2 - 60, bar_y - 30),
                song.duration or "--:--",
                fill="white",
                font=FONTS["small"],
            )

            # ===== CONTROLS PNG =====
            try:
                controls = Image.open("anony/assets/controls.png").convert("RGBA")
                controls = controls.resize((700, 200), Image.Resampling.LANCZOS)

                bg.paste(
                    controls,
                    (panel_x + 140, panel_y + 320),
                    controls
                )
            except:
                pass

            # ===== VOLUME BAR =====
            vol_y = panel_y + 500

            draw.line(
                [(panel_x + 180, vol_y),
                 (panel_x + 900, vol_y)],
                fill=(150, 150, 150),
                width=6,
            )

            draw.line(
                [(panel_x + 180, vol_y),
                 (panel_x + 520, vol_y)],
                fill=(220, 220, 220),
                width=6,
            )

            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)
            return config.DEFAULT_THUMB
