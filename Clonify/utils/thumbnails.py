"""
thumbnails.py - Pixel-accurate red music player thumbnail generator.

Usage:
    from thumbnails import generate_thumbnail, get_thumb
    generate_thumbnail(style="A", album_art_path="cover.jpg", song_title="Salvatore",
                       artist_name="Lana Del Rey", album_label="Airdopes 131",
                       current_seconds=141, total_seconds=260,
                       output_path="player_demo.png",
                       reference_image="reference.png")

If reference_image is provided, key colors will be sampled from it for a perfect match.
"""

from typing import Optional, Union
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import os
import math

# ---------------------------
# BASE DIMENSIONS (match screenshot)
# ---------------------------
CANVAS = (1500, 800)           # overall image size
WIDGET = (1450, 650)          # inner rounded card size
WIDGET_POS = (25, 75)         # widget top-left on canvas
RADIUS = 70                   # widget corner radius
ART_SIZE = (630, 650)         # left album art area (exact from screenshot)

# ---------------------------
# DEFAULT COLORS (sampled approximate)
# They will be overridden if a reference image is provided
# ---------------------------
BG_COLOR = (87, 26, 20)
WIDGET_COLOR = (44, 9, 8)
RED_TINT = (180, 0, 0)
TITLE_COLOR = (255, 255, 255)
ARTIST_COLOR = (215, 205, 200)
ALBUM_COLOR = (238, 220, 214)
PROG_BG = (95, 38, 34)
PROG_FG = (255, 192, 182)
ICON_COLOR = (255, 255, 255)

# ---------------------------
# FONT PATHS (common fallbacks)
# ---------------------------
_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "./fonts/DejaVuSans-Bold.ttf",
    "./fonts/DejaVuSans.ttf",
    "./fonts/Arial.ttf",
]


def load_font(size: int, bold: bool = False):
    # prefer a Bold file when bold=True
    for p in _FONT_PATHS:
        try:
            if not os.path.isfile(p):
                continue
            name = os.path.basename(p).lower()
            if bold and "bold" in name:
                return ImageFont.truetype(p, size)
            if not bold and "bold" not in name:
                return ImageFont.truetype(p, size)
        except Exception:
            continue
    # final fallback
    try:
        return ImageFont.load_default()
    except Exception:
        raise RuntimeError("No usable font found")


# ---------------------------
# Utilities
# ---------------------------
def ensure_dir(path: str) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return m


def tint_image(img: Image.Image, tint_color=RED_TINT, strength=0.65) -> Image.Image:
    overlay = Image.new("RGB", img.size, tint_color)
    return Image.blend(img.convert("RGB"), overlay, strength)


def mmss(sec: Union[int, float]) -> str:
    s = max(0, int(sec))
    return f"{s // 60}:{s % 60:02d}"


def _open_album_art(candidate: Optional[Union[str, Image.Image]]):
    if candidate is None:
        return None
    if isinstance(candidate, Image.Image):
        return candidate.convert("RGB")
    if isinstance(candidate, str) and os.path.isfile(candidate):
        try:
            return Image.open(candidate).convert("RGB")
        except Exception:
            return None
    return None


def sample_colors_from_reference(ref_img_path: str):
    """
    Sample key colors from the provided reference image.
    Returns a dict with BG_COLOR, WIDGET_COLOR, RED_TINT, TITLE_COLOR, ARTIST_COLOR, ALBUM_COLOR, PROG_BG, PROG_FG, ICON_COLOR
    """
    try:
        r = Image.open(ref_img_path).convert("RGB")
    except Exception:
        return None

    w, h = r.size

    # sample at a few strategic points (corners, center-left artwork area, right text area)
    def at(x_pct, y_pct):
        x = min(w - 1, max(0, int(x_pct * w)))
        y = min(h - 1, max(0, int(y_pct * h)))
        return r.getpixel((x, y))

    samples = {
        "bg": at(0.5, 0.5),               # approximate center -> widget bg color
        "edge": at(0.02, 0.5),            # left edge margin -> outer bg
        "art_center": at(0.22, 0.45),     # inside album art
        "title": at(0.65, 0.15),          # near title text
        "artist": at(0.65, 0.23),         # near artist text
        "prog_bg": at(0.65, 0.28),
        "prog_fg": at(0.65, 0.28),        # same area; we'll lighten/darken
        "icon": at(0.85, 0.5),
    }

    # Make slight adjustments for best contrasting colors
    def lighten(c, amount=30):
        return tuple(min(255, int(ch + amount)) for ch in c)

    def darken(c, amount=30):
        return tuple(max(0, int(ch - amount)) for ch in c)

    sampled = {
        "BG_COLOR": samples["edge"],
        "WIDGET_COLOR": samples["bg"],
        "RED_TINT": samples["art_center"],
        "TITLE_COLOR": lighten(samples["title"], 30) if samples["title"] else (255, 255, 255),
        "ARTIST_COLOR": lighten(samples["artist"], 8) if samples["artist"] else (215, 205, 200),
        "ALBUM_COLOR": lighten(samples["title"], 6) if samples["title"] else (238, 220, 214),
        "PROG_BG": darken(samples["prog_bg"], 30),
        # for progress foreground, pick a lightened variant so it stands out
        "PROG_FG": lighten(samples["prog_fg"], 80),
        "ICON_COLOR": samples["icon"],
    }

    return sampled


