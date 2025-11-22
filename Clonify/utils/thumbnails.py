"""
Thumbnail Generator Utility
---------------------------
Generates music-style thumbnail images with background gradients,
album art, rounded corners, progress bars, playback icons, and text.
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Optional
import os
import re

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def sanitize_text(text: str) -> str:
    """Replace unsupported characters to prevent PIL errors."""
    return re.sub(r'[^\x00-\xFF]', '?', text)

def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a Unicode-compatible TrueType font."""
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "./fonts/DejaVuSans-Bold.ttf",
        "./fonts/arial.ttf"
    ]
    for font_path in possible_fonts:
        if os.path.isfile(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    # Fallback to default PIL font
    return ImageFont.load_default()


# ---------------------------------------------------------
# Thumbnail Generator Class
# ---------------------------------------------------------

class ThumbnailGenerator:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.margin = 40

    def create_gradient_background(self, color_start=(220, 50, 20), color_end=(80, 20, 10)) -> Image.Image:
        """Create a vertical gradient background."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)
        for y in range(self.height):
            ratio = y / float(self.height)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            draw.line((0, y, self.width, y), fill=(r, g, b))
        return img

    def resize_album_art(self, path: str, size: int = 350) -> Optional[Image.Image]:
        if not os.path.isfile(path):
            print(f"[ThumbnailGenerator] Album art not found: {path}")
            return None
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return img
        except Exception as exc:
            print("[ThumbnailGenerator] Failed to load album art:", exc)
            return None

    def round_corners(self, img: Image.Image, radius: int = 30) -> Image.Image:
        width, height = img.size
        corner = Image.new("L", (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(corner)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
        mask = Image.new("L", (width, height), 255)
        mask.paste(corner.crop((0, 0, radius, radius)), (0, 0))
        mask.paste(corner.crop((radius, 0, radius * 2, radius)), (width - radius, 0))
        mask.paste(corner.crop((0, radius, radius, radius * 2)), (0, height - radius))
        mask.paste(corner.crop((radius, radius, radius * 2, radius * 2)), (width - radius, height - radius))
        img.putalpha(mask)
        return img

    def seconds_to_time(self, seconds: int) -> str:
        minutes, secs = divmod(seconds, 60)
        return f"{minutes}:{secs:02d}"

    def create_thumbnail(
        self,
        album_art_path: str,
        song_title: str,
        artist_name: str,
        album: str = "Airdopes 131",
        current_seconds: int = 0,
        total_seconds: int = 0,
        output_path: str = "thumbnail.png"
    ) -> str:

        song_title = sanitize_text(song_title)
        artist_name = sanitize_text(artist_name)
        album = sanitize_text(album)

        current_time = self.seconds_to_time(current_seconds)
        total_time = self.seconds_to_time(total_seconds)
        progress = (current_seconds / total_seconds) if total_seconds > 0 else 0.0

        base = self.create_gradient_background()
        art = self.resize_album_art(album_art_path)
        if art is not None:
            art = self.round_corners(art, 30)
            base.paste(art, (self.margin, (self.height // 2) - (art.size[1] // 2)), art if art.mode == "RGBA" else None)

        draw = ImageDraw.Draw(base)

        font_album = load_font(28)
        font_title = load_font(48)
        font_artist = load_font(32)
        font_time = load_font(24)
        font_control = load_font(32)

        x = self.margin + 450
        y = 120
        draw.text((x, y), album, font=font_album, fill=(200, 150, 120))
        y += 50
        draw.text((x, y), song_title, font=font_title, fill=(255, 255, 255))
        y += 70
        draw.text((x, y), artist_name, font=font_artist, fill=(200, 200, 200))

        # Progress bar
        y += 80
        bar_width = 600
        bar_height = 8
        draw.rectangle((x, y, x + bar_width, y + bar_height), fill=(80, 50, 40))
        draw.rectangle((x, y, x + int(bar_width * progress), y + bar_height), fill=(255, 100, 50))

        y += 25
        draw.text((x, y), current_time, font=font_time, fill=(200, 200, 200))
        draw.text((x + bar_width - 60, y), "-" + total_time, font=font_time, fill=(200, 200, 200))

        control_y = y + 80
        controls = ["<<", "||", ">>", "VOL"]
        for index, label in enumerate(controls):
            draw.text((x + 100 + index * 80, control_y), label, font=font_control, fill=(255, 255, 255))

        vol_x = x + 20
        vol_y = control_y + 100
        vol_width = 500
        vol_height = 6
        draw.rectangle((vol_x, vol_y, vol_x + vol_width, vol_y + vol_height), fill=(80, 50, 40))
        draw.rectangle((vol_x, vol_y, vol_x + int(vol_width * 0.7), vol_y + vol_height), fill=(255, 100, 50))

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        base.save(output_path, quality=95)
        print("[ThumbnailGenerator] Saved thumbnail:", output_path)
        return output_path


# ---------------------------------------------------------
# Backward-Compatible Wrapper
# ---------------------------------------------------------

def get_thumb(
    album_art_path: str,
    song_title: str = "Unknown Title",
    artist_name: str = "Unknown Artist",
    album: str = "Airdopes 131",
    current_seconds: int = 0,
    total_seconds: int = 0,
    output_path: str = "thumbnail.png"
) -> str:
    gen = ThumbnailGenerator()
    return gen.create_thumbnail(
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album=album,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path
    )