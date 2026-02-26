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
            "title": ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 44),
            "artist": ImageFont.truetype("anony/helpers/Inter-Light.ttf", 28),
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
            return Image.new("RGBA", (1280, 720), (40, 20, 20, 255))


class Thumbnail:
    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            save_path = f"cache/{song.id}_final.png"

            thumb = await fetch_image(song.thumbnail)

            width, height = 1280, 720

            # ===== SOFT BLUR BACKGROUND =====
            bg = thumb.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(55))
            bg = ImageEnhance.Brightness(bg).enhance(0.85)

            tint = Image.new("RGBA", (width, height), (30, 20, 20, 90))
            bg = Image.alpha_composite(bg.convert("RGBA"), tint)

            # ===== PANEL FRAME =====
            panel_x, panel_y = 305, 125
            panel_w = 975 - 305
            panel_h = 595 - 125

            # ===== SOFT SHADOW =====
            shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 255))
            shadow = shadow.filter(ImageFilter.GaussianBlur(25))
            bg.paste(shadow, (panel_x + 10, panel_y + 20), shadow)

            # ===== FROSTED GLASS PANEL =====
            glass = Image.new("RGBA", (panel_w, panel_h), (40, 40, 40, 150))
            mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, panel_w, panel_h),
                radius=30,
                fill=255,
            )
            glass.putalpha(mask)
            bg.paste(glass, (panel_x, panel_y), glass)

            draw = ImageDraw.Draw(bg)

            # ===== ALBUM COVER =====
            cover = ImageOps.fit(
                thumb, (220, 220), Image.Resampling.LANCZOS
            )

            cover_mask = Image.new("L", (220, 220), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, 220, 220), radius=25, fill=255
            )
            cover.putalpha(cover_mask)

            bg.paste(cover, (305, 150), cover)

            # ===== TEXT =====
            title = (song.title or "Unknown Title")[:45]
            artist = (song.channel_name or "Unknown Artist")[:40]

            draw.text(
                (550, 170),
                title,
                fill="white",
                font=FONTS["title"],
            )

            draw.text(
                (550, 225),
                artist,
                fill=(220, 220, 220),
                font=FONTS["artist"],
            )

            # ===== THIN PROGRESS BAR =====
            bar_y = 360
            bar_start = panel_x + 180
            bar_end = panel_x + panel_w - 180

            draw.line(
                [(bar_start, bar_y), (bar_end, bar_y)],
                fill=(180, 180, 180),
                width=5,
            )

            progress = bar_start + int((bar_end - bar_start) * 0.3)

            draw.line(
                [(bar_start, bar_y), (progress, bar_y)],
                fill=(240, 240, 240),
                width=5,
            )

            # ===== CONTROLS =====
            try:
                controls = Image.open("anony/assets/controls.png").convert("RGBA")
                controls = controls.resize((600, 160), Image.Resampling.LANCZOS)

                bg.paste(
                    controls,
                    (335, 415),
                    controls,
                )
            except:
                pass

            # ===== THIN VOLUME BAR =====
            vol_y = 575
            padding = 110
            bar_start = panel_x + padding
            bar_end = panel_x + panel_w - padding

            draw.line(
                [(bar_start, vol_y),
                 (bar_end, vol_y)],
                fill=(150, 150, 150),
                width=5,
            )

            filled_width = int((bar_end - bar_start) * 0.6)

            draw.line(
                [(bar_start, vol_y),
                 (bar_start + filled_width, vol_y)],
                fill=(240, 240, 240),
                width=5,
            )

            bg.save(save_path, "PNG", quality=95)
            return save_path

        except Exception as e:
            logger.warning("Thumbnail generation failed: %s", e)
            return config.DEFAULT_THUMB
