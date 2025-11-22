"""
Thumbnail Generator Utility
---------------------------
Creates music-style video thumbnails with gradient backgrounds, album art,
rounded corners, progress bars, playback icons, and text.

Includes a backward-compatible `get_thumb()` function because older
Clonify modules import:

    from Clonify.utils.thumbnails import get_thumb
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Optional


class ThumbnailGenerator:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.margin = 40

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def create_gradient_background(
        self,
        color_start=(220, 50, 20),
        color_end=(80, 20, 10)
    ) -> Image.Image:
        """Generate a vertical gradient background."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        for y in range(self.height):
            r = int(color_start[0] + (color_end[0] - color_start[0]) * (y / self.height))
            g = int(color_start[1] + (color_end[1] - color_start[1]) * (y / self.height))
            b = int(color_start[2] + (color_end[2] - color_start[2]) * (y / self.height))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    def resize_album_art(self, path: str, size: int = 350) -> Optional[Image.Image]:
        """Load album art, convert to RGB, and shrink it."""
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            print(f"[ThumbnailGenerator] Failed to load image: {e}")
            return None

    def round_corners(self, img: Image.Image, radius: int = 30) -> Image.Image:
        """Apply rounded corners to album art."""
        w, h = img.size
        circle = Image.new("L", (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

        alpha = Image.new("L", (w, h), 255)
        alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
        alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
        alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
        alpha.paste(circle.crop((radius, radius, radius * 2, radius * 2)), (w - radius, h - radius))

        img.putalpha(alpha)
        return img

    def seconds_to_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    # ---------------------------------------------------------
    # Main Thumbnail Generator
    # ---------------------------------------------------------

    def create_thumbnail(
        self,
        album_art_path: str,
        song_title: str,
        artist_name: str,
        album: str = "Airdopes 131",
        current_seconds: int = 141,
        total_seconds: int = 281,
        output_path: str = "thumbnail.png"
    ) -> str:
        """Render and export the final thumbnail image."""

        current_time = self.seconds_to_time(current_seconds)
        total_time = self.seconds_to_time(total_seconds)
        progress_ratio = current_seconds / total_seconds if total_seconds > 0 else 0

        base = self.create_gradient_background()

        art = self.resize_album_art(album_art_path, 350)
        if art:
            art = self.round_corners(art, 30)
            base.paste(
                art,
                (self.margin, self.height // 2 - 175),
                art if art.mode == "RGBA" else None
            )

        draw = ImageDraw.Draw(base)

        # Load fonts
        try:
            album_font = ImageFont.truetype("arial.ttf", 28)
            title_font = ImageFont.truetype("arial.ttf", 48)
            artist_font = ImageFont.truetype("arial.ttf", 32)
            time_font = ImageFont.truetype("arial.ttf", 24)
            control_font = ImageFont.truetype("arial.ttf", 40)
        except:
            album_font = title_font = artist_font = time_font = control_font = ImageFont.load_default()

        x = self.margin + 450
        y = 120

        # Album
        draw.text((x, y), album, font=album_font, fill=(200, 150, 120))

        # Title
        y += 50
        draw.text((x, y), song_title, font=title_font, fill=(255, 255, 255))

        # Artist
        y += 70
        draw.text((x, y), artist_name, font=artist_font, fill=(200, 200, 200))

        # Progress bar
        y += 80
        bar_w, bar_h = 600, 8

        draw.rectangle((x, y, x + bar_w, y + bar_h), fill=(80, 50, 40))
        draw.rectangle((x, y, x + int(bar_w * progress_ratio), y + bar_h), fill=(255, 100, 50))

        # Time text
        y += 25
        draw.text((x, y), current_time, font=time_font, fill=(200, 200, 200))
        draw.text((x + bar_w - 60, y), f"-{total_time}", font=time_font, fill=(200, 200, 200))

        # Controls
        control_y = y + 80
        controls = ["⏮", "⏸", "⏭", "🔊"]

        for i, c in enumerate(controls):
            draw.text((x + 100 + i * 80, control_y), c, font=control_font, fill=(255, 255, 255))

        # Volume
        vol_x = x + 20
        vol_y = control_y + 100
        vol_w, vol_h = 500, 6

        draw.rectangle((vol_x, vol_y, vol_x + vol_w, vol_y + vol_h), fill=(80, 50, 40))
        draw.rectangle((vol_x, vol_y, vol_x + int(vol_w * 0.7), vol_y + vol_h), fill=(255, 100, 50))

        # Save
        base.save(output_path, quality=95)
        print(f"[ThumbnailGenerator] Saved thumbnail -> {output_path}")

        return output_path


# --------------------------------------------------------------------
# Backward-Compatible Legacy Wrapper
# Required because older Clonify modules import get_thumb()
# --------------------------------------------------------------------

def get_thumb(
    album_art_path: str,
    song_title: str,
    artist_name: str,
    album: str = "Airdopes 131",
    current_seconds: int = 141,
    total_seconds: int = 281,
    output_path: str = "thumbnail.png",
) -> str:
    """Legacy wrapper preserving old API."""
    generator = ThumbnailGenerator()
    return generator.create_thumbnail(
        album_art_path,
        song_title,
        artist_name,
        album,
        current_seconds,
        total_seconds,
        output_path,
    )