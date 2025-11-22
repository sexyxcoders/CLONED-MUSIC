"""
exact_music_thumbnail.py
Creates a pixel-accurate music widget thumbnail similar to the screenshots provided.

Usage:
    from exact_music_thumbnail import get_thumb
    get_thumb(
        album_art_path="cover.jpg",
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="out.png",
        canvas_size=(1280,720)
    )

If album_art_path doesn't exist, a placeholder is generated so you can test layout.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import math
import textwrap

# ---------- Configuration ----------
DEFAULT_CANVAS = (1280, 720)
WIDGET_SIZE = (1100, 500)        # width, height of the rounded card similar to screenshot
WIDGET_OFFSET = (90, 110)        # where the widget sits on the canvas
ART_SIZE = (430, 500)            # left artwork size (w,h)
ROUNDS = 50                      # corner radius for widget and art
BG_COLOR = (95, 22, 17)          # page background (dark red)
WIDGET_COLOR = (55, 12, 12)      # inner widget (slightly lighter)
RED_OVERLAY = (180, 0, 0)        # overlay color to tint album art
ICON_COLOR = (255, 255, 255)     # white icons/text
PROG_BG = (100, 48, 42)          # progress bar background
PROG_FG = (255, 200, 190)        # progress foreground (light pink)
TIME_COLOR = (235, 230, 230)     # time text color
ALBUM_COLOR = (220, 180, 160)    # small album label color
# -----------------------------------

def load_font(size, bold=False):
    # try some common fonts; fallback to default.
    candidate_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "./fonts/DejaVuSans-Bold.ttf" if bold else "./fonts/DejaVuSans.ttf",
        "./fonts/arialbd.ttf" if bold else "./fonts/arial.ttf"
    ]
    for p in candidate_paths:
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def rounded_rectangle_mask(size, radius):
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    return mask

def tint_red(img, strength=0.62):
    """Blend a red overlay to reproduce the mono red look."""
    red = Image.new("RGB", img.size, RED_OVERLAY)
    return Image.blend(img.convert("RGB"), red, strength)

def generate_placeholder_art(size):
    """Create a simple placeholder album art (so you can test without providing an image)."""
    w, h = size
    img = Image.new("RGB", (w, h), (50, 20, 20))
    draw = ImageDraw.Draw(img)
    # simple gradient
    for y in range(h):
        t = y / h
        r = int(40 + (180 - 40) * t)
        g = int(10 + (20 - 10) * (1 - t))
        b = int(10 + (40 - 10) * (1 - t))
        draw.line((0, y, w, y), fill=(r, g, b))
    # a soft elliptical highlight
    ellipse = Image.new("L", (w, h), 0)
    ed = ImageDraw.Draw(ellipse)
    ed.ellipse((int(w*0.15), int(h*0.05), int(w*0.9), int(h*0.9)), fill=120)
    blur = ellipse.filter(ImageFilter.GaussianBlur(30))
    img.putalpha(255)
    red = Image.new("RGBA", img.size, (255, 0, 0, 30))
    img = Image.alpha_composite(img.convert("RGBA"), red)
    return img.convert("RGB")

def draw_controls(draw, top_left_x, top_left_y, spacing=110):
    """Draw play control icons centered area — uses simple polygon shapes so no emoji font needed."""
    # We'll draw three items: prev (triangle-left pair), pause (two bars), next (triangle-right pair), and speaker icon to right.
    # prev
    px = top_left_x
    py = top_left_y
    # left double triangles (prev)
    tri_size = 34
    gap = 12
    # left triangle
    draw.polygon([(px, py+tri_size),(px+tri_size, py+tri_size*0.5),(px, py)], fill=ICON_COLOR)
    # second left triangle offset
    draw.polygon([(px+tri_size+6, py+tri_size),(px+tri_size*2+6, py+tri_size*0.5),(px+tri_size+6, py)], fill=ICON_COLOR)

    # pause in middle
    px2 = px + spacing
    wbar = 18
    hbar = 50
    draw.rectangle((px2 - 18, py, px2 - 2, py + hbar), fill=ICON_COLOR)
    draw.rectangle((px2 + 2, py, px2 + 18, py + hbar), fill=ICON_COLOR)

    # next triangles (mirror of prev)
    px3 = px2 + spacing
    draw.polygon([(px3, py),(px3+tri_size, py+tri_size*0.5),(px3, py+tri_size)], fill=ICON_COLOR)
    draw.polygon([(px3+tri_size+6, py),(px3+tri_size*2+6, py+tri_size*0.5),(px3+tri_size+6, py+tri_size)], fill=ICON_COLOR)

    # speaker icon at right of controls (simple speaker + waves)
    spx = px3 + spacing + 80
    spy = py + 6
    # speaker base
    draw.polygon([(spx, spy+10), (spx+18, spy), (spx+18, spy+50), (spx, spy+40)], fill=ICON_COLOR)
    # wave arcs using arc drawing with thick stroke - emulate by drawing multiple arcs
    for i in range(3):
        bbox = [spx+22 + i*7, spy+2 - i*4, spx+22 + 30 + i*7, spy+48 + i*4]
        draw.arc(bbox, start=-60, end=60, fill=ICON_COLOR, width=3)

def seconds_to_mmss(sec):
    sec = max(0, int(sec))
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"

def create_thumbnail(
    album_art_path,
    song_title="Unknown Title",
    artist_name="Unknown Artist",
    album="Airdopes 131",
    current_seconds=141,
    total_seconds=260,
    output_path="thumbnail.png",
    canvas_size=DEFAULT_CANVAS
):
    # --- canvas & widget ---
    cw, ch = canvas_size
    canvas = Image.new("RGB", (cw, ch), BG_COLOR)
    widget_w, widget_h = WIDGET_SIZE
    widget = Image.new("RGB", (widget_w, widget_h), WIDGET_COLOR)

    # apply subtle inner shadow on widget to match screenshot depth
    shadow = Image.new("RGBA", (widget_w, widget_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    # darken bottom-left area a bit
    for i in range(12):
        alpha = int(18 + i*6)
        sd.rounded_rectangle((i, i, widget_w-i, widget_h-i), radius=ROUNDS-10, fill=(0,0,0,alpha))
    widget = Image.alpha_composite(widget.convert("RGBA"), shadow).convert("RGB")

    # round mask and paste widget on canvas
    mask = rounded_rectangle_mask((widget_w, widget_h), ROUNDS)
    canvas.paste(widget, WIDGET_OFFSET, mask)

    # --- album art ---
    art_x, art_y = WIDGET_OFFSET[0], WIDGET_OFFSET[1]
    # try load album art
    if album_art_path and os.path.isfile(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
        # crop to center square then resize to ART_SIZE preserving aspect mood
        aw, ah = art.size
        # scale while preserving aspect and then center crop to ART_SIZE
        art_thumb = ImageOps.fit(art, ART_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    else:
        art_thumb = generate_placeholder_art(ART_SIZE)

    # tint the album art red strongly then apply rounded corners
    art_tinted = tint_red(art_thumb, strength=0.66)
    art_mask = rounded_rectangle_mask(ART_SIZE, ROUNDS)
    art_rgba = art_tinted.copy().convert("RGBA")
    art_rgba.putalpha(art_mask)
    canvas.paste(art_rgba, (art_x, art_y), art_rgba)

    # --- content right side (texts, progress, controls) ---
    draw = ImageDraw.Draw(canvas)
    # fonts
    f_album = load_font(28)
    f_title = load_font(68, bold=True)
    f_artist = load_font(44)
    f_time = load_font(28)
    # positions (derived to match screenshot)
    right_x = art_x + ART_SIZE[0] + 60
    cur_y = art_y + 20

    # small album label
    draw.text((right_x, cur_y), album, font=f_album, fill=ALBUM_COLOR)
    cur_y += 52

    # song title (single-line large; truncate with ellipsis if too long)
    # We'll measure and if longer than available width, cut and add ellipsis
    max_title_w = WIDGET_SIZE[0] - (ART_SIZE[0] + 120)
    title = song_title
    # simple truncation:
    while draw.textlength(title, font=f_title) > max_title_w and len(title) > 4:
        title = title[:-2]
    if title != song_title:
        title = title[:-3] + "..."
    draw.text((right_x, cur_y), title, font=f_title, fill=ICON_COLOR)
    cur_y += 92

    # artist line
    draw.text((right_x, cur_y), artist_name, font=f_artist, fill=TIME_COLOR)
    cur_y += 78

    # progress bar
    bar_w = 520
    bar_h = 12
    bar_x = right_x
    bar_y = cur_y
    # background
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=8, fill=PROG_BG)
    # foreground according to progress
    progress = 0.0
    if total_seconds and total_seconds > 0:
        progress = max(0.0, min(1.0, float(current_seconds) / float(total_seconds)))
    fg_w = int(bar_w * progress)
    if fg_w > 0:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fg_w, bar_y + bar_h), radius=8, fill=PROG_FG)
    # small rounded 'cap' on left to mimic screenshot
    cap_radius = 6
    # times under the bar
    cur_y += 30
    draw.text((bar_x, cur_y), seconds_to_mmss(current_seconds), font=f_time, fill=TIME_COLOR)
    draw.text((bar_x + bar_w - 70, cur_y), "-" + seconds_to_mmss(total_seconds), font=f_time, fill=TIME_COLOR)
    cur_y += 70

    # draw controls; center control group horizontally in available right region
    controls_center_x = right_x + 60
    controls_top = cur_y
    draw_controls(draw, controls_center_x, controls_top, spacing=140)

    # --- bottom volume bar (near bottom-right of widget) ---
    vol_x = right_x
    vol_y = WIDGET_OFFSET[1] + WIDGET_SIZE[1] - 110
    vol_w = 480
    vol_h = 10
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_w, vol_y + vol_h), radius=6, fill=PROG_BG)
    # assume 70% volume
    vol_level = int(vol_w * 0.7)
    draw.rounded_rectangle((vol_x, vol_y, vol_x + vol_level, vol_y + vol_h), radius=6, fill=PROG_FG)
    # small speaker icons at both ends (left small speaker and right volume speaker)
    draw.rectangle((vol_x - 12, vol_y + 1, vol_x - 2, vol_y + vol_h - 1), fill=TIME_COLOR)
    draw.rectangle((vol_x + vol_w + 8, vol_y + 1, vol_x + vol_w + 18, vol_y + vol_h - 1), fill=TIME_COLOR)

    # subtle outer stroke around widget for crispness
    stroke = Image.new("RGBA", (widget_w, widget_h), (0,0,0,0))
    sd = ImageDraw.Draw(stroke)
    sd.rounded_rectangle((0,0,widget_w-1,widget_h-1), radius=ROUNDS, outline=(20,8,8,80), width=2)
    canvas.paste(stroke, WIDGET_OFFSET, stroke)

    # final save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, quality=95)
    print("[exact_music_thumbnail] Saved to:", output_path)
    return output_path

# Backwards-compatible wrapper
def get_thumb(
    album_art_path,
    song_title="Unknown Title",
    artist_name="Unknown Artist",
    album="Airdopes 131",
    current_seconds=141,
    total_seconds=260,
    output_path="thumbnail.png",
    canvas_size=DEFAULT_CANVAS
):
    return create_thumbnail(
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album=album,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
        canvas_size=canvas_size
    )

# If run as script, quick demo:
if __name__ == "__main__":
    # if you have an album art, put its path here; otherwise leave None to use placeholder
    sample_art = "album.jpg"  # replace with your file, or ensure album.jpg exists
    if not os.path.isfile(sample_art):
        sample_art = None
    get_thumb(
        album_art_path=sample_art,
        song_title="Anuv Jain - Afsos Ft. Ap",
        artist_name="N?x? // ? ? ? ?",
        album="Airdopes 131",
        current_seconds=141,
        total_seconds=140,
        output_path="exact_thumbnail_output.png"
    )