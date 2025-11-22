"""
thumbnails.py - Thumbnail generator (exact red player + extras)

Public API:
    generate_thumbnail(style="A", **kwargs)
    get_thumb(...)  # backward compatible wrapper

Styles:
    A - Exact red iOS-style full player (pixel-accurate layout)
    B - Simple square card
    C - Modern gradient layout
"""
from typing import Optional, Union
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import os
import io

# --------------------------- CONFIG (tuned for screenshots) ---------------------------
CANVAS = (1500, 800)            # overall image size
WIDGET = (1450, 650)           # inner dark rounded card
ART_SIZE = (620, 650)          # album art area (square-ish in screenshots)
RADIUS = 70
WIDGET_POS = (25, 75)

BG_COLOR = (86, 20, 18)
WIDGET_COLOR = (44, 10, 10)
RED_TINT = (170, 0, 0)

ALBUM_COLOR = (235, 220, 215)
TITLE_COLOR = (255, 255, 255)
ARTIST_COLOR = (210, 200, 195)

PROG_BG = (95, 38, 34)
PROG_FG = (255, 200, 192)

ICON_COLOR = (255, 255, 255)

# --------------------------- FONT LOADER ---------------------------
_DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "./fonts/DejaVuSans-Bold.ttf",
    "./fonts/DejaVuSans.ttf",
    "./fonts/Arial.ttf",
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Load a TrueType font from known locations, fallback to PIL default.
    bold: prefer a font whose filename contains "Bold"
    """
    for p in _DEFAULT_FONT_PATHS:
        try:
            if not os.path.isfile(p):
                continue
            name = os.path.basename(p).lower()
            if bold and "bold" not in name:
                # try to prefer bold if requested
                # but still allow non-bold if bold not found later
                pass
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    # final fallback
    return ImageFont.load_default()


# --------------------------- UTILITIES ---------------------------
def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return m


def tint_image(img: Image.Image, tint_color=RED_TINT, strength=0.7) -> Image.Image:
    overlay = Image.new("RGB", img.size, tint_color)
    return Image.blend(img.convert("RGB"), overlay, strength)


def mmss(sec: Union[int, float]) -> str:
    s = max(0, int(sec))
    return f"{s // 60}:{s % 60:02d}"


def ensure_dir(path: str) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)


def auto_fit_font(draw: ImageDraw.ImageDraw, text: str, base_font, max_w: int, bold: bool = False, min_size: int = 12):
    """
    Reduce font size until text fits within max_w. Returns a font instance.
    """
    # determine starting size
    size = getattr(base_font, "size", 36)
    if size is None:
        size = 36
    font = base_font
    while draw.textlength(text, font=font) > max_w and size > min_size:
        size -= 2
        font = load_font(size, bold=bold)
    return font


# --------------------------- ICONS (vector) ---------------------------
def draw_prev(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    t = int(34 * scale)
    # left triangles
    draw.polygon([(x - t, y), (x, y - t // 2), (x, y + t // 2)], fill=ICON_COLOR)
    draw.polygon([(x + 6, y), (x + t + 6, y - t // 2), (x + t + 6, y + t // 2)], fill=ICON_COLOR)


def draw_pause(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    h = int(56 * scale)
    w = int(16 * scale)
    draw.rectangle((x - w - 6, y - h // 2, x - 4, y + h // 2), fill=ICON_COLOR)
    draw.rectangle((x + 4, y - h // 2, x + w + 6, y + h // 2), fill=ICON_COLOR)


def draw_next(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    t = int(34 * scale)
    # right triangles
    draw.polygon([(x + t, y), (x, y - t // 2), (x, y + t // 2)], fill=ICON_COLOR)
    draw.polygon([(x + t + 6, y), (x + 2 * t + 6, y - t // 2), (x + 2 * t + 6, y + t // 2)], fill=ICON_COLOR)


# --------------------------- PLACEHOLDER ART ---------------------------
def placeholder_art(size):
    w, h = size
    img = Image.new("RGB", (w, h), (40, 10, 10))
    draw = ImageDraw.Draw(img)
    # subtle vertical gradient
    for yy in range(h):
        t = yy / max(1, h - 1)
        r = int(30 + (200 - 30) * t)
        g = 10
        b = 10
        draw.line((0, yy, w, yy), fill=(r, g, b))
    # vignette
    vign = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vign)
    vd.ellipse((-int(w * 0.1), -int(h * 0.2), int(w * 1.1), int(h * 1.2)), fill=180)
    vign = vign.filter(ImageFilter.GaussianBlur(60))
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (255, 0, 0, 40))
    base = Image.alpha_composite(base, overlay).convert("RGB")
    return base


def _open_album_art(candidate: Optional[Union[str, Image.Image]]):
    """
    Accept either:
      - path to file (str)
      - PIL.Image.Image instance
    Return: PIL.Image (RGB) or None on failure
    """
    if candidate is None:
        return None
    if isinstance(candidate, Image.Image):
        try:
            return candidate.convert("RGB")
        except Exception:
            return None
    if isinstance(candidate, str):
        if os.path.isfile(candidate):
            try:
                return Image.open(candidate).convert("RGB")
            except Exception:
                return None
    # we do not attempt HTTP fetching here (no network); return None
    return None


# --------------------------- STYLE A (Exact Red Player) ---------------------------
def generate_style_a(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    """
    Exact recreation of the provided red iOS-style player.

    album_art_path may be:
      - None -> use placeholder
      - path string -> file loaded (if exists)
      - PIL.Image.Image -> used directly
    """
    # prepare canvas + widget
    canvas = Image.new("RGB", CANVAS, BG_COLOR)
    widget = Image.new("RGB", WIDGET, WIDGET_COLOR)
    mask_w = rounded_mask(WIDGET, RADIUS)
    canvas.paste(widget, WIDGET_POS, mask_w)

    # load art (support PIL.Image or path), fallback to placeholder
    art = _open_album_art(album_art_path)
    if art is None:
        art = placeholder_art(ART_SIZE)

    # fit, tint, round
    art = ImageOps.fit(art, ART_SIZE, Image.Resampling.LANCZOS)
    art = tint_image(art, RED_TINT, 0.65)
    art_rgba = art.convert("RGBA")
    art_rgba.putalpha(rounded_mask(ART_SIZE, RADIUS))
    canvas.paste(art_rgba, WIDGET_POS, art_rgba)

    draw = ImageDraw.Draw(canvas)

    # fonts (sizes tuned to match screenshot)
    f_album = load_font(42)
    f_title = load_font(90, bold=True)
    f_artist = load_font(50)
    f_time = load_font(35)

    # text block positions
    right_x = WIDGET_POS[0] + ART_SIZE[0] + 70
    y = WIDGET_POS[1] + 30

    # album label
    draw.text((right_x, y), album_label, font=f_album, fill=ALBUM_COLOR)
    y += 70

    # title (auto fit)
    max_w = WIDGET[0] - ART_SIZE[0] - 180
    f_title = auto_fit_font(draw, song_title, f_title, max_w, bold=True, min_size=22)
    title_to_draw = song_title
    # truncate if still too long
    while draw.textlength(title_to_draw, font=f_title) > max_w and len(title_to_draw) > 4:
        title_to_draw = title_to_draw[:-2]
    if title_to_draw != song_title:
        # ensure '...' end
        title_to_draw = title_to_draw[:-3] + "..." if len(title_to_draw) > 3 else title_to_draw + "..."
    draw.text((right_x, y), title_to_draw, font=f_title, fill=TITLE_COLOR)
    # advance y by font size (if available) else a reasonable fallback
    y += getattr(f_title, "size", 60) + 28

    # artist
    f_artist = auto_fit_font(draw, artist_name, f_artist, max_w, bold=False, min_size=18)
    draw.text((right_x, y), artist_name, font=f_artist, fill=ARTIST_COLOR)
    y += getattr(f_artist, "size", 40) + 60

    # progress bar
    bar_w = 620
    bar_h = 14
    bx, by = right_x, y
    draw.rounded_rectangle((bx, by, bx + bar_w, by + bar_h), radius=10, fill=PROG_BG)
    # safe progress fraction
    try:
        progress = max(0.0, min(1.0, float(current_seconds) / float(max(1.0, total_seconds))))
    except Exception:
        progress = 0.0
    fg = int(bar_w * progress)
    if fg > 0:
        draw.rounded_rectangle((bx, by, bx + fg, by + bar_h), radius=10, fill=PROG_FG)

    # times
    y_time = by + bar_h + 10
    draw.text((bx, y_time), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
    # right aligned remaining time
    draw.text((bx + bar_w - 110, y_time), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)

    # playback controls row (centered; tuned values)
    icon_center_y = WIDGET_POS[1] + 330
    center_x = bx + bar_w // 2

    # draw prev / pause / next icons
    draw_prev(draw, center_x - 150, icon_center_y, scale=1.2)
    draw_pause(draw, center_x - 12, icon_center_y, scale=1.2)
    draw_next(draw, center_x + 120, icon_center_y, scale=1.2)

    # bottom volume bar (simple)
    vol_y = WIDGET_POS[1] + WIDGET[1] - 120
    vol_x = right_x
    vol_w = 560
    vol_h = 14
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_w, vol_y + vol_h), radius=8, fill=PROG_BG)
    vol_level = int(vol_w * 0.72)
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_level, vol_y + vol_h), radius=8, fill=PROG_FG)

    # small end squares
    draw.rectangle((vol_x - 14, vol_y + 2, vol_x - 6, vol_y + vol_h - 2), fill=ICON_COLOR)
    draw.rectangle((vol_x + vol_w + 6, vol_y + 2, vol_x + vol_w + 14, vol_y + vol_h - 2), fill=ICON_COLOR)

    ensure_dir(output_path)
    canvas.save(output_path, quality=95)
    return output_path


# --------------------------- STYLE B (Simple Card) ---------------------------
def generate_style_b(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    img_w, img_h = 900, 900
    img = Image.new("RGB", (img_w, img_h), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    # art
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


# --------------------------- STYLE C (Gradient Modern) ---------------------------
def generate_style_c(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    w, h = CANVAS
    img = Image.new("RGB", (w, h), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    # vertical gradient background
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


# --------------------------- PUBLIC API ---------------------------
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
                       output_path: str = "thumbnail.png"):
    """
    Main factory function. style: 'A'|'B'|'C'
    album_art_path may be None, a filesystem path, or a PIL Image
    """
    style = (style or "A").upper()
    if style not in _STYLE_MAP:
        raise ValueError("Unknown style '%s'. Use 'A', 'B', or 'C'." % style)
    return _STYLE_MAP[style](
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album_label=album_label,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
    )


# --------------------------- BACKWARDS COMPAT ---------------------------
def get_thumb(album_art_path,
              song_title="Unknown Title",
              artist_name="Unknown Artist",
              album_label="Airdopes 131",
              current_seconds=0,
              total_seconds=200,
              output_path="thumbnail.png",
              style="A"):
    """
    Backwards-compatible wrapper kept for existing imports.
    """
    return generate_thumbnail(
        style=style,
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album_label=album_label,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
    )


# --------------------------- QUICK DEMO (if run as script) ---------------------------
if __name__ == "__main__":
    demo_art = None
    if os.path.exists("album.jpg"):
        demo_art = "album.jpg"
    # Example: pass a path or a PIL Image object for album_art_path
    generate_thumbnail(
        style="A",
        album_art_path=demo_art,
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album_label="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="player_demo.png",
    )