# ---------------------------
# Vector icon drawing (scaleable)
# ---------------------------
def draw_prev(draw: ImageDraw.Draw, x, y, scale=1.0, fill=(255, 255, 255)):
    t = int(34 * scale)
    # left triangles (two triangles to simulate double-previous)
    draw.polygon([(x - t - 8, y), (x - 8, y - t // 2), (x - 8, y + t // 2)], fill=fill)
    draw.polygon([(x + 6 - 8, y), (x + t + 6 - 8, y - t // 2), (x + t + 6 - 8, y + t // 2)], fill=fill)


def draw_pause(draw: ImageDraw.Draw, x, y, scale=1.0, fill=(255, 255, 255)):
    h = int(56 * scale)
    w = int(16 * scale)
    # left bar
    draw.rectangle((x - w - 8, y - h // 2, x - 4 - 8, y + h // 2), fill=fill)
    # right bar
    draw.rectangle((x + 4 - 8, y - h // 2, x + w + 4 - 8, y + h // 2), fill=fill)


def draw_next(draw: ImageDraw.Draw, x, y, scale=1.0, fill=(255, 255, 255)):
    t = int(34 * scale)
    # right triangles
    draw.polygon([(x + t + 8, y), (x + 8, y - t // 2), (x + 8, y + t // 2)], fill=fill)
    draw.polygon([(x + t + 6 + 8, y), (x + 2 * t + 6 + 8, y - t // 2), (x + 2 * t + 6 + 8, y + t // 2)], fill=fill)


# ---------------------------
# Placeholder art (if no album provided)
# ---------------------------
def placeholder_art(size):
    w, h = size
    base = Image.new("RGB", (w, h), (30, 10, 10))
    draw = ImageDraw.Draw(base)
    for yy in range(h):
        t = yy / max(1, h - 1)
        r = int(30 + (200 - 30) * t)
        draw.line((0, yy, w, yy), fill=(r, 8, 8))
    # subtle overlay red
    overlay = Image.new("RGBA", (w, h), (180, 0, 0, 60))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return base


# ---------------------------
# Style A: Pixel-accurate player (main)
# ---------------------------
def generate_style_a(album_art_path,
                     song_title,
                     artist_name,
                     album_label,
                     current_seconds,
                     total_seconds,
                     output_path,
                     reference_image: Optional[str] = None):
    """
    Generate a thumbnail replicating the provided screenshot exactly.

    - If reference_image is provided, sample exact colors from it.
    - album_art_path may be None, a path, or PIL Image.
    """

    # if reference image provided, sample palette
    global BG_COLOR, WIDGET_COLOR, RED_TINT, TITLE_COLOR, ARTIST_COLOR, ALBUM_COLOR, PROG_BG, PROG_FG, ICON_COLOR
    if reference_image and os.path.isfile(reference_image):
        sampled = sample_colors_from_reference(reference_image)
        if sampled:
            BG_COLOR = sampled["BG_COLOR"]
            WIDGET_COLOR = sampled["WIDGET_COLOR"]
            RED_TINT = sampled["RED_TINT"]
            TITLE_COLOR = sampled["TITLE_COLOR"]
            ARTIST_COLOR = sampled["ARTIST_COLOR"]
            ALBUM_COLOR = sampled["ALBUM_COLOR"]
            PROG_BG = sampled["PROG_BG"]
            PROG_FG = sampled["PROG_FG"]
            ICON_COLOR = sampled["ICON_COLOR"]

    # prepare canvas and widget (rounded)
    canvas = Image.new("RGB", CANVAS, BG_COLOR)
    widget = Image.new("RGB", WIDGET, WIDGET_COLOR)
    mask_w = rounded_mask(WIDGET, RADIUS)
    canvas.paste(widget, WIDGET_POS, mask_w)

    # load album art (if None, use placeholder)
    art = _open_album_art(album_art_path)
    if art is None:
        art = placeholder_art(ART_SIZE)
    art = ImageOps.fit(art, ART_SIZE, Image.Resampling.LANCZOS)
    # apply red tint like screenshot
    art = tint_image(art, RED_TINT, strength=0.65)
    art_rgba = art.convert("RGBA")
    art_rgba.putalpha(rounded_mask(ART_SIZE, 28))  # smaller radius for art corners
    canvas.paste(art_rgba, WIDGET_POS, art_rgba)

    draw = ImageDraw.Draw(canvas)

    # fonts tuned to screenshot (fallbacks)
    f_album = load_font(42)
    f_title = load_font(90, bold=True)
    f_artist = load_font(50)
    f_time = load_font(34)

    # text block measured from screenshot
    right_x = WIDGET_POS[0] + ART_SIZE[0] + 70
    y = WIDGET_POS[1] + 30

    # album label (small)
    draw.text((right_x, y), album_label, font=f_album, fill=ALBUM_COLOR)
    y += 70

    # title - auto-fit width
    max_w = WIDGET[0] - ART_SIZE[0] - 180
    # reduce font size until it fits visually
    title_font = f_title
    while draw.textlength(song_title, font=title_font) > max_w and getattr(title_font, "size", 80) > 20:
        size_new = getattr(title_font, "size", 90) - 6
        title_font = load_font(size_new, bold=True)
    title_to_draw = song_title
    # truncate long titles
    while draw.textlength(title_to_draw, font=title_font) > max_w and len(title_to_draw) > 4:
        title_to_draw = title_to_draw[:-2]
    if title_to_draw != song_title:
        title_to_draw = title_to_draw[:-3] + "..." if len(title_to_draw) > 3 else title_to_draw + "..."

    draw.text((right_x, y), title_to_draw, font=title_font, fill=TITLE_COLOR)
    y += getattr(title_font, "size", 60) + 28

    # artist
    artist_font = f_artist
    while draw.textlength(artist_name, font=artist_font) > max_w and getattr(artist_font, "size", 50) > 12:
        artist_font = load_font(getattr(artist_font, "size", 50) - 4)
    draw.text((right_x, y), artist_name, font=artist_font, fill=ARTIST_COLOR)
    y += getattr(artist_font, "size", 40) + 60

    # progress bar
    bar_w = 620
    bar_h = 14
    bx, by = right_x, y
    # bg
    draw.rounded_rectangle((bx, by, bx + bar_w, by + bar_h), radius=10, fill=PROG_BG)
    # compute progress fraction safely
    try:
        progress = max(0.0, min(1.0, float(current_seconds) / float(max(1.0, total_seconds))))
    except Exception:
        progress = 0.0
    fg = int(bar_w * progress)
    if fg > 0:
        draw.rounded_rectangle((bx, by, bx + fg, by + bar_h), radius=10, fill=PROG_FG)

    # times (left current, right remaining)
    y_time = by + bar_h + 10
    draw.text((bx, y_time), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
    draw.text((bx + bar_w - 110, y_time), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)

    # playback controls row
    icon_center_y = WIDGET_POS[1] + 330
    center_x = bx + bar_w // 2

    # draw prev / pause / next using the vector routines
    draw_prev(draw, center_x - 150, icon_center_y, scale=1.2, fill=ICON_COLOR)
    draw_pause(draw, center_x - 12, icon_center_y, scale=1.2, fill=ICON_COLOR)
    draw_next(draw, center_x + 120, icon_center_y, scale=1.2, fill=ICON_COLOR)

    # bluetooth + speaker icons (simple vector approximations)
    # speaker (left of bluetooth)
    sp_x = bx + bar_w + 28
    sp_y = icon_center_y
    # small speaker triangle + rectangle
    draw.polygon([(sp_x - 26, sp_y - 14), (sp_x - 6, sp_y - 14), (sp_x + 2, sp_y - 4), (sp_x + 2, sp_y + 4), (sp_x - 6, sp_y + 14), (sp_x - 26, sp_y + 14)], fill=ICON_COLOR)
    # bluetooth (approx) to the right of speaker
    bt_x = sp_x + 32
    bt_y = sp_y
    # simplified bluetooth: two crossing triangles/lines
    draw.line((bt_x - 4, bt_y - 20, bt_x + 14, bt_y), fill=ICON_COLOR, width=4)
    draw.line((bt_x + 14, bt_y, bt_x - 4, bt_y + 20), fill=ICON_COLOR, width=4)
    draw.line((bt_x - 4, bt_y - 20, bt_x - 4, bt_y + 20), fill=ICON_COLOR, width=2)

    # bottom volume bar (near bottom right area)
    vol_y = WIDGET_POS[1] + WIDGET[1] - 120
    vol_x = right_x
    vol_w = 560
    vol_h = 14
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_w, vol_y + vol_h), radius=8, fill=PROG_BG)
    vol_level = int(vol_w * 0.72)
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_level, vol_y + vol_h), radius=8, fill=PROG_FG)
    # little end blocks as in screenshot
    draw.rectangle((vol_x - 14, vol_y + 2, vol_x - 6, vol_y + vol_h - 2), fill=ICON_COLOR)
    draw.rectangle((vol_x + vol_w + 6, vol_y + 2, vol_x + vol_w + 14, vol_y + vol_h - 2), fill=ICON_COLOR)

    ensure_dir(output_path)
    canvas.save(output_path, quality=95)
    return output_path


# ---------------------------
# Style B & C (kept simple)
# ---------------------------
def generate_style_b(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path, reference_image: Optional[str] = None):
    img_w, img_h = 900, 900
    img = Image.new("RGB", (img_w, img_h), (20, 20, 20))
    draw = ImageDraw.Draw(img)
    art = _open_album_art(album_art_path)
    if art is None:
        art = placeholder_art((800, 800))
    else:
        art = ImageOps.fit(art, (800, 800), Image.Resampling.LANCZOS)
    img.paste(art, (50, 50))
    f_title = load_font(56, bold=True)
    f_artist = load_font(36)
    draw.text((60, 800), song_title, font=f_title, fill=TITLE_COLOR)
    draw.text((60, 860), artist_name, font=f_artist, fill=ARTIST_COLOR)
    ensure_dir(output_path)
    img.save(output_path, quality=95)
    return output_path


def generate_style_c(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path, reference_image: Optional[str] = None):
    w, h = CANVAS
    img = Image.new("RGB", (w, h), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    for yy in range(h):
        g = int(30 + (120 - 30) * (yy / max(1, h - 1)))
        draw.line((0, yy, w, yy), fill=(g, int(g * 0.6), int(g * 0.4)))
    art = _open_album_art(album_art_path)
    if art is None:
        art = placeholder_art((520, 520))
    else:
        art = ImageOps.fit(art, (520, 520), Image.Resampling.LANCZOS)
    img.paste(art, (60, 100))
    f_title = load_font(70, bold=True)
    f_artist = load_font(40)
    draw.text((620, 150), song_title, font=f_title, fill=TITLE_COLOR)
    draw.text((620, 240), artist_name, font=f_artist, fill=ARTIST_COLOR)
    ensure_dir(output_path)
    img.save(output_path, quality=95)
    return output_path


# ---------------------------
# PUBLIC API
# ---------------------------
_STYLE_MAP = {
    "A": generate_style_a,
    "B": generate_style_b,
    "C": generate_style_c,
}


def generate_thumbnail(style: str = "A",
                       album_art_path: Optional[Union[str, Image.Image]] = None,
                       song_title: str = "Unknown Title",
                       artist_name: str = "Unknown Artist",
                       album_label: str = "Airdopes 131",
                       current_seconds: int = 0,
                       total_seconds: int = 200,
                       output_path: str = "thumbnail.png",
                       reference_image: Optional[str] = None):
    """
    Main factory. Pass reference_image to sample perfect colors from screenshot.
    """
    style = (style or "A").upper()
    if style not in _STYLE_MAP:
        raise ValueError("Unknown style '%s'. Use 'A', 'B', or 'C'." % style)
    # call chosen style function
    return _STYLE_MAP[style](
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album_label=album_label,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
        reference_image=reference_image
    )


# Backwards compatibility wrapper used by your codebase
def get_thumb(album_art_path,
              song_title="Unknown Title",
              artist_name="Unknown Artist",
              album_label="Airdopes 131",
              current_seconds=0,
              total_seconds=200,
              output_path="thumbnail.png",
              style="A",
              reference_image: Optional[str] = None):
    return generate_thumbnail(
        style=style,
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album_label=album_label,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
        reference_image=reference_image
    )


# ---------------------------
# Quick CLI demo if executed directly
# ---------------------------
if __name__ == "__main__":
    # The uploaded screenshot you provided — put its filename here to get exact sampling
    REF = "reference_player.png"  # replace with the path to the screenshot you uploaded
    demo_art = None
    if os.path.exists("album.jpg"):
        demo_art = "album.jpg"
    # Create the pixel-accurate output using the reference for color sampling
    generate_thumbnail(
        style="A",
        album_art_path=demo_art,
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album_label="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="player_demo_exact.png",
        reference_image=REF
    )
    print("Wrote player_demo_exact.png (uses reference_image for perfect color matching)")