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

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import os

# --------------------------- CONFIG ---------------------------
CANVAS = (1280, 720)
WIDGET = (1125, 520)
ART_SIZE = (430, 500)
RADIUS = 55
WIDGET_POS = (90, 110)

BG_COLOR = (86, 20, 18)
WIDGET_COLOR = (44, 10, 10)
RED_TINT = (170, 0, 0)

ALBUM_COLOR = (220, 190, 165)
TITLE_COLOR = (255, 255, 255)
ARTIST_COLOR = (215, 205, 200)

PROG_BG = (95, 38, 34)
PROG_FG = (255, 200, 192)

ICON_COLOR = (255, 255, 255)

# --------------------------- FONT LOADER ---------------------------
_DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "./fonts/DejaVuSans-Bold.ttf",
    "./fonts/DejaVuSans.ttf",
    "./fonts/Arial.ttf",
]


def load_font(size: int, bold: bool = False):
    """
    Load a TrueType font from known locations, fallback to PIL default.
    `bold` prefers bold candidates when available.
    """
    for p in _DEFAULT_FONT_PATHS:
        if os.path.isfile(p):
            try:
                # simple heuristic: choose bold path when requested
                if bold and "Bold" not in os.path.basename(p):
                    continue
                if not bold and "Bold" in os.path.basename(p):
                    continue
                return ImageFont.truetype(p, size)
            except Exception:
                continue
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


def mmss(sec):
    s = max(0, int(sec))
    return f"{s//60}:{s%60:02d}"


def ensure_dir(path):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)


def auto_fit_font(draw: ImageDraw.ImageDraw, text: str, base_font, max_w: int, bold=False, min_size=12):
    """
    Reduce font size until text fits within max_w. Returns a font instance.
    """
    size = getattr(base_font, "size", 36)
    font = base_font
    while draw.textlength(text, font=font) > max_w and size > min_size:
        size -= 2
        font = load_font(size, bold=bold)
    return font


# --------------------------- ICONS (vector) ---------------------------
# Draws basic prev/pause/next icons similar to screenshot


