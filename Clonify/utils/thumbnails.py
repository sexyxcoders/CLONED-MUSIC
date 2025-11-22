from PIL import Image, ImageDraw, ImageFont
from typing import Optional
import os


class ThumbnailGenerator:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.margin = 40

    def create_gradient_background(self, color_start=(220, 50, 20), color_end=(80, 20, 10)):
        """Create a vertical gradient background."""
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)

        r1, g1, b1 = color_start
        r2, g2, b2 = color_end

        for y in range(self.height):
            ratio = y / self.height
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    def resize_album_art(self, path: str, size: int = 350):
        """Load and resize album art."""
        try:
            img = Image.open(path).convert('RGB')
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            print(f"[ThumbnailGenerator] Error loading image: {e}")
            return None

    def round_corners(self, img: Image.Image, radius: int = 30):
        """Apply rounded corners to an image."""
        circle = Image.new('L', (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse([0, 0, radius * 2, radius * 2], fill=255)

        alpha = Image.new('L', img.size, 255)
        w, h = img.size

        alpha.paste(circle.crop([0, 0, radius, radius]), (0, 0))
        alpha.paste(circle.crop([radius, 0, radius * 2, radius]), (w - radius, 0))
        alpha.paste(circle.crop([0, radius, radius, radius * 2]), (0, h - radius))
        alpha.paste(circle.crop([radius, radius, radius * 2, radius * 2]), (w - radius, h - radius))

        img.putalpha(alpha)
        return img

    def seconds_to_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

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
        """
        Create a full graphic audio thumbnail.
        Returns: output_path
        """

        # Convert time
        current_time = self.seconds_to_time(current_seconds)
        total_time = self.seconds_to_time(total_seconds)
        progress = current_seconds / total_seconds if total_seconds > 0 else 0

        base = self.create_gradient_background()

        # Load album art
        art = self.resize_album_art(album_art_path, 350)
        if art:
            art = self.round_corners(art, 30)
            base.paste(art, (self.margin, self.height // 2 - 175), art)

        draw = ImageDraw.Draw(base)

        # Fonts
        try:
            album_font = ImageFont.truetype("arial.ttf", 28)
            title_font = ImageFont.truetype("arial.ttf", 48)
            artist_font = ImageFont.truetype("arial.ttf", 32)
            time_font = ImageFont.truetype("arial.ttf", 24)
            control_font = ImageFont.truetype("arial.ttf", 40)
        except:
            album_font = title_font = artist_font = time_font = control_font = ImageFont.load_default()

        # Text positioning
        x = self.margin + 450
        y = 120

        # Draw texts
        draw.text((x, y), album, font=album_font, fill=(200, 150, 120))
        y += 50
        draw.text((x, y), song_title, font=title_font, fill=(255, 255, 255))
        y += 70
        draw.text((x, y), artist_name, font=artist_font, fill=(200, 200, 200))

        # Progress bar
        y += 80
        bar_width = 600
        bar_height = 8

        draw.rectangle([x, y, x + bar_width, y + bar_height], fill=(80, 50, 40))
        draw.rectangle([x, y, x + int(bar_width * progress), y + bar_height], fill=(255, 100, 50))

        # Time text
        y += 25
        draw.text((x, y), current_time, font=time_font, fill=(200, 200, 200))
        draw.text((x + bar_width - 60, y), f"-{total_time}", font=time_font, fill=(200, 200, 200))

        # Playback controls
        controls = ["⏮", "⏸", "⏭", "🔊"]
        control_y = y + 80
        spacing = 80

        for i, c in enumerate(controls):
            draw.text((x + 100 + spacing * i, control_y), c, font=control_font, fill=(255, 255, 255))

        # Volume bar
        vol_x = x + 20
        vol_y = control_y + 100
        vol_width = 500
        vol_height = 6

        draw.rectangle([vol_x, vol_y, vol_x + vol_width, vol_y + vol_height], fill=(80, 50, 40))
        draw.rectangle([vol_x, vol_y, vol_x + int(vol_width * 0.7), vol_y + vol_height], fill=(255, 100, 50))

        base.save(output_path, quality=95)
        print(f"[ThumbnailGenerator] Thumbnail saved -> {output_path}")

        return output_path


# ---------------------------------------------------------------------
# BACKWARD-COMPATIBILITY WRAPPER
# ---------------------------------------------------------------------

def get_thumb(album_art_path: str, song_title: str, artist_name: str,
              album: str = "Airdopes 131", current_seconds: int = 141,
              total_seconds: int = 281, output_path: str = "thumbnail.png") -> str:
    """
    Backwards-compatible wrapper so old imports:
        from Clonify.utils.thumbnails import get_thumb
    still work.
    """
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