"""
Perfect iOS-Style Music Thumbnail Generator
-------------------------------------------
Creates an EXACT replica of the layout shown in the screenshot:
- Rounded rectangular music widget
- Red monochrome album-art filter
- iOS-style progress bar
- Play/forward/back icons
- White text with correct alignment
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import re


# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    return re.sub(r"[^\x00-\xFF]", "?", text)


def load_font(size: int):
    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "./fonts/DejaVuSans.ttf",
        "./fonts/arial.ttf"
    ]
    for f in fonts:
        if os.path.isfile(f):
            try:
                return ImageFont.truetype(f, size)
            except:
                pass
    return ImageFont.load_default()


# ──────────────────────────────────────────────────────────────
# Thumbnail Generator
# ──────────────────────────────────────────────────────────────

class IOSMusicThumbnail:

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height

    def red_filter(self, img: Image.Image) -> Image.Image:
        """Applies deep red overlay exactly like the screenshot."""
        red = Image.new("RGB", img.size, (255, 0, 0))
        return Image.blend(img.convert("RGB"), red, 0.6)

    def round_rect(self, size, radius=60):
        """Mask for rounded widget."""
        w, h = size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
        return mask

    def seconds(self, sec: int):
        return f"{sec//60}:{sec%60:02d}"

    def create(
        self,
        album_path: str,
        title: str,
        artist: str,
        album="Airdopes 131",
        current=141,       # 2:21
        total=140,         # -2:20 (screenshot shows slight mismatch)
        out="thumbnail.png"
    ):

        # ----- Base Full Red Background -----
        bg = Image.new("RGB", (self.width, self.height), (90, 20, 10))

        # ----- Music Widget (Rounded) -----
        widget = Image.new("RGB", (1100, 500), (65, 10, 10))
        widget_mask = self.round_rect(widget.size, radius=55)
        widget.putalpha(widget_mask)

        # Paste widget centered
        bg.paste(widget, (90, 110), widget)

        draw = ImageDraw.Draw(bg)

        # -------------------------------
        # ALBUM ART with red filter
        # -------------------------------
        if os.path.isfile(album_path):
            art = Image.open(album_path).convert("RGB")
            art = art.resize((430, 500))
            art = self.red_filter(art)
            art_mask = self.round_rect((430, 500), radius=55)
            art.putalpha(art_mask)
            bg.paste(art, (90, 110), art)

        # -------------------------------
        # Text Styling
        # -------------------------------
        font_small = load_font(35)
        font_title = load_font(60)
        font_artist = load_font(45)
        font_time = load_font(32)
        font_icons = load_font(55)

        text_x = 560
        y = 160

        # Album Name
        draw.text((text_x, y), sanitize(album), fill=(255, 255, 255), font=font_small)
        y += 60

        # Song Title (bold white)
        draw.text((text_x, y), sanitize(title), fill=(255, 255, 255), font=font_title)
        y += 80

        # Artist Name
        draw.text((text_x, y), sanitize(artist), fill=(230, 230, 230), font=font_artist)
        y += 90

        # -------------------------------
        # PROGRESS BAR
        # -------------------------------
        bar_w = 520
        bar_h = 10
        progress = max(0, min(1, current / total))

        # Background bar
        draw.rounded_rectangle(
            (text_x, y, text_x + bar_w, y + bar_h),
            radius=6, fill=(120, 60, 50)
        )
        # Progress part
        draw.rounded_rectangle(
            (text_x, y, text_x + int(bar_w * progress), y + bar_h),
            radius=6, fill=(255, 200, 180)
        )

        # Times
        draw.text((text_x, y + 20), self.seconds(current), fill=(230, 230, 230), font=font_time)
        draw.text((text_x + bar_w - 80, y + 20), f"-{self.seconds(total)}", fill=(230, 230, 230), font=font_time)

        # -------------------------------
        # CONTROL BUTTONS (Centered)
        # -------------------------------
        btn_y = y + 110
        draw.text((text_x + 30, btn_y), "⏮", font=font_icons, fill="white")
        draw.text((text_x + 130, btn_y), "⏸", font=font_icons, fill="white")
        draw.text((text_x + 230, btn_y), "⏭", font=font_icons, fill="white")
        draw.text((text_x + 350, btn_y + 2), "🔊", font=font_icons, fill="white")

        bg.save(out, quality=95)
        return out


# Backwards compatibility
def get_thumb(album_art_path, song_title, artist_name, album="Airdopes 131",
              current_seconds=141, total_seconds=140, output_path="thumbnail.png"):

    gen = IOSMusicThumbnail()
    return gen.create(
        album_path=album_art_path,
        title=song_title,
        artist=artist_name,
        album=album,
        current=current_seconds,
        total=total_seconds,
        out=output_path
    )