def draw_prev(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    t = int(34 * scale)
    # two left triangles
    draw.polygon([(x, y + t), (x + t, y + t//2), (x, y)], fill=ICON_COLOR)
    draw.polygon([(x + t + 8, y + t), (x + t * 2 + 8, y + t//2), (x + t + 8, y)], fill=ICON_COLOR)


def draw_pause(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    h = int(56 * scale)
    w = int(16 * scale)
    draw.rectangle((x - w, y - h // 2, x - 4, y + h // 2), fill=ICON_COLOR)
    draw.rectangle((x + 4, y - h // 2, x + w, y + h // 2), fill=ICON_COLOR)


def draw_next(draw: ImageDraw.ImageDraw, x, y, scale=1.0):
    t = int(34 * scale)
    draw.polygon([(x + t * 2 + 8, y), (x + t + 8, y + t//2), (x + t * 2 + 8, y + t)], fill=ICON_COLOR)
    draw.polygon([(x + t + 8, y), (x + t, y + t//2), (x + t + 8, y + t)], fill=ICON_COLOR)


# --------------------------- PLACEHOLDER ART ---------------------------
def placeholder_art(size):
    w, h = size
    img = Image.new("RGB", (w, h), (40, 10, 10))
    draw = ImageDraw.Draw(img)
    # subtle vertical gradient
    for y in range(h):
        t = y / h
        r = int(30 + (200 - 30) * t)
        g = int(10)
        b = int(10)
        draw.line((0, y, w, y), fill=(r, g, b))
    # vignette
    vign = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vign)
    vd.ellipse((-int(w * 0.1), -int(h * 0.2), int(w * 1.1), int(h * 1.2)), fill=180)
    vign = vign.filter(ImageFilter.GaussianBlur(60))
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (255, 0, 0, 40))
    base = Image.alpha_composite(base, overlay).convert("RGB")
    return base


# --------------------------- STYLE A (Exact Red Player) ---------------------------
def generate_style_a(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    """
    Exact recreation of the provided red iOS-style player.
    """
    # prepare canvas + widget
    canvas = Image.new("RGB", CANVAS, BG_COLOR)

    widget = Image.new("RGB", WIDGET, WIDGET_COLOR)
    mask_w = rounded_mask(WIDGET, RADIUS)
    canvas.paste(widget, WIDGET_POS, mask_w)

    # load art (fallback)
    if album_art_path and os.path.isfile(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
    else:
        art = placeholder_art(ART_SIZE)

    # fit, tint, round
    art = ImageOps.fit(art, ART_SIZE, Image.Resampling.LANCZOS)
    art = tint_image(art, RED_TINT, 0.7)
    art_rgba = art.convert("RGBA")
    art_rgba.putalpha(rounded_mask(ART_SIZE, RADIUS))
    canvas.paste(art_rgba, WIDGET_POS, art_rgba)

    draw = ImageDraw.Draw(canvas)

    # fonts
    f_album = load_font(30)
    f_title = load_font(72, bold=True)
    f_artist = load_font(44)
    f_time = load_font(28)

    # text block positions
    right_x = WIDGET_POS[0] + ART_SIZE[0] + 60
    y = WIDGET_POS[1] + 20

    # album label
    draw.text((right_x, y), album_label, font=f_album, fill=ALBUM_COLOR)
    y += 58

    # title (auto fit)
    max_w = WIDGET[0] - ART_SIZE[0] - 140
    f_title = auto_fit_font(draw, song_title, f_title, max_w, bold=True, min_size=18)
    title_to_draw = song_title
    # additional truncate safety
    while draw.textlength(title_to_draw, font=f_title) > max_w and len(title_to_draw) > 4:
        title_to_draw = title_to_draw[:-2]
    if title_to_draw != song_title:
        title_to_draw = title_to_draw[:-3] + "..."
    draw.text((right_x, y), title_to_draw, font=f_title, fill=TITLE_COLOR)
    y += f_title.size + 20

    # artist
    f_artist = auto_fit_font(draw, artist_name, f_artist, max_w, bold=False, min_size=14)
    draw.text((right_x, y), artist_name, font=f_artist, fill=ARTIST_COLOR)
    y += f_artist.size + 50

    # progress bar
    bar_w = 520
    bar_h = 12
    bx, by = right_x, y
    draw.rounded_rectangle((bx, by, bx + bar_w, by + bar_h), radius=8, fill=PROG_BG)
    progress = max(0.0, min(1.0, float(current_seconds) / float(max(1.0, total_seconds))))
    fg = int(bar_w * progress)
    if fg > 0:
        draw.rounded_rectangle((bx, by, bx + fg, by + bar_h), radius=8, fill=PROG_FG)

    # times
    y_time = by + bar_h + 8
    draw.text((bx, y_time), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
    draw.text((bx + bar_w - 80, y_time), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)

    # playback controls row (centered)
    icon_center_y = WIDGET_POS[1] + 260  # tuned to match screenshot spacing
    center_x = bx + bar_w // 2

    # draw prev / pause / next icons using vector helpers
    draw_prev(draw, center_x - 120, icon_center_y)
    draw_pause(draw, center_x - 20, icon_center_y)
    draw_next(draw, center_x + 80, icon_center_y)

    # bottom volume bar (simple)
    vol_y = WIDGET_POS[1] + WIDGET[1] - 100
    vol_x = right_x
    vol_w = 480
    vol_h = 12
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_w, vol_y + vol_h), radius=8, fill=PROG_BG)
    vol_level = int(vol_w * 0.72)
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_level, vol_y + vol_h), radius=8, fill=PROG_FG)

    # small end squares
    draw.rectangle((vol_x - 10, vol_y + 2, vol_x - 4, vol_y + vol_h - 2), fill=ICON_COLOR)
    draw.rectangle((vol_x + vol_w + 6, vol_y + 2, vol_x + vol_w + 12, vol_y + vol_h - 2), fill=ICON_COLOR)

    ensure_dir(output_path)
    canvas.save(output_path, quality=95)
    return output_path


# --------------------------- STYLE B (Simple Card) ---------------------------
def generate_style_b(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    img_w, img_h = 800, 900
    img = Image.new("RGB", (img_w, img_h), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    # art
    if album_art_path and os.path.isfile(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
        art = ImageOps.fit(art, (700, 700), Image.Resampling.LANCZOS)
    else:
        art = placeholder_art((700, 700))
    img.paste(art, (50, 50))

    f_title = load_font(52, bold=True)
    f_artist = load_font(32)

    draw.text((60, 780), song_title, font=f_title, fill=TITLE_COLOR)
    draw.text((60, 840), artist_name, font=f_artist, fill=ARTIST_COLOR)

    ensure_dir(output_path)
    img.save(output_path, quality=95)
    return output_path


# --------------------------- STYLE C (Gradient Modern) ---------------------------
def generate_style_c(album_art_path, song_title, artist_name, album_label,
                     current_seconds, total_seconds, output_path):
    w, h = CANVAS
    img = Image.new("RGB", (w, h), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    # gradient
    for y in range(h):
        g = int(30 + (120 - 30) * (y / h))
        draw.line((0, y, w, y), fill=(g, int(g * 0.6), int(g * 0.4)))

    if album_art_path and os.path.isfile(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
        art = ImageOps.fit(art, (520, 520), Image.Resampling.LANCZOS)
    else:
        art = placeholder_art((520, 520))
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


def generate_thumbnail(style="A", album_art_path=None, song_title="Unknown Title",
                       artist_name="Unknown Artist", album_label="Airdopes 131",
                       current_seconds=0, total_seconds=200, output_path="thumbnail.png"):
    """
    Main factory function. style: 'A'|'B'|'C'
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
    # simple demo, writes player_demo.png into cwd
    demo_art = None
    if os.path.exists("album.jpg"):
        demo_art = "album.jpg"
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