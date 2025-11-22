"""
music_player_thumbnail_b_refactored.py
Generates a pixel-accurate 'Full Album Photo Player' thumbnail (Style B)
Matching the provided screenshot exactly (Option A).

Author: ChatGPT
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import os

# ============================================================
# CONFIGURATION (Exact to Screenshot)
# ============================================================

CANVAS = (1280, 720)

WIDGET = (1100, 500)
WIDGET_POS = (90, 110)
ART_SIZE = (430, 500)
RADIUS = 55

BG_COLOR = (86, 20, 18)
WIDGET_COLOR = (44, 10, 10)
RED_TINT = (170, 0, 0)

ALBUM_COLOR = (220, 190, 165)
TITLE_COLOR = (255, 255, 255)
ARTIST_COLOR = (215, 205, 200)

PROG_BG = (95, 38, 34)
PROG_FG = (255, 200, 192)

ICON_COLOR = (255, 255, 255)

# ============================================================
# HELPERS
# ============================================================

def load_font(size, bold=False):
    """Loads system font or local fallback."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "./fonts/DejaVuSans-Bold.ttf" if bold else "./fonts/DejaVuSans.ttf",
        "./fonts/Arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def rounded_mask(size, r):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=r, fill=255)
    return mask


def tint(img, strength=0.7):
    return Image.blend(img.convert("RGB"), Image.new("RGB", img.size, RED_TINT), strength)


def fit_text_width(draw, text, font, max_w):
    """Auto-shrinks text until it fits exactly."""
    size = font.size
    while draw.textlength(text, font=font) > max_w and size > 15:
        size -= 2
        font = load_font(size, bold=True)
    return font


def mmss(sec):
    sec = int(max(0, sec))
    return f"{sec//60}:{sec%60:02d}"


# ============================================================
# DRAWING
# ============================================================

def draw_controls(draw, cx, cy):
    """Draw prev, pause, next, speaker icons — pixel matched."""
    t = 34
    left_x = cx - 220
    y = cy

    # Prev
    draw.polygon([(left_x, y+t), (left_x+t, y+t/2), (left_x, y)], fill=ICON_COLOR)
    draw.polygon([(left_x+t+8, y+t), (left_x+t*2+8, y+t/2), (left_x+t+8, y)], fill=ICON_COLOR)

    # Pause
    px = cx - 30
    draw.rectangle((px-22, y-28, px-6, y+28), fill=ICON_COLOR)
    draw.rectangle((px+6, y-28, px+22, y+28), fill=ICON_COLOR)

    # Next
    nx = cx + 120
    draw.polygon([(nx, y), (nx+t, y+t/2), (nx, y+t)], fill=ICON_COLOR)
    draw.polygon([(nx+t+8, y), (nx+t*2+8, y+t/2), (nx+t+8, y+t)], fill=ICON_COLOR)

    # Speaker
    spx = cx + 300
    spy = y - 22
    draw.polygon([(spx, spy+18),(spx+22, spy),(spx+22, spy+44),(spx, spy+26)], fill=ICON_COLOR)
    draw.arc((spx+26, spy-8, spx+66, spy+52), -60, 60, fill=ICON_COLOR, width=3)
    draw.arc((spx+34, spy-2, spx+86, spy+58), -60, 60, fill=ICON_COLOR, width=3)
    draw.arc((spx+42, spy+6, spx+104, spy+66), -60, 60, fill=ICON_COLOR, width=3)


# ============================================================
# MAIN GENERATOR
# ============================================================

def create_thumbnail(
    album_art_path,
    song_title="Unknown Title",
    artist_name="Unknown Artist",
    album_label="Airdopes 131",
    current_seconds=0,
    total_seconds=200,
    output_path="player_b.png",
):
    cw, ch = CANVAS
    canvas = Image.new("RGB", (cw, ch), BG_COLOR)

    # Widget
    widget = Image.new("RGB", WIDGET, WIDGET_COLOR)
    mask = rounded_mask(WIDGET, RADIUS)
    canvas.paste(widget, WIDGET_POS, mask)

    # Album art
    ax, ay = WIDGET_POS
    if album_art_path and os.path.exists(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
        art = ImageOps.fit(art, ART_SIZE, method=Image.Resampling.LANCZOS)
    else:
        art = Image.new("RGB", ART_SIZE, (100, 0, 0))

    art = tint(art, 0.7)
    art_rgba = art.convert("RGBA")
    art_rgba.putalpha(rounded_mask(ART_SIZE, RADIUS))
    canvas.paste(art_rgba, (ax, ay), art_rgba)

    # Right Panel
    draw = ImageDraw.Draw(canvas)

    f_album = load_font(28)
    f_title = load_font(72, bold=True)
    f_artist = load_font(42)
    f_time = load_font(28)

    right_x = ax + ART_SIZE[0] + 60
    cy = ay + 20

    # Album label
    draw.text((right_x, cy), album_label, font=f_album, fill=ALBUM_COLOR)
    cy += 55

    # Auto-fit Title
    max_title_w = WIDGET[0] - ART_SIZE[0] - 150
    f_title = fit_text_width(draw, song_title, f_title, max_title_w)
    draw.text((right_x, cy), song_title, font=f_title, fill=TITLE_COLOR)
    cy += f_title.size + 20

    # Artist (auto-fit also)
    f_artist = fit_text_width(draw, artist_name, f_artist, max_title_w)
    draw.text((right_x, cy), artist_name, font=f_artist, fill=ARTIST_COLOR)
    cy += f_artist.size + 50

    # Progress Bar
    bar_w = 520
    bar_h = 12
    bx, by = right_x, cy

    draw.rounded_rectangle((bx, by, bx+bar_w, by+bar_h), radius=8, fill=PROG_BG)

    progress = max(0, min(1, current_seconds / max(1, total_seconds)))
    fg = int(bar_w * progress)

    if fg > 0:
        draw.rounded_rectangle((bx, by, bx+fg, by+bar_h), radius=8, fill=PROG_FG)

    cy += 32

    draw.text((bx, cy), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
    draw.text((bx + bar_w - 80, cy), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)

    cy += 70

    # Controls
    draw_controls(draw, bx + 120, cy)

    # Volume bar
    vol_y = WIDGET_POS[1] + WIDGET[1] - 100
    vol_x = right_x
    vol_w = 480
    vol_h = 12

    draw.rounded_rectangle((vol_x, vol_y, vol_x+vol_w, vol_y+vol_h), radius=8, fill=PROG_BG)
    draw.rounded_rectangle((vol_x, vol_y, vol_x+int(vol_w*0.72), vol_y+vol_h),
                           radius=8, fill=PROG_FG)

    draw.rectangle((vol_x - 10, vol_y+2, vol_x - 4, vol_y+vol_h-2), fill=ICON_COLOR)
    draw.rectangle((vol_x + vol_w + 6, vol_y+2, vol_x + vol_w + 12, vol_y+vol_h-2),
                   fill=ICON_COLOR)

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, quality=95)
    print("[Refactored] Saved:", output_path)
    return output_path