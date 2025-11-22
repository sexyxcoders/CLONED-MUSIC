"""
Thumbnail Generator Utility
---------------------------
Creates music-style video thumbnails with gradient backgrounds, album art,
rounded corners, progress bars, playback icons, and text.

Includes a backward-compatible get_thumb() function because older
Clonify modules use:

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
    # Helper functions
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
            ratio = y / self.height
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    def resize_album_art(self, path: str, size: int = 350) -> Optional[Image.Image]:
        """Load and resize album art safely."""
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return img
        except Exception as exc:
            print("[ThumbnailGenerator] Error loading album art:", exc)
            return None

    def round_corners(self, img: Image.Image, radius: int = 30) -> Image.Image:
        """Apply rounded corners to an image."""
        width, height = img.size
        corner = Image.new("L", (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(corner)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

        mask = Image.new("L", img.size, 255)
        mask.paste(corner.crop((0, 0, radius, radius)), (0, 0))
        mask.paste(corner.crop((radius, 0, radius * 2, radius)), (width - radius, 0))
        mask.paste(corner.crop((0, radius, radius, radius * 2)), (0, height - radius))
        mask.paste(corner.crop((radius, radius, radius * 2, radius * 2)),
                   (width - radius, height - radius))

        img.putalpha(mask)
        return img

    def seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes, secs = divmod(seconds, 60)
        return f"{minutes}:{secs:02d}"

    # ---------------------------------------------------------
    # Thumbnail creation
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
        """Render and save the thumbnail."""

        # Prepare time values
        current_time = self.seconds_to_time(current_seconds)
        total_time = self.seconds_to_time(total_seconds)
        progress_ratio = (current_seconds / total_seconds) if total_seconds > 0 else 0.0

        # Background
        base = self.create_gradient_background()

        # Album art
        art = self.resize_album_art(album_art_path, 350)
        if art is not None:
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
        except Exception:
            # Fallback in case Arial is missing
            album_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            artist_font = ImageFont.load_default()
            time_font = ImageFont.load_default()
            control_font = ImageFont.load_default()

        # Text positions
        x = self.margin + 450
        y = 120

        # Album name
        draw.text((x, y), album, font=album_font, fill=(200, 150, 120))

        # Song title
        y += 50
        draw.text((x, y), song_title, font=title_font, fill=(255, 255, 255))

        # Artist
        y += 70
        draw.text((x, y), artist_name, font=artist_font, fill=(200, 200, 200))

        # Progress bar
        y += 80
        bar_width = 600
        bar_height = 8

        draw.rectangle((x, y, x + bar_width, y + bar_height), fill=(80, 50, 40))
        draw.rectangle((x, y, x + int(bar_width * progress_ratio), y + bar_height),
                       fill=(255, 100, 50))

        # Time text
        y += 25
        draw.text((x, y), current_time, font=time_font, fill=(200, 200, 200))
        draw.text((x + bar_width - 60, y), f"-{total_time}", font=time_font,
                  fill=(200, 200, 200))

        # Playback controls (ASCII-safe)
        control_y = y + 80
        controls = ["<<", "||", ">>", "VOL"]

        for index, label in enumerate(controls):
            draw.text((x + 100 + index * 80, control_y), label, font=control_font,
                      fill=(255, 255, 255))

        # Volume bar
        vol_x = x + 20
        vol_y = control_y + 100
        vol_width = 500
        vol_height = 6

        draw.rectangle((vol_x, vol_y, vol_x + vol_width, vol_y + vol_height),
                       fill=(80, 50, 40))
        draw.rectangle((vol_x, vol_y, vol_x + int(vol_width * 0.7), vol_y + vol_height),
                       fill=(255, 100, 50))

        # Save output
        base.save(output_path, quality=95)
        print("[ThumbnailGenerator] Thumbnail saved to:", output_path)
        return output_path


# ---------------------------------------------------------
# Legacy wrapper for old Clonify imports
# ---------------------------------------------------------

def get_thumb(
    album_art_path: str,
    song_title: str,
    artist_name: str,
    album: str = "Airdopes 131",
    current_seconds: int = 141,
    total_seconds: int = 281,
    output_path: str = "thumbnail.png"
) -> str:
    """Compatibility wrapper for older Clonify code."""
    generator = ThumbnailGenerator()
    return generator.create_thumbnail(
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album=album,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path
